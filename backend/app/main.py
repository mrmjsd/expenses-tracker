from fastapi import FastAPI
from app.api.v1.endpoints.main import api_router  # Correct import path
from app.core.config import settings
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware
import logging

def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"
logger = logging.getLogger(__name__)
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
    debug=True
)
# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
# Include the API router with the correct prefix
app.include_router(api_router, prefix=settings.API_V1_STR)
