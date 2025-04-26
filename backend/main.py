from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import settings
from backend.api.v1.api import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for managing Parliament TV video clips",
    version="1.0.0"
)

# Configure CORS for frontend access
# When using credentials, we can't use wildcard origins
origins = settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS else ["http://localhost:3000"]
# Remove any wildcard entries as they're not compatible with credentials
origins = [origin for origin in origins if origin != "*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT
    }

# Include routers
app.include_router(api_router, prefix=settings.API_V1_STR)

# Make sure the app is properly configured for testing
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
