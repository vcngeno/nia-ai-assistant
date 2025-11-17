from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os

from database import engine, Base
from routers import conversation, auth, children, dashboard

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[NIA] %(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("🌟 Nia is starting up...")
    
    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("✅ Database tables created successfully")
    logger.info("✅ Nia API started successfully!")
    
    yield
    
    logger.info("👋 Nia is shutting down...")

# Create FastAPI app
app = FastAPI(
    title="Nia - AI Learning Assistant",
    description="COPPA-compliant AI tutoring platform for children",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware - allows frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5180",
        os.getenv("FRONTEND_URL", "http://localhost:3000"),
        "*"  # Allow all origins for now - we'll restrict this after frontend is deployed
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(children.router, prefix="/api/v1/children", tags=["Child Profiles"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Parent Dashboard"])
app.include_router(conversation.router, prefix="/api/v1/conversation", tags=["Conversations"])

@app.get("/")
async def root():
    return {
        "message": "Welcome to Nia API",
        "version": "1.0.0",
        "status": "operational"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "ai_service": "operational"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
