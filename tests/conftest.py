import fakeredis.aioredis
import pytest


@pytest.fixture
async def fake_redis():
    """Provides a fresh in-memory async FakeRedis instance for isolated testing."""
    server = fakeredis.FakeServer()
    client = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
    yield client
    await client.flushall()
    await client.aclose()
