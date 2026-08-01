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
