"""FastAPI application entry point: creates the app and registers routers."""

from fastapi import FastAPI

from app.core.exceptions import AppError, app_error_handler
from app.core.telemetry import configure_telemetry
from app.routers.auth import router as auth_router
from app.routers.cart import router as cart_router
from app.routers.categories import router as categories_router
from app.routers.diagnostics import router as diagnostics_router
from app.routers.health import router as health_router
from app.routers.inventory import router as inventory_router
from app.routers.orders import router as orders_router
from app.routers.products import router as products_router
from app.routers.users import router as users_router

app = FastAPI(
    title="Cloud E-Commerce API",
    description="Cloud-native e-commerce backend built with FastAPI.",
    version="1.0.0",
)

# Application Insights, only when its connection string is set (on Azure).
configure_telemetry(app)

# Any AppError raised during a request (e.g. NotFoundError) becomes a JSON error response.
app.add_exception_handler(AppError, app_error_handler)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(products_router)
app.include_router(categories_router)
app.include_router(inventory_router)
app.include_router(cart_router)
app.include_router(orders_router)
app.include_router(diagnostics_router)
