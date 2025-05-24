from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import psutil
import platform
import os
import json
from datetime import datetime, timedelta

from backend.api import deps
from backend.db.models.user import User, UserRole
from backend.services.system.docker_metrics import DockerMetrics

router = APIRouter()

@router.get("/info", response_model=Dict[str, Any])
async def get_system_info(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Get detailed system information.
    Only accessible to admin users.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    try:
        # Get Docker system info
        docker_info = DockerMetrics.get_system_info()
        
        # Get host system info
        system_info = {
            "os": {
                "name": platform.system(),
                "version": platform.version(),
                "platform": platform.platform(),
                "architecture": platform.machine()
            },
            "cpu": {
                "count": psutil.cpu_count(logical=True),
                "physical_count": psutil.cpu_count(logical=False),
                "usage_percent": psutil.cpu_percent(interval=0.1)
            },
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "used": psutil.virtual_memory().used,
                "percent": psutil.virtual_memory().percent
            },
            "disk": {
                "total": psutil.disk_usage('/').total,
                "used": psutil.disk_usage('/').used,
                "free": psutil.disk_usage('/').free,
                "percent": psutil.disk_usage('/').percent
            },
            "network": {
                "interfaces": list(psutil.net_if_addrs().keys()),
                "stats": {
                    interface: {
                        "bytes_sent": stats.bytes_sent,
                        "bytes_recv": stats.bytes_recv,
                        "packets_sent": stats.packets_sent,
                        "packets_recv": stats.packets_recv,
                        "errin": stats.errin,
                        "errout": stats.errout,
                        "dropin": stats.dropin,
                        "dropout": stats.dropout
                    } for interface, stats in psutil.net_io_counters(pernic=True).items()
                }
            },
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
            "uptime_seconds": int(datetime.now().timestamp() - psutil.boot_time())
        }
        
        # Merge Docker info with system info
        return {
            "host": system_info,
            "docker": docker_info.get("docker", {}),
            "containers": DockerMetrics.get_container_stats()
        }
    except Exception as e:
        # Log the error
        print(f"Error getting system info: {str(e)}")
        
        # Return basic info in case of error
        return {
            "host": {
                "os": {
                    "name": platform.system(),
                    "version": platform.version()
                },
                "error": str(e)
            }
        }

@router.get("/containers", response_model=Dict[str, Any])
async def get_containers(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Get container statistics.
    Only accessible to admin users.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    try:
        # Get container stats
        containers = DockerMetrics.get_container_stats()
        
        return {
            "containers": containers,
            "count": len(containers)
        }
    except Exception as e:
        # Log the error
        print(f"Error getting container stats: {str(e)}")
        
        # Return empty list in case of error
        return {
            "containers": [],
            "count": 0,
            "error": str(e)
        }

@router.get("/disk", response_model=Dict[str, Any])
async def get_disk_usage(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Get detailed disk usage statistics.
    Only accessible to admin users.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    try:
        # Get disk usage
        disk_usage = DockerMetrics.get_disk_usage()
        
        # Get storage breakdown
        storage_breakdown = DockerMetrics.get_storage_breakdown()
        
        # Merge disk usage with storage breakdown
        return {
            "volumes": disk_usage.get("volumes", {}),
            "total_volume_bytes": disk_usage.get("total_volume_bytes", 0),
            "breakdown": storage_breakdown,
            "host_disk": {
                "total": psutil.disk_usage('/').total,
                "used": psutil.disk_usage('/').used,
                "free": psutil.disk_usage('/').free,
                "percent": psutil.disk_usage('/').percent
            }
        }
    except Exception as e:
        # Log the error
        print(f"Error getting disk usage: {str(e)}")
        
        # Return basic info in case of error
        return {
            "volumes": {},
            "total_volume_bytes": 0,
            "breakdown": {
                "video_clips_bytes": 0,
                "capture_sessions_bytes": 0,
                "thumbnails_bytes": 0,
                "transcriptions_bytes": 0,
                "other_bytes": 0
            },
            "host_disk": {
                "total": 0,
                "used": 0,
                "free": 0,
                "percent": 0
            },
            "error": str(e)
        }

@router.get("/logs", response_model=Dict[str, Any])
async def get_system_logs(
    container: Optional[str] = None,
    lines: int = 100,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Get system logs from containers.
    Only accessible to admin users.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    try:
        # If container is specified, get logs for that container
        if container:
            logs = DockerMetrics.get_container_logs(container, lines)
            return {
                "container": container,
                "logs": logs,
                "count": len(logs)
            }
        
        # Otherwise, get container stats to list available containers
        containers = DockerMetrics.get_container_stats()
        container_names = [c.get("name") for c in containers]
        
        return {
            "available_containers": container_names,
            "message": "Specify a container name to get logs"
        }
    except Exception as e:
        # Log the error
        print(f"Error getting system logs: {str(e)}")
        
        # Return error message
        return {
            "error": str(e),
            "message": "Failed to get system logs"
        }

# These endpoints are now handled by the enhanced versions above

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
