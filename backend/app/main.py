import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.routes import router as api_router
from app.services.embedding_service import get_embedding_service
from app.services.vector_service import get_vector_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Warm up model and ChromaDB once on server boot
    print("🚀 Starting up DocChat backend...")
    get_embedding_service()
    get_vector_service()
    print("✨ DocChat backend is ready to accept requests.")
    yield
    print("🛑 Shutting down DocChat backend...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="DocChat — RAG-Powered PDF Assistant API",
    lifespan=lifespan,
)

# CORS configuration restricted strictly to allowed frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)

# Include API router under /api and root for robust client compatibility
app.include_router(api_router, prefix="/api")
app.include_router(api_router)

# Also provide direct health check at root /health
@app.get("/health", tags=["Health"])
async def root_health():
    return {"status": "ok"}

# Static files & SPA support for unified single-container deployment
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.config import PROJECT_ROOT, BACKEND_DIR

dist_candidates = [
    BACKEND_DIR / "frontend_dist",
    PROJECT_ROOT / "frontend" / "dist",
    Path("/app/frontend_dist"),
]
frontend_dist = next((p for p in dist_candidates if p.exists() and (p / "index.html").exists()), None)

if frontend_dist:
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        if full_path.startswith("api") or full_path in ("docs", "redoc", "openapi.json"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not Found")
        file_path = frontend_dist / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(frontend_dist / "index.html"))
else:
    @app.get("/", tags=["Root"])
    async def root():
        return {
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "status": "online",
            "docs_url": "/docs",
        }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", settings.PORT))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)

