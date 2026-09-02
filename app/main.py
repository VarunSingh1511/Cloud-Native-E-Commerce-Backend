"""FastAPI application entry point."""

from fastapi import FastAPI

from app.routers.products import router as products_router

app = FastAPI(
    title="Cloud E-Commerce API",
    description="Week 1 FastAPI REST API using temporary in-memory product data.",
    version="0.1.0",
)

app.include_router(products_router)


@app.get("/", tags=["Health"], summary="Check that the API is running")
def read_root() -> dict[str, str]:
    """Provide a lightweight endpoint for confirming the application is online."""
    return {"message": "Cloud E-Commerce API is running"}
