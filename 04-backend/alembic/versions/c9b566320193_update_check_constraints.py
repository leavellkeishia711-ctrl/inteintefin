"""update check constraints

Revision ID: c9b566320193
Revises: e8acf4873fc7
Create Date: 2026-08-01 19:24:28.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9b566320193'
down_revision: Union[str, Sequence[str], None] = '6033c46a54ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ad Accounts
    op.execute("ALTER TABLE ad_accounts DROP CONSTRAINT IF EXISTS check_ad_account_status")
    op.execute("ALTER TABLE ad_accounts ADD CONSTRAINT check_ad_account_status CHECK (status IN ('active', 'warming', 'banned', 'suspended'))")
    
    # Campaign Runs
    op.execute("ALTER TABLE campaign_runs DROP CONSTRAINT IF EXISTS check_campaign_run_status")
    op.execute("ALTER TABLE campaign_runs ADD CONSTRAINT check_campaign_run_status CHECK (status IN ('active', 'stopped', 'banned'))")
    
    # Consumables
    op.execute("ALTER TABLE consumables DROP CONSTRAINT IF EXISTS check_consumable_type")
    op.execute("ALTER TABLE consumables ADD CONSTRAINT check_consumable_type CHECK (type IN ('proxy', 'card', 'account_service', 'other'))")
    op.execute("ALTER TABLE consumables DROP CONSTRAINT IF EXISTS check_consumable_status")
    op.execute("ALTER TABLE consumables ADD CONSTRAINT check_consumable_status CHECK (status IN ('active', 'expired', 'burned'))")
    
    # Payroll Runs
    op.execute("ALTER TABLE payroll_runs DROP CONSTRAINT IF EXISTS check_payroll_run_status")
    op.execute("ALTER TABLE payroll_runs ADD CONSTRAINT check_payroll_run_status CHECK (status IN ('draft', 'approved', 'paid'))")
    
    # Payroll Line Items
    op.execute("ALTER TABLE payroll_line_items DROP CONSTRAINT IF EXISTS check_payroll_line_item_status")
    op.execute("ALTER TABLE payroll_line_items ADD CONSTRAINT check_payroll_line_item_status CHECK (status IN ('draft', 'approved', 'paid', 'held'))")
    
    # Decision Recommendations
    op.execute("ALTER TABLE decision_recommendations DROP CONSTRAINT IF EXISTS check_decision_status")
    op.execute("ALTER TABLE decision_recommendations ADD CONSTRAINT check_decision_status CHECK (status IN ('recommended', 'approved', 'executed', 'rejected'))")
    
    # Partner Payouts
    op.execute("ALTER TABLE partner_payouts DROP CONSTRAINT IF EXISTS check_partner_payout_status")
    op.execute("ALTER TABLE partner_payouts ADD CONSTRAINT check_partner_payout_status CHECK (status IN ('booked', 'in_hold', 'scrubbed', 'paid'))")


def downgrade() -> None:
    op.execute("ALTER TABLE ad_accounts DROP CONSTRAINT IF EXISTS check_ad_account_status")
    op.execute("ALTER TABLE ad_accounts ADD CONSTRAINT check_ad_account_status CHECK (status IN ('preparing', 'ready', 'active', 'banned', 'closed'))")
    
    op.execute("ALTER TABLE campaign_runs DROP CONSTRAINT IF EXISTS check_campaign_run_status")
    op.execute("ALTER TABLE campaign_runs ADD CONSTRAINT check_campaign_run_status CHECK (status IN ('active', 'paused', 'completed'))")
    
    op.execute("ALTER TABLE consumables DROP CONSTRAINT IF EXISTS check_consumable_type")
    op.execute("ALTER TABLE consumables ADD CONSTRAINT check_consumable_type CHECK (type IN ('proxy', 'domain', 'cloaking', 'vps', 'other'))")
    op.execute("ALTER TABLE consumables DROP CONSTRAINT IF EXISTS check_consumable_status")
    op.execute("ALTER TABLE consumables ADD CONSTRAINT check_consumable_status CHECK (status IN ('active', 'expired', 'replaced'))")
    
    op.execute("ALTER TABLE payroll_runs DROP CONSTRAINT IF EXISTS check_payroll_run_status")
    op.execute("ALTER TABLE payroll_runs ADD CONSTRAINT check_payroll_run_status CHECK (status IN ('draft', 'calculated', 'approved', 'paid'))")
    
    op.execute("ALTER TABLE payroll_line_items DROP CONSTRAINT IF EXISTS check_payroll_line_item_status")
    op.execute("ALTER TABLE payroll_line_items ADD CONSTRAINT check_payroll_line_item_status CHECK (status IN ('draft', 'approved', 'paid'))")
    
    op.execute("ALTER TABLE decision_recommendations DROP CONSTRAINT IF EXISTS check_decision_status")
    op.execute("ALTER TABLE decision_recommendations ADD CONSTRAINT check_decision_status CHECK (status IN ('recommended', 'applied', 'dismissed'))")
    
    op.execute("ALTER TABLE partner_payouts DROP CONSTRAINT IF EXISTS check_partner_payout_status")
    op.execute("ALTER TABLE partner_payouts ADD CONSTRAINT check_partner_payout_status CHECK (status IN ('booked', 'in_hold', 'scrubbed', 'paid', 'cancelled'))")
