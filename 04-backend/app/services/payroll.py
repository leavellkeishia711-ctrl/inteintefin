from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import uuid
from decimal import Decimal
from app.db.models import PayrollRun, PayrollLineItem, User, Company
from app.schemas.payroll import PayrollResponse, EmployeePayroll

async def get_payroll_overview(db: AsyncSession, company_id: uuid.UUID) -> PayrollResponse:
    # Get active employees
    users_result = await db.execute(
        select(User).where(User.company_id == company_id)
    )
    users = users_result.scalars().all()
    active_employees = len(users)

    # Calculate total payroll and get list
    total_payroll = Decimal("0")
    pending_approval = 0
    employees = []

    # Get latest payroll run
    latest_run_result = await db.execute(
        select(PayrollRun)
        .where(PayrollRun.company_id == company_id)
        .order_by(PayrollRun.period_end.desc())
        .limit(1)
    )
    latest_run = latest_run_result.scalars().first()

    if latest_run:
        total_payroll = latest_run.total_amount
        if latest_run.status == 'draft':
            pending_approval = 1

        # Get line items
        line_items_result = await db.execute(
            select(PayrollLineItem, User)
            .join(User, PayrollLineItem.user_id == User.id)
            .where(PayrollLineItem.payroll_run_id == latest_run.id)
        )
        for item, user in line_items_result:
            employees.append(EmployeePayroll(
                user_id=user.id,
                name=user.name,
                role=user.role,
                base_salary=item.base_amount,
                bonus_amount=item.bonus_amount,
                total_amount=item.total_amount,
                status=item.status,
                model_type="Fixed" # We could fetch from CompensationPlan
            ))
    else:
        # Fallback to compensation plans if no payroll run
        from app.db.models.system import CompensationPlan
        for user in users:
            comp_result = await db.execute(
                select(CompensationPlan).where(CompensationPlan.user_id == user.id)
                .order_by(CompensationPlan.effective_from.desc()).limit(1)
            )
            comp = comp_result.scalars().first()
            base = comp.base_salary if comp else Decimal("0")
            employees.append(EmployeePayroll(
                user_id=user.id,
                name=user.name,
                role=user.role,
                base_salary=base,
                bonus_amount=Decimal("0"),
                total_amount=base,
                status="draft",
                model_type=comp.bonus_basis if comp else "Fixed"
            ))

    return PayrollResponse(
        total_payroll=total_payroll,
        active_employees=active_employees,
        pending_approval=pending_approval,
        employees=employees
    )

from datetime import date
import sqlalchemy as sa

async def calculate_payroll_run(db: AsyncSession, company_id: uuid.UUID, period_start: date, period_end: date) -> PayrollRun:
    from app.db.models.system import CompensationPlan
    from app.db.models.campaigns import CampaignRunStat, CampaignRun
    
    # 1. Check if run exists
    existing = await db.execute(
        select(PayrollRun).where(
            PayrollRun.company_id == company_id,
            PayrollRun.period_start == period_start,
            PayrollRun.period_end == period_end,
            PayrollRun.deleted_at.is_(None)
        )
    )
    run = existing.scalars().first()
    if run:
        if run.status != 'draft':
            return run
        # Delete old line items
        await db.execute(
            sa.delete(PayrollLineItem).where(PayrollLineItem.payroll_run_id == run.id)
        )
    else:
        run = PayrollRun(
            company_id=company_id,
            period_start=period_start,
            period_end=period_end,
            status='draft',
            total_amount=Decimal('0'),
            currency='USD' # Assuming base currency
        )
        db.add(run)
        await db.flush()

    # 2. Get active employees and their compensation plans
    users_result = await db.execute(
        select(User).where(
            User.company_id == company_id,
            User.deleted_at.is_(None)
        )
    )
    users = users_result.scalars().all()
    
    total_run_amount = Decimal('0')
    
    for user in users:
        # Get active comp plan for the period (simplified: getting most recent one valid in this period)
        comp_result = await db.execute(
            select(CompensationPlan).where(
                CompensationPlan.user_id == user.id,
                CompensationPlan.effective_from <= period_end,
                sa.or_(CompensationPlan.effective_to.is_(None), CompensationPlan.effective_to >= period_start)
            ).order_by(CompensationPlan.effective_from.desc()).limit(1)
        )
        comp = comp_result.scalars().first()
        
        if not comp:
            continue
            
        base_salary = comp.base_salary * comp.fx_rate_to_base
        bonus_amount = Decimal('0')
        
        # Calculate bonus
        if comp.bonus_basis == 'Profit' or comp.bonus_basis == 'Margin':
            # Simplified: total margin generated by this buyer
            stats_result = await db.execute(
                select(sa.func.sum((CampaignRunStat.revenue - CampaignRunStat.spend) * CampaignRunStat.fx_rate_to_base))
                .join(CampaignRun, CampaignRunStat.campaign_run_id == CampaignRun.id)
                .where(
                    CampaignRun.buyer_id == user.id,
                    CampaignRunStat.stat_date >= period_start,
                    CampaignRunStat.stat_date <= period_end,
                    CampaignRunStat.deleted_at.is_(None),
                    CampaignRun.deleted_at.is_(None)
                )
            )
            profit = stats_result.scalar() or Decimal('0')
            if comp.quota_target and profit > comp.quota_target:
                bonus_amount = (profit - comp.quota_target) * (comp.bonus_percent / Decimal('100'))
            elif not comp.quota_target and profit > 0:
                bonus_amount = profit * (comp.bonus_percent / Decimal('100'))
                
        elif comp.bonus_basis == 'Revenue':
            stats_result = await db.execute(
                select(sa.func.sum(CampaignRunStat.revenue * CampaignRunStat.fx_rate_to_base))
                .join(CampaignRun, CampaignRunStat.campaign_run_id == CampaignRun.id)
                .where(
                    CampaignRun.buyer_id == user.id,
                    CampaignRunStat.stat_date >= period_start,
                    CampaignRunStat.stat_date <= period_end,
                    CampaignRunStat.deleted_at.is_(None),
                    CampaignRun.deleted_at.is_(None)
                )
            )
            revenue = stats_result.scalar() or Decimal('0')
            if comp.quota_target and revenue > comp.quota_target:
                bonus_amount = (revenue - comp.quota_target) * (comp.bonus_percent / Decimal('100'))
            elif not comp.quota_target and revenue > 0:
                bonus_amount = revenue * (comp.bonus_percent / Decimal('100'))
        
        # Round correctly
        base_salary = base_salary.quantize(Decimal("0.0001"))
        bonus_amount = bonus_amount.quantize(Decimal("0.0001"))
        total_amount = base_salary + bonus_amount
        total_run_amount += total_amount
        
        item = PayrollLineItem(
            payroll_run_id=run.id,
            user_id=user.id,
            base_amount=base_salary,
            bonus_amount=bonus_amount,
            total_amount=total_amount,
            currency='USD',
            status='draft'
        )
        db.add(item)
        
    run.total_amount = total_run_amount
    await db.flush()
    return run
