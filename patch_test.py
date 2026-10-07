import re

file_path = '04-backend/tests/test_pr_a_data_integrity.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add the import if not exists
if "from app.db.models.companies import Company" not in content:
    content = content.replace("from app.db.models.campaigns import CampaignRunStat, CampaignRun, ExternalCampaignMapping",
                              "from app.db.models.campaigns import CampaignRunStat, CampaignRun, ExternalCampaignMapping\nfrom app.db.models.companies import Company")

old_block = """    with patch("app.connectors.tiktok_ads.resolve_fx_rate", autospec=True) as mock_fx:
        mock_fx.return_value = Decimal("1.10000000")
        async with tenant_session(comp_id) as db:
            await connector.upsert(db, [record])
            await db.commit()
        
        mock_fx.assert_awaited_once()
        args = mock_fx.call_args.args
        assert args[1:] == ("EUR", "USD", date(2023, 1, 1))

    async with system_session() as db_session:
        stats = (await db_session.execute(select(CampaignRunStat).where(CampaignRunStat.external_id == "tk123"))).scalars().all()
        assert len(stats) == 1"""

new_block = """    with patch("app.connectors.tiktok_ads.resolve_fx_rate", autospec=True) as mock_fx:
        mock_fx.return_value = Decimal("1.10000000")
        async with tenant_session(comp_id) as db:
            company = await db.scalar(select(Company).where(Company.id == uuid.UUID(comp_id)))
            assert company is not None
            assert company.base_currency
            expected_base = company.base_currency
            await connector.upsert(db, [record])
            await db.commit()
            
            mock_fx.assert_awaited_once()
            args = mock_fx.call_args.args
            assert args[0] is db
            assert args[1:] == ("EUR", expected_base, date(2023, 1, 1))

    async with system_session() as db_session:
        stats = (await db_session.execute(
            select(CampaignRunStat).where(
                CampaignRunStat.external_id == "tk123",
                CampaignRunStat.company_id == uuid.UUID(comp_id)
            )
        )).scalars().all()
        assert len(stats) == 1
        assert stats[0].fx_rate_to_base == Decimal("1.10000000")"""

if old_block in content:
    content = content.replace(old_block, new_block)
else:
    print("WARNING: Old block not found!")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
