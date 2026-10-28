"""Hosting boundary checks; existing course tests cover the reused teaching API."""
import asyncio
import importlib.util
import json
from pathlib import Path

import httpx
import pytest

import app
from cloudflare_adapter import HostedAPI

TOKEN = 'test-personal-access-' + 'a' * 32
ORIGIN = 'https://learning.example'


@pytest.fixture(autouse=True)
def restore_environment(monkeypatch):
    for key in ('GROQ_API_KEY', 'GEMINI_API_KEY', 'DEFAULT_AI_MODEL'):
        monkeypatch.setenv(key, 'before-test')
    yield
    app.get_analyzer.cache_clear()


def client_for(env=None):
    bindings = {'AI_ACCESS_TOKEN': TOKEN, 'GROQ_API_KEY': 'synthetic-not-a-real-key', 'ALLOWED_ORIGINS': ORIGIN}
    bindings.update(env or {})

    async def original(scope, receive, send):
        await receive()
        await send({'type': 'http.response.start', 'status': 200,
                    'headers': [(b'access-control-allow-origin', b'*')]})
        await send({'type': 'http.response.body', 'body': b'{"original_app":true}'})

    hosted = HostedAPI(original)

    async def with_bindings(scope, receive, send):
        scope['env'] = bindings
        await hosted(scope, receive, send)

    return httpx.AsyncClient(transport=httpx.ASGITransport(app=with_bindings), base_url='http://worker.test')


def test_missing_or_wrong_personal_key_is_rejected():
    async def check():
        async with client_for() as client:
            assert (await client.post('/api/ai/software-chat')).status_code == 401
            assert (await client.post('/api/ai/software-chat', headers={'Authorization': 'Bearer wrong'})).status_code == 401
    asyncio.run(check())


def test_unconfigured_worker_fails_closed():
    async def check():
        async with client_for({'AI_ACCESS_TOKEN': ''}) as client:
            assert (await client.get('/api/health')).status_code == 503
        async with client_for({'GROQ_API_KEY': '', 'GEMINI_API_KEY': ''}) as client:
            assert (await client.get('/api/health')).status_code == 503
    asyncio.run(check())


def test_authorized_request_reaches_original_app_and_replaces_wildcard_cors():
    async def check():
        async with client_for() as client:
            result = await client.post('/api/hld/evaluate', json={'example': 'unchanged'},
                                       headers={'Authorization': f'Bearer {TOKEN}', 'Origin': ORIGIN})
            assert result.json() == {'original_app': True}
            assert result.headers['access-control-allow-origin'] == ORIGIN
    asyncio.run(check())


def test_health_and_preflight_need_no_personal_key_but_unknown_origins_fail():
    async def check():
        async with client_for() as client:
            assert (await client.get('/api/health')).status_code == 200
            result = await client.options('/api/hld/evaluate', headers={'Origin': ORIGIN})
            assert result.status_code == 204 and not result.content
            assert 'Authorization' in result.headers['access-control-allow-headers']
            result = await client.get('/api/health', headers={'Origin': 'https://other.example'})
            assert result.status_code == 403
            assert 'access-control-allow-origin' not in result.headers
    asyncio.run(check())


def test_large_chunked_body_is_rejected():
    async def chunks():
        for _ in range(3):
            yield b'x' * 65536

    async def check():
        async with client_for() as client:
            result = await client.post('/api/hld/evaluate', content=chunks(), headers={'Authorization': f'Bearer {TOKEN}'})
            assert result.status_code == 413
    asyncio.run(check())


def test_per_instance_throttle_and_local_only_routes():
    async def check():
        headers = {'Authorization': f'Bearer {TOKEN}'}
        async with client_for({'AI_REQUESTS_PER_MINUTE': '1'}) as client:
            assert (await client.post('/api/hld/evaluate', headers=headers)).status_code == 200
            assert (await client.post('/api/hld/evaluate', headers=headers)).status_code == 429
        async with client_for() as client:
            assert (await client.post('/api/process-leetcode', headers=headers)).status_code == 501
    asyncio.run(check())


def test_build_packages_original_sources_and_never_local_secrets(tmp_path, monkeypatch):
    backend = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location('worker_prepare', backend / 'cloudflare/prepare.py')
    prepare = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prepare)
    monkeypatch.setattr(prepare, 'BUILD', tmp_path / 'build')
    build = prepare.prepare()
    for name in ('app.py', 'hld_api.py', 'software_api.py', 'ai_learning_api.py'):
        assert (build / 'src' / name).read_bytes() == (backend / name).read_bytes()
    assert not (build / 'src/.env').exists()
    assert not (build / 'src/requirements.txt').exists()
    assert not (build / 'src/pipeline/fetch_leetcode.py').exists()
    assert len(list((build / 'src/pipeline/data').glob('*.json'))) == 4


def test_deployment_origins_stay_in_private_configuration(tmp_path, monkeypatch):
    backend = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location('private_worker_prepare', backend / 'cloudflare/prepare.py')
    prepare = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prepare)
    config = tmp_path / 'config'
    config.mkdir()
    for name in ('wrangler.jsonc', 'pyproject.toml', 'uv.lock', 'pylock.toml'):
        (config / name).write_bytes((backend / 'cloudflare' / name).read_bytes())
    monkeypatch.setattr(prepare, 'CONFIG', config)
    monkeypatch.setattr(prepare, 'BUILD', tmp_path / 'build')
    monkeypatch.delenv('CLOUDFLARE_ALLOWED_ORIGINS', raising=False)

    build = prepare.prepare()
    defaults = json.loads((build / 'wrangler.jsonc').read_text())
    assert defaults['vars']['ALLOWED_ORIGINS'] == 'http://127.0.0.1:5173,http://localhost:5173'

    private = config / 'wrangler.local.json'
    private.write_text(json.dumps({'vars': {'ALLOWED_ORIGINS': 'https://private.example'}}))
    prepare.prepare()
    assert json.loads((build / 'wrangler.jsonc').read_text())['vars']['ALLOWED_ORIGINS'] == 'https://private.example'
    assert not (build / 'src/wrangler.local.json').exists()

    monkeypatch.setenv('CLOUDFLARE_ALLOWED_ORIGINS', 'https://ci.example')
    prepare.prepare()
    assert json.loads((build / 'wrangler.jsonc').read_text())['vars']['ALLOWED_ORIGINS'] == 'https://ci.example'

    private.write_text(json.dumps({'vars': {'GROQ_API_KEY': 'synthetic-only'}}))
    with pytest.raises(ValueError, match='secrets'):
        prepare.prepare()
