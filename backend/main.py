from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import settings
from backend.api.v1.api import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for managing Parliament TV video clips",
    version="1.0.0"
)

# Configure CORS for frontend access - simplified approach for development
# In a development environment, we'll allow all origins for easier debugging

# For Docker development, we need to allow all frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=False,  # Must be False when using wildcard origins
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,  # 24 hours cache for preflight requests
)

print("CORS configured with wildcard origins for development")

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
