import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_api_persistence_create(client_a: AsyncClient):
    create_res = await client_a.post('/api/v1/connectors/', json={
        'connector_name': 'keitaro_pers',
        'secret': 'some_secret_persist',
        'sync_interval_minutes': 15
    })
    assert create_res.status_code == 200
    connector_id = create_res.json()['id']
    
    list_res = await client_a.get('/api/v1/connectors/')
    assert list_res.status_code == 200
    connectors = list_res.json()
    
    found = [c for c in connectors if c['id'] == connector_id]
    assert len(found) == 1
    assert found[0]['connector_name'] == 'keitaro_pers'
    assert found[0]['sync_interval_minutes'] == 15

@pytest.mark.asyncio
async def test_api_persistence_patch_status(client_a: AsyncClient):
    create_res = await client_a.post('/api/v1/connectors/', json={
        'connector_name': 'patch_test_pers',
        'secret': 'sec',
        'sync_interval_minutes': 10
    })
    assert create_res.status_code == 200
    connector_id = create_res.json()['id']

    patch_res = await client_a.patch(f'/api/v1/connectors/{connector_id}', json={
        'status': 'paused'
    })
    assert patch_res.status_code == 200
    assert patch_res.json()['status'] == 'paused'

    list_res = await client_a.get('/api/v1/connectors/')
    found = [c for c in list_res.json() if c['id'] == connector_id]
    assert found[0]['status'] == 'paused'

@pytest.mark.asyncio
async def test_api_persistence_soft_delete(client_a: AsyncClient):
    create_res = await client_a.post('/api/v1/connectors/', json={
        'connector_name': 'delete_test_pers',
        'secret': 'del',
        'sync_interval_minutes': 10
    })
    assert create_res.status_code == 200
    connector_id = create_res.json()['id']

    del_res = await client_a.delete(f'/api/v1/connectors/{connector_id}')
    assert del_res.status_code == 204

    list_res = await client_a.get('/api/v1/connectors/')
    found = [c for c in list_res.json() if c['id'] == connector_id]
    assert len(found) == 0
