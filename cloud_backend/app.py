"""ASGI entrypoint for Vercel. No server threads, timers, or writable disk."""
import json
import asyncio
import logging
import os
import ipaddress
from functools import lru_cache
from urllib.parse import urlparse, quote
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from sqlalchemy.exc import SQLAlchemyError
from .database import Database
from .security import CloudError
from .service import Service
from .persistence import Download

COOKIE = 'xuanhoa_session'


def client_address(request):
    # Only Vercel runtime configuration authorizes the platform-owned header.
    if os.environ.get('VERCEL') == '1':
        candidate = request.headers.get('x-vercel-forwarded-for', '').strip()
        try:
            return str(ipaddress.ip_address(candidate))
        except ValueError:
            return 'unverified-vercel-peer'
    return request.client.host if request.client else 'unknown'


def allowed_origins():
    explicit = os.environ.get('XH_PUBLIC_ORIGIN', '')
    origins = {explicit} if explicit else set()
    # Vercel's own environment variables are trusted server configuration, not
    # request headers. Never reflect an arbitrary Host/Origin into this list.
    origins.update('https://'+os.environ[key] for key in ('VERCEL_URL', 'VERCEL_PROJECT_PRODUCTION_URL') if os.environ.get(key))
    valid = set()
    for origin in origins:
        parsed = urlparse(origin)
        if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
            raise CloudError('Cấu hình tên miền cloud chưa hợp lệ.', 503, 'configuration_required')
        valid.add(origin)
    return valid


@lru_cache(maxsize=1)
def configured_service():
    url, secret = os.environ.get('XH_DATABASE_URL', ''), os.environ.get('XH_SESSION_SECRET', '')
    if not url or len(secret) < 32:
        raise CloudError('Chưa cấu hình kết nối Supabase cho bản cloud.', 503, 'configuration_required')
    if not allowed_origins():
        raise CloudError('Chưa cấu hình tên miền HTTPS.', 503, 'configuration_required')
    return Service(Database(url), secret)


def create_app(service=None, origins=None, *, testing=False):
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    # scrypt uses ~128 MiB per verification. Queue logins asynchronously so a
    # burst cannot exhaust memory or occupy all threads needed for attendance.
    login_slots = asyncio.Semaphore(2)

    @app.middleware('http')
    async def headers(request, call_next):
        response = await call_next(request)
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Permissions-Policy'] = 'camera=(self), microphone=(), geolocation=()'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'none'; object-src 'none'; base-uri 'self'"
        response.headers['Content-Security-Policy-Report-Only'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; font-src 'self'; worker-src 'self' blob:; media-src 'self' blob:; form-action 'self'"
        if request.url.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['Referrer-Policy'] = 'no-referrer'
        return response

    @app.exception_handler(CloudError)
    async def known_error(request, error):
        return JSONResponse({'error': str(error), 'code': error.code}, status_code=error.status,
            headers={'Retry-After': str(error.retry_after)} if hasattr(error, 'retry_after') else None)

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request, error):
        # SQLAlchemy exception strings can include URLs or personal parameters.
        logging.error('Cloud database operation failed (%s)', type(error).__name__)
        return JSONResponse({'error': 'Chưa kết nối được dữ liệu cloud. Thử lại sau.', 'code': 'database_unavailable'}, status_code=503)

    def backend():
        return service or configured_service()

    @app.get('/api/health')
    def health():
        try:
            backend()
        except CloudError:
            return JSONResponse({'status': 'configuration_required', 'stage': 'foundation'}, status_code=503)
        with backend().database.engine.connect() as db:
            ready = backend().readiness(db)['ready']
        return {'status':'ready' if ready else 'configured', 'stage':'cloud', 'readyForParishUse':ready}

    @app.get('/api/{action:path}')
    def read(action: str, request: Request):
        result = backend().get(action, request.cookies.get(COOKIE, ''), dict(request.query_params), client_address(request))
        if isinstance(result, Download):
            if len(result.content) > 4_000_000:
                raise CloudError('File quá lớn để tải một lượt. Dùng tải từng phần.', 413, 'download_too_large')
            return Response(result.content, media_type=result.content_type,
                headers={'Content-Disposition': "attachment; filename*=UTF-8''"+quote(result.filename, safe='')})
        return result

    @app.post('/api/{action:path}')
    async def write(action: str, request: Request):
        valid = set(origins) if origins is not None else allowed_origins()
        origin = request.headers.get('origin')
        current = str(request.base_url).rstrip('/')
        if origin not in valid or current not in valid:
            raise CloudError('Nguồn truy cập không hợp lệ.', 403, 'invalid_origin')
        if request.headers.get('content-type', '').split(';')[0].strip().lower() != 'application/json':
            raise CloudError('Yêu cầu cần định dạng JSON.', 415, 'invalid_content_type')
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 3_000_000:
                raise CloudError('Dữ liệu gửi quá lớn.', 413, 'payload_too_large')
        try:
            values = json.loads(body)
            if not isinstance(values, dict):
                raise ValueError()
        except (ValueError, UnicodeDecodeError):
            raise CloudError('Nội dung yêu cầu không hợp lệ.', 400, 'invalid_json')
        token = request.cookies.get(COOKIE, '')
        csrf = request.headers.get('x-csrf-token', '')
        instance = backend()
        if action == 'auth/login':
            async with login_slots:
                result = await run_in_threadpool(instance.login, values, client_address(request))
        else:
            result = await run_in_threadpool(instance.post, action, token, csrf, values, client_address(request))
        result = dict(result)
        # Preview tokens are optimistic-concurrency fingerprints, not sessions.
        new_token = result.pop('token', None) if action in ('auth/login','auth/password') else None
        response = JSONResponse(result)
        if new_token is not None:
            response.set_cookie(COOKIE, new_token, max_age=28800, path='/', secure=not testing,
                                httponly=True, samesite='strict')
        elif action == 'auth/logout':
            response.delete_cookie(COOKIE, path='/', secure=not testing, httponly=True, samesite='strict')
        return response

    # Vercel recognizes FastAPI static mounts. Local cloud development uses the
    # same built files; neither path includes the data directory or .local.
    assets = Path(__file__).resolve().parents[1] / 'dist'
    if assets.is_dir():
        app.mount('/', StaticFiles(directory=str(assets), html=True), name='web')
    return app


app = create_app()
