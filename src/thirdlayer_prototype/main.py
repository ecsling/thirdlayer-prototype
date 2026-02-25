"""FastAPI server for metrics and transitions endpoints."""
from fastapi import FastAPI
from contextlib import asynccontextmanager

from thirdlayer_prototype.db.storage import Storage


storage: Storage | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage storage lifecycle."""
    global storage
    storage = Storage("thirdlayer.db")
    storage.connect()
    yield
    storage.close()


app = FastAPI(title="ThirdLayer Prototype", lifespan=lifespan)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "ThirdLayer Prototype",
        "description": "Agentic browser workflow predictor",
        "endpoints": [
            "/metrics",
            "/transitions/top?k=10",
        ],
    }


@app.get("/metrics")
async def get_metrics():
    """Get system metrics snapshot.
    
    Returns metrics about predictions, executions, and performance.
    """
    if not storage:
        return {"error": "storage_not_initialized"}
    
    total_transitions = storage.get_total_transition_count()
    recent_actions = storage.get_recent_actions(limit=5)
    
    return {
        "total_transitions_learned": total_transitions,
        "recent_actions_count": len(recent_actions),
        "database_path": storage.db_path,
    }


@app.get("/transitions/top")
async def get_top_transitions(k: int = 10):
    """Get top K most common transitions.
    
    Args:
        k: Number of transitions to return (default 10).
    
    Returns:
        List of transitions with from_action, to_action, and count.
    """
    if not storage:
        return {"error": "storage_not_initialized"}
    
    return storage.get_top_transitions(k=k)
