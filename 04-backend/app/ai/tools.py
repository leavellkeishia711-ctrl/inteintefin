from pydantic import BaseModel, Field, conint, computed_field
from typing import Optional, Literal, List, Dict, Any
from datetime import date, timedelta
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.pnl import calculate_pnl
from app.services.cashflow import calculate_cashflow
from app.services.metrics import get_health_score, get_spend_discrepancy
from app.services.campaigns import get_campaign_stats, get_ad_account_cost
from app.services.transactions import get_transactions
import json

class ToolArgument(BaseModel):
    pass

class GetPnLArgs(ToolArgument):
    date_from: date = Field(..., description="Start date for PnL calculation.")
    date_to: date = Field(..., description="End date for PnL calculation.")
    group_by: Optional[Literal["day", "week", "month"]] = Field(None, description="Granularity of grouping.")

class GetCashflowArgs(ToolArgument):
    date_from: date = Field(..., description="Start date.")
    date_to: date = Field(..., description="End date.")

class GetMetricsArgs(ToolArgument):
    date_from: date = Field(..., description="Start date.")
    date_to: date = Field(..., description="End date.")

class GetCampaignStatsArgs(ToolArgument):
    date_from: date = Field(..., description="Start date.")
    date_to: date = Field(..., description="End date.")
    ad_account_id: Optional[UUID] = None
    campaign_run_id: Optional[UUID] = None
    limit: conint(ge=1, le=100) = Field(50, description="Max number of records.") # type: ignore

class GetTransactionsArgs(ToolArgument):
    date_from: date = Field(..., description="Start date.")
    date_to: date = Field(..., description="End date.")
    category: Optional[str] = None
    type: Optional[Literal["income", "expense"]] = None
    limit: conint(ge=1, le=100) = Field(50, description="Max number of records.") # type: ignore

class GetConsumablesCostArgs(ToolArgument):
    date_from: date = Field(..., description="Start date.")
    date_to: date = Field(..., description="End date.")
    ad_account_id: UUID = Field(..., description="Ad Account ID.")

# Max period validation
def validate_dates(date_from: date, date_to: date):
    if (date_to - date_from).days > 366:
        raise ValueError("Requested period exceeds maximum allowed range (366 days).")

def truncate_response(data: str, max_length: int = 4000) -> str:
    if len(data) > max_length:
        return data[:max_length] + "... (truncated due to size limits)"
    return data

def make_json(data: Any) -> str:
    # Use default string cast for Decimals and UUIDs
    return json.dumps(data, default=str)

async def execute_tool(tool_name: str, arguments: dict, db: AsyncSession, company_id: UUID | str) -> tuple[bool, Any]:
    try:
        c_id = UUID(company_id) if isinstance(company_id, str) else company_id

        if tool_name == "get_pnl_report":
            args = GetPnLArgs(**arguments)
            validate_dates(args.date_from, args.date_to)
            pnl = await calculate_pnl(db, c_id, args.date_from, args.date_to)
            return True, {"pnl": pnl}
            
        elif tool_name == "get_cash_flow":
            args = GetCashflowArgs(**arguments)
            validate_dates(args.date_from, args.date_to)
            cf = await calculate_cashflow(db, c_id, args.date_to)
            return True, {"cash_flow": cf}
            
        elif tool_name == "get_financial_summary":
            args = GetMetricsArgs(**arguments)
            validate_dates(args.date_from, args.date_to)
            hs = await get_health_score(db, c_id, as_of_date=args.date_to)
            discrepancy = await get_spend_discrepancy(db, c_id, args.date_from, args.date_to)
            return True, {"health_score": hs, "spend_discrepancy": discrepancy}
            
        elif tool_name == "get_campaign_metrics":
            args = GetCampaignStatsArgs(**arguments)
            validate_dates(args.date_from, args.date_to)
            stats = await get_campaign_stats(
                db, c_id, args.date_from, args.date_to, 
                campaign_run_id=args.campaign_run_id, 
                ad_account_id=args.ad_account_id, 
                limit=args.limit
            )
            return True, [
                {
                    "stat_date": s.stat_date,
                    "spend": s.spend,
                    "revenue": s.revenue,
                    "currency": s.currency,
                    "source": s.source
                } for s in stats
            ]
            
        else:
            return False, f"Error: Unknown tool {tool_name}"
            
    except Exception as e:
        # Do not expose internal exceptions to the LLM (security requirement)
        import logging
        logging.getLogger(__name__).error(f"Tool Execution Error ({tool_name}): {str(e)}")
        return False, "Internal error during tool execution."

# Define the tools spec for Anthropic
def get_tools_spec() -> List[Dict[str, Any]]:
    return [
        {
            "name": "get_pnl_report",
            "description": "Get Profit and Loss statement for a date range.",
            "input_schema": GetPnLArgs.model_json_schema()
        },
        {
            "name": "get_cash_flow",
            "description": "Get cash flow metrics for a date range.",
            "input_schema": GetCashflowArgs.model_json_schema()
        },
        {
            "name": "get_financial_summary",
            "description": "Get health score and ROI metrics.",
            "input_schema": GetMetricsArgs.model_json_schema()
        },
        {
            "name": "get_campaign_metrics",
            "description": "Get campaign performance statistics.",
            "input_schema": GetCampaignStatsArgs.model_json_schema()
        }
    ]
