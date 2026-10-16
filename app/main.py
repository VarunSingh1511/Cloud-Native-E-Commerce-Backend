"""FastAPI application entry point: creates the app and registers routers."""

from fastapi import FastAPI

from app.core.exceptions import AppError, app_error_handler
from app.routers.health import router as health_router
from app.routers.products import router as products_router

app = FastAPI(
    title="Cloud E-Commerce API",
    description="Cloud-native e-commerce backend built with FastAPI.",
    version="0.3.0",
)

# Any AppError raised during a request (e.g. NotFoundError) becomes a JSON error response.
app.add_exception_handler(AppError, app_error_handler)

app.include_router(health_router)
app.include_router(products_router)
