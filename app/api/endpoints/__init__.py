"""endpoints/__init__.py — Combined router that includes all sub-routers."""
from fastapi import APIRouter

from app.api.endpoints.artifacts import router as artifacts_router
from app.api.endpoints.logs import router as logs_router
from app.api.endpoints.outputs import router as outputs_router
from app.api.endpoints.pipeline import router as pipeline_router
from app.api.endpoints.rendering import router as rendering_router
from app.api.endpoints.scenes import router as scenes_router
from app.api.endpoints.sessions import router as sessions_router
from app.api.endpoints.status import router as status_router


router = APIRouter()
router.include_router(pipeline_router)
router.include_router(status_router)
router.include_router(outputs_router)
router.include_router(scenes_router)
router.include_router(rendering_router)
router.include_router(sessions_router)
router.include_router(artifacts_router)
router.include_router(logs_router)
