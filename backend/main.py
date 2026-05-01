import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from core.config import settings
from db.session import Base, engine
from core.audit_middleware import AuditLogMiddleware
from api.routers.auth import router as auth_router
from api.routers.shipments import router as shipments_router
from api.routers.operations import (
    qc_router, customs_router, txn_router, analytics_router, storage_router
)
from api.routers.documents import router as documents_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    import db.session as _db
    _db.Base.metadata.create_all(bind=_db.engine)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Agricultural Fresh Produce Trade Operations Platform",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuditLogMiddleware)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": str(exc)})


# Register all routers
app.include_router(auth_router)
app.include_router(shipments_router)
app.include_router(qc_router)
app.include_router(customs_router)
app.include_router(txn_router)
app.include_router(analytics_router)
app.include_router(documents_router)
app.include_router(storage_router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}
