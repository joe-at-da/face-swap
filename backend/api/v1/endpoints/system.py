from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from backend.api import deps
from backend.db.models.user import User, UserRole
from backend.services.system.docker_metrics import DockerMetrics

router = APIRouter()

@router.get("/info", response_model=Dict[str, Any])
async def get_system_info(
    current_user: User = Depends(deps.get_current_user),
):
    """
    Get detailed system information including Docker, CPU, memory, and disk.
    Only accessible to admin users.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    return DockerMetrics.get_system_info()

@router.get("/containers", response_model=List[Dict[str, Any]])
async def get_container_stats(
    current_user: User = Depends(deps.get_current_user),
):
    """
    Get statistics for all running Docker containers.
    Only accessible to admin users.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    return DockerMetrics.get_container_stats()

@router.get("/disk", response_model=Dict[str, Any])
async def get_disk_usage(
    current_user: User = Depends(deps.get_current_user),
):
    """
    Get disk usage statistics for Docker volumes and the host system.
    Only accessible to admin users.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    return DockerMetrics.get_disk_usage()

@router.get("/logs/{container_name}", response_model=List[Dict[str, Any]])
async def get_container_logs(
    container_name: str,
    lines: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Get logs from a specific container.
    Only accessible to admin users.
    
    Args:
        container_name: Name of the container
        lines: Number of log lines to retrieve (1-1000)
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    return DockerMetrics.get_container_logs(container_name, lines)

@router.get("/logs", response_model=List[Dict[str, Any]])
async def get_system_logs(
    lines: int = Query(100, ge=1, le=1000),
    level: Optional[str] = Query(None, description="Filter logs by level (info, warning, error)"),
    source: Optional[str] = Query(None, description="Filter logs by source container"),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Get system logs from all containers or filtered by source.
    Only accessible to admin users.
    
    Args:
        lines: Number of log lines to retrieve (1-1000)
        level: Filter logs by level (info, warning, error)
        source: Filter logs by source container
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    # Get container names
    containers = DockerMetrics.get_container_stats()
    container_names = [container["name"] for container in containers]
    
    # If source is specified, only get logs from that container
    if source and source in container_names:
        logs = DockerMetrics.get_container_logs(source, lines)
    else:
        # Get logs from all containers
        logs = []
        for container_name in container_names:
            container_logs = DockerMetrics.get_container_logs(container_name, lines // len(container_names))
            logs.extend(container_logs)
        
        # Sort by timestamp
        logs.sort(key=lambda x: x["timestamp"], reverse=True)
        
        # Limit to requested number of lines
        logs = logs[:lines]
    
    # Filter by level if specified
    if level:
        level = level.lower()
        filtered_logs = []
        
        for log in logs:
            message = log["message"].lower()
            
            # Simple heuristic to determine log level
            if level == "error" and ("error" in message or "exception" in message or "fail" in message):
                log["level"] = "error"
                filtered_logs.append(log)
            elif level == "warning" and ("warning" in message or "warn" in message):
                log["level"] = "warning"
                filtered_logs.append(log)
            elif level == "info" and not any(keyword in message for keyword in ["error", "exception", "fail", "warning", "warn"]):
                log["level"] = "info"
                filtered_logs.append(log)
        
        return filtered_logs
    
    # Add level to each log entry based on content
    for log in logs:
        message = log["message"].lower()
        if "error" in message or "exception" in message or "fail" in message:
            log["level"] = "error"
        elif "warning" in message or "warn" in message:
            log["level"] = "warning"
        else:
            log["level"] = "info"
    
    return logs
