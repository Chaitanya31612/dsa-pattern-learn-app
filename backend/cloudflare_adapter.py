"""Hosting boundary only. FastAPI routes, context, and scoring are reused as-is."""
import hmac
import json
import os
import time
from collections import deque


def binding(env, name, default=''):
    value = env.get(name, default) if isinstance(env, dict) else getattr(env, name, default)
    return str(value) if value is not None else default


class HostedAPI:
    def __init__(self, application):
        self.application = application
        self.configuration = None
        self.requests = deque()

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.application(scope, receive, send)
        env = scope.get('env', {})
        headers = dict(scope.get('headers', []))
        origin = headers.get(b'origin', b'').decode('latin-1')
        allowed = {s.strip() for s in binding(env, 'ALLOWED_ORIGINS').split(',') if s.strip()}
        cors = [(b'vary', b'Origin')]
        if origin and origin in allowed:
            cors += [(b'access-control-allow-origin', origin.encode()),
                     (b'access-control-allow-methods', b'GET, POST, OPTIONS'),
                     (b'access-control-allow-headers', b'Content-Type, Authorization')]

        async def reply(status, detail):
            await send({'type': 'http.response.start', 'status': status,
                        'headers': cors + [(b'content-type', b'application/json')]})
            await send({'type': 'http.response.body', 'body': b'' if status == 204 else json.dumps({'detail': detail}).encode()})

        if origin and origin not in allowed:
            return await reply(403, 'This website is not allowed to use this AI backend.')
        if scope['method'] == 'OPTIONS':
            return await reply(204, '')
        token = binding(env, 'AI_ACCESS_TOKEN')
        if len(token) < 32:
            return await reply(503, 'Set a Cloudflare AI_ACCESS_TOKEN secret of at least 32 characters.')
        if scope['path'] != '/api/health':
            provided = headers.get(b'authorization', b'')
            if not hmac.compare_digest(provided, ('Bearer ' + token).encode()):
                return await reply(401, 'Enter the hosted AI access key in application Settings, then retry.')
            # Best-effort per-isolate throttling, not an account-wide quota.
            now = time.monotonic()
            while self.requests and now - self.requests[0] >= 60:
                self.requests.popleft()
            try:
                limit = max(1, min(60, int(binding(env, 'AI_REQUESTS_PER_MINUTE', '12'))))
            except ValueError:
                limit = 12
            if len(self.requests) >= limit:
                return await reply(429, 'Too many AI requests. Wait a minute and retry.')
            self.requests.append(now)
        if scope['path'] in ('/api/process-leetcode', '/api/custom-problems'):
            return await reply(501, 'Custom problem fetching/storage uses the local Python server. Cloudflare hosts the AI endpoints only.')
        if not binding(env, 'GROQ_API_KEY') and not binding(env, 'GEMINI_API_KEY'):
            return await reply(503, 'Add a GROQ_API_KEY or GEMINI_API_KEY runtime secret in Cloudflare.')

        # Bindings are fixed for a deployed Worker version, never supplied by the
        # browser. Reuse the existing provider factory's environment contract.
        configuration = tuple(binding(env, key) for key in ('GROQ_API_KEY', 'GEMINI_API_KEY', 'DEFAULT_AI_MODEL'))
        if configuration != self.configuration:
            for key, value in zip(('GROQ_API_KEY', 'GEMINI_API_KEY', 'DEFAULT_AI_MODEL'), configuration):
                if value:
                    os.environ[key] = value
                else:
                    os.environ.pop(key, None)
            from app import get_analyzer
            get_analyzer.cache_clear()
            self.configuration = configuration

        # Check actual bytes as well as Content-Length; chunked bodies have no
        # trustworthy length header. Existing Pydantic field limits still apply.
        chunks = []
        size = 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            chunk = message.get('body', b'')
            size += len(chunk)
            if size > 128 * 1024:
                return await reply(413, 'Request too large. Keep your question or submitted attempt under 128 KB.')
            chunks.append(chunk)
            if not message.get('more_body', False):
                break
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type': 'http.request', 'body': b''.join(chunks), 'more_body': False}
            return await receive()

        async def with_cors(message):
            if message['type'] == 'http.response.start':
                # Replace the local app's permissive CORS headers at this hosted
                # boundary. Local Uvicorn continues to use the original app.
                message = {**message, 'headers': [
                    (k, v) for k, v in message.get('headers', [])
                    if not k.lower().startswith(b'access-control-')
                ] + cors}
            await send(message)

        await self.application(scope, replay, with_cors)
