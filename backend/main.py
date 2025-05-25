import json
from datetime import datetime
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from backend.core.config import settings
from backend.api.v1.api import api_router

# Custom JSON encoder to handle datetime objects
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# Custom JSONResponse class using our encoder
class CustomJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            cls=CustomJSONEncoder,
        ).encode("utf-8")

# Create FastAPI app with custom JSON response class
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for managing Parliament TV video clips",
    version="1.0.0",
    default_response_class=CustomJSONResponse
)

# Configure CORS for frontend access
# In development, explicitly allow the frontend origin

# Define allowed origins - use settings value if available
allowed_origins_str = settings.CORS_ORIGINS if hasattr(settings, 'CORS_ORIGINS') else "http://localhost:3000,http://127.0.0.1:3000"
allowed_origins = allowed_origins_str.split(',')

# Check if wildcard is in the list
if "*" in allowed_origins:
    # If wildcard is present, allow all origins
    allow_origins_setting = ["*"]
    allow_origin_regex_setting = None
else:
    # Otherwise use the specific origins
    allow_origins_setting = allowed_origins
    allow_origin_regex_setting = None

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins_setting,
    allow_origin_regex=allow_origin_regex_setting,
    allow_credentials=True,   # Allow credentials when using specific origins
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,  # 24 hours cache for preflight requests
)

print(f"CORS configured with allowed origins: {allowed_origins}")

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT
    }

# Include routers
app.include_router(api_router, prefix=settings.API_V1_STR)

# Add a direct route for metrics at root level for Prometheus
@app.get("/metrics", response_class=PlainTextResponse)
async def root_metrics():
    # Import the metrics endpoint function
    from backend.api.v1.endpoints.metrics import get_metrics
    # Call and return the metrics
    return await get_metrics()

# Make sure the app is properly configured for testing
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
