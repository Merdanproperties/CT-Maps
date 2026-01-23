"""
Remediation API - Allows frontend to trigger automatic fixes on backend
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import subprocess
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter()

class RemediationRequest(BaseModel):
    action: str
    params: dict = {}

class RemediationResponse(BaseModel):
    success: bool
    message: str
    executed_commands: list[str] = []

@router.post("/restart-backend", response_model=RemediationResponse)
async def restart_backend():
    """
    Restart the backend server
    Note: This will only work if running under a process manager
    """
    try:
        # Try to restart via process manager
        project_root = Path(__file__).parent.parent.parent.parent
        restart_script = project_root / "scripts" / "restart_backend.sh"
        
        if restart_script.exists():
            result = subprocess.run(
                ["bash", str(restart_script)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return RemediationResponse(
                    success=True,
                    message="Backend restart initiated",
                    executed_commands=[f"Executed: {restart_script}"]
                )
            else:
                return RemediationResponse(
                    success=False,
                    message=f"Restart script failed: {result.stderr}",
                    executed_commands=[f"Attempted: {restart_script}"]
                )
        else:
            return RemediationResponse(
                success=False,
                message="Restart script not found. Please restart manually.",
                executed_commands=[]
            )
    except Exception as e:
        logger.error(f"Backend restart failed: {e}")
        return RemediationResponse(
            success=False,
            message=f"Restart failed: {str(e)}",
            executed_commands=[]
        )

@router.post("/reconnect-database", response_model=RemediationResponse)
async def reconnect_database():
    """
    Force database reconnection
    """
    try:
        from database import engine
        
        # Dispose and recreate connection pool
        engine.dispose()
        
        # Test new connection
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        return RemediationResponse(
            success=True,
            message="Database connection pool refreshed successfully",
            executed_commands=["engine.dispose()", "Tested new connection"]
        )
    except Exception as e:
        logger.error(f"Database reconnection failed: {e}")
        return RemediationResponse(
            success=False,
            message=f"Database reconnection failed: {str(e)}",
            executed_commands=[f"Error: {str(e)}"]
        )

@router.post("/check-postgres", response_model=RemediationResponse)
async def check_postgres():
    """
    Check if PostgreSQL is running and accessible
    """
    try:
        result = subprocess.run(
            ["psql", "-l"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            return RemediationResponse(
                success=True,
                message="PostgreSQL is running and accessible",
                executed_commands=["psql -l"]
            )
        else:
            return RemediationResponse(
                success=False,
                message="PostgreSQL is not accessible. Please start PostgreSQL.",
                executed_commands=["psql -l (failed)"]
            )
    except FileNotFoundError:
        return RemediationResponse(
            success=False,
            message="psql command not found. PostgreSQL may not be installed.",
            executed_commands=[]
        )
    except Exception as e:
        return RemediationResponse(
            success=False,
            message=f"PostgreSQL check failed: {str(e)}",
            executed_commands=[f"Error: {str(e)}"]
        )

@router.post("/execute", response_model=RemediationResponse)
async def execute_remediation(request: RemediationRequest):
    """
    Execute a remediation action
    """
    action_map = {
        "restart_backend": restart_backend,
        "reconnect_database": reconnect_database,
        "check_postgres": check_postgres,
    }
    
    if request.action not in action_map:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown remediation action: {request.action}"
        )
    
    return await action_map[request.action]()
