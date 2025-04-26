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
# For development environment, we'll use a simpler CORS setup

# In development, we'll allow specific origins with credentials
if settings.ENVIRONMENT == "development":
    # Explicitly list all possible frontend origins for Docker networking
    allow_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://frontend:3000",
        "http://host.docker.internal:3000"
    ]
    
    # Add any additional origins from settings
    if settings.CORS_ORIGINS:
        for origin in settings.CORS_ORIGINS.split(","):
            origin = origin.strip()
            if origin and origin != "*" and origin not in allow_origins:
                allow_origins.append(origin)
    
    print(f"CORS allowed origins (development): {allow_origins}")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=86400,  # 24 hours cache for preflight requests
    )
else:
    # For production, we'll be more restrictive
    origins = settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS else []
    allow_origins = [origin.strip() for origin in origins if origin.strip() and origin.strip() != "*"]
    
    print(f"CORS allowed origins (production): {allow_origins}")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
        expose_headers=["Content-Length"],
        max_age=86400,  # 24 hours cache for preflight requests
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
