import pytest
import uuid
from decimal import Decimal
from datetime import datetime, date, timezone
from fastapi import HTTPException
from app.services.validation import validate_fk
from app.db.models.users import User, Team
from app.db.models.companies import Company
from app.db.models.campaigns import Campaign, CampaignRun, AdAccount
from app.db.models.finance import Transaction
from app.db.session import system_session

@pytest.mark.asyncio
async def test_validate_fk_logic():
    async with system_session() as db_session:
        company_id_1 = uuid.uuid4()
        company_id_2 = uuid.uuid4()
        
        c1 = Company(id=company_id_1, name='C1', base_currency='USD')
        c2 = Company(id=company_id_2, name='C2', base_currency='USD')
        db_session.add(c1)
        db_session.add(c2)
        
        team_c1 = Team(id=uuid.uuid4(), company_id=company_id_1, name='T1')
        ad_acc_c1 = AdAccount(id=uuid.uuid4(), company_id=company_id_1, platform='fb', external_account_id='FB1', status='active')
        campaign_c1 = Campaign(id=uuid.uuid4(), company_id=company_id_1)
        user_c1 = User(id=uuid.uuid4(), company_id=company_id_1, email=f'{uuid.uuid4()}@a.com', password_hash='hash', name='U1', role='owner')
        db_session.add_all([team_c1, ad_acc_c1, campaign_c1, user_c1])
        await db_session.flush()

        run_c1 = CampaignRun(id=uuid.uuid4(), company_id=company_id_1, campaign_id=campaign_c1.id, buyer_id=user_c1.id, started_at=datetime.now(timezone.utc), status='active')
        db_session.add(run_c1)
        
        tx_c1 = Transaction(id=uuid.uuid4(), company_id=company_id_1, type='expense', category='ad_spend', amount=Decimal('100'), currency='USD', fx_rate_to_base=Decimal('1'), occurred_on=date.today(), created_by=user_c1.id, source='manual')
        db_session.add(tx_c1)

        team_c2 = Team(id=uuid.uuid4(), company_id=company_id_2, name='T2')
        db_session.add(team_c2)

        team_c1_del = Team(id=uuid.uuid4(), company_id=company_id_1, name='T1_del')
        team_c1_del.deleted_at = datetime.now(timezone.utc)
        db_session.add(team_c1_del)

        await db_session.commit()

        # TEST: Valid (same company)
        await validate_fk(db_session, Team, team_c1.id, company_id_1, 'team_id')
        await validate_fk(db_session, AdAccount, ad_acc_c1.id, company_id_1, 'ad_account_id')
        await validate_fk(db_session, Campaign, campaign_c1.id, company_id_1, 'campaign_id')
        await validate_fk(db_session, User, user_c1.id, company_id_1, 'buyer_id')
        await validate_fk(db_session, CampaignRun, run_c1.id, company_id_1, 'campaign_run_id')
        await validate_fk(db_session, Transaction, tx_c1.id, company_id_1, 'transaction_id')

        # TEST: None is valid
        await validate_fk(db_session, Team, None, company_id_1, 'team_id')

        # TEST: Cross-tenant (returns 422)
        with pytest.raises(HTTPException) as exc1:
            await validate_fk(db_session, Team, team_c2.id, company_id_1, 'team_id')
        assert exc1.value.status_code == 422
        assert 'team_id' in exc1.value.detail

        # TEST: Soft-deleted (returns 422)
        with pytest.raises(HTTPException) as exc2:
            await validate_fk(db_session, Team, team_c1_del.id, company_id_1, 'team_id')
        assert exc2.value.status_code == 422

        # TEST: Not found (returns 422)
        with pytest.raises(HTTPException) as exc3:
            await validate_fk(db_session, Team, uuid.uuid4(), company_id_1, 'team_id')
        assert exc3.value.status_code == 422
