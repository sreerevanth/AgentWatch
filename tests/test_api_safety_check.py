import asyncio

import pytest

from fastapi.testclient import TestClient

from agentwatch.api.server import create_app


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_safety_check_blocks_critical(client):
    res = client.post('/api/v1/safety/check', json={'command': 'rm -rf /', 'tool_name': 'bash'})
    assert res.status_code == 200
    data = res.json()
    assert data['blocked'] is True
    assert data['risk_level'] in ('critical', 'high')


def test_safety_check_allows_safe(client):
    res = client.post('/api/v1/safety/check', json={'command': 'echo hello', 'tool_name': 'bash'})
    assert res.status_code == 200
    data = res.json()
    assert data['blocked'] is False
    assert data['risk_level'] in ('safe', 'low')
