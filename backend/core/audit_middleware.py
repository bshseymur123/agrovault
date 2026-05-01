"""
Audit logging middleware.
Writes a row to audit_logs for every POST / PATCH / PUT / DELETE request
that returns a 2xx status. Extracts user_id from the JWT silently.
"""
import time
import json
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from jose import jwt, JWTError

from core.config import settings
from db.session import SessionLocal
from models.models import AuditLog


AUDIT_METHODS = {"POST", "PATCH", "PUT", "DELETE"}
SKIP_PATHS = {"/api/health", "/api/auth/token", "/api/auth/login"}


def _extract_user_id(request: Request) -> int | None:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return int(payload.get("sub", 0)) or None
    except (JWTError, ValueError):
        return None


def _parse_entity(path: str) -> tuple[str, int | None]:
    """Derive entity_type and entity_id from URL path."""
    parts = [p for p in path.split("/") if p]
    # e.g. ['api', 'shipments', '3', 'status']
    entity_type = "unknown"
    entity_id = None
    if len(parts) >= 2:
        entity_type = parts[1]  # shipments / transactions / customs / etc.
    if len(parts) >= 3:
        try:
            entity_id = int(parts[2])
        except ValueError:
            pass
    return entity_type, entity_id


def _action_from_method(method: str) -> str:
    return {"POST": "create", "PATCH": "update", "PUT": "update", "DELETE": "delete"}.get(method, method.lower())


class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Only log mutating requests that succeeded
        if (
            request.method in AUDIT_METHODS
            and response.status_code in range(200, 300)
            and request.url.path not in SKIP_PATHS
            and request.url.path.startswith("/api/")
        ):
            user_id = _extract_user_id(request)
            entity_type, entity_id = _parse_entity(request.url.path)
            action = _action_from_method(request.method)
            ip = request.client.host if request.client else None

            detail = f"{request.method} {request.url.path}"

            try:
                db = SessionLocal()
                db.add(AuditLog(
                    user_id=user_id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    action=action,
                    detail=detail,
                    ip_address=ip,
                ))
                db.commit()
                db.close()
            except Exception:
                pass  # Never let audit logging break the main request

        return response
