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

def format_log_source(source: str) -> str:
    """Format log source to be more descriptive"""
    if not source:
        return "system"
        
    # Map numeric sources to more descriptive names
    if source.isdigit():
        process_map = {
            "1": "init",
            "131": "syslogd",
            "0": "kernel",
            "80": "httpd",
            "3306": "mysql",
            "5432": "postgresql"
        }
        return process_map.get(source, f"process-{source}")
    
    # Map common source names to more user-friendly names
    source_map = {
        "app": "application",
        "sys": "system",
        "db": "database",
        "auth": "authentication",
        "net": "network",
        "api": "api-server",
        "web": "web-server",
        "ui": "user-interface"
    }
    return source_map.get(source.lower(), source)


def format_log_message(message: str) -> str:
    """Clean up and format log messages"""
    if not message:
        return "No message provided"
    
    # Remove leading colons, brackets, etc.
    message = message.strip()
    if message.startswith(':'):
        message = message[1:].strip()
    
    # Remove redundant prefixes
    prefixes_to_remove = [
        "INFO: ", "WARNING: ", "ERROR: ", 
        "DEBUG: ", "NOTICE: ", "ALERT: ",
        "[INFO] ", "[WARNING] ", "[ERROR] ", 
        "[DEBUG] ", "[NOTICE] ", "[ALERT] "
    ]
    
    for prefix in prefixes_to_remove:
        if message.startswith(prefix):
            message = message[len(prefix):].strip()
    
    return message


@router.get("/logs", response_model=Dict[str, Any])
async def get_system_logs(
    container: Optional[str] = None,
    lines: int = 100,
    level: Optional[str] = None,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Get system logs from containers or application logs.
    Only accessible to admin users.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    try:
        # Get application logs when no specific container is requested
        if not container:
            logs = get_application_logs(lines)
            
            # Filter by level if specified
            if level and level.lower() != 'all':
                logs = [log for log in logs if log.get('level', '').lower() == level.lower()]
            
            # Format logs for frontend display
            formatted_logs = []
            for log in logs:
                formatted_logs.append({
                    "id": hash(f"{log.get('timestamp', '')}-{log.get('message', '')}") % 10000000,  # Generate stable ID
                    "timestamp": log.get("timestamp", datetime.now().isoformat()),
                    "level": log.get("level", "info").lower(),
                    "message": format_log_message(log.get("message", "")),
                    "source": format_log_source(log.get("source", "")),
                    "user": log.get("user", "System")
                })
            
            return {
                "items": formatted_logs,
                "total": len(formatted_logs),
                "source": "application"
            }
        
        # If specific container is requested, get container logs
        logs = DockerMetrics.get_container_logs(container, lines)
        
        # Format container logs for frontend display
        formatted_logs = []
        for i, log in enumerate(logs):
            # Extract level from message if possible
            log_level = "info"
            if "error" in log.get("message", "").lower():
                log_level = "error"
            elif "warn" in log.get("message", "").lower():
                log_level = "warning"
                
            formatted_logs.append({
                "id": i + 1,
                "timestamp": log.get("timestamp", datetime.now().isoformat()),
                "level": log.get("level", log_level).lower(),
                "message": format_log_message(log.get("message", "")),
                "source": format_log_source(log.get("source", container)),
                "user": "System"
            })
        
        return {
            "items": formatted_logs,
            "total": len(formatted_logs),
            "container": container
        }
    except Exception as e:
        # Log the error
        print(f"Error getting system logs: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Return error message with some sample logs so the UI isn't empty
        error_logs = [{
            "id": 1,
            "timestamp": datetime.now().isoformat(),
            "level": "error",
            "message": format_log_message(f"Failed to get system logs: {str(e)}"),
            "source": format_log_source("api"),
            "user": "System"
        }]
        
        return {
            "items": error_logs,
            "total": len(error_logs),
            "error": str(e)
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
    
    try:
        # Try to get logs from Docker containers
        logs = get_docker_logs(lines, source)
    except Exception as e:
        print(f"Error getting system logs: {str(e)}")
        # Fallback to application logs if Docker isn't available
        logs = get_application_logs(lines)
    
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

def get_docker_logs(lines: int, source: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get logs from Docker containers"""
    # Get container names
    containers = DockerMetrics.get_container_stats()
    container_names = [container["name"] for container in containers]
    
    # If source is specified, only get logs from that container
    if source and source in container_names:
        logs = DockerMetrics.get_container_logs(source, lines)
    else:
        # Get logs from all containers
        logs = []
        if container_names:
            for container_name in container_names:
                container_logs = DockerMetrics.get_container_logs(container_name, lines // max(len(container_names), 1))
                logs.extend(container_logs)
        
        # Sort by timestamp
        logs.sort(key=lambda x: x["timestamp"], reverse=True)
        
        # Limit to requested number of lines
        logs = logs[:lines]
    
    return logs

def get_application_logs(lines: int) -> List[Dict[str, Any]]:
    """Generate application logs from system logs and application events"""
    import logging
    import os
    import re
    from datetime import datetime, timedelta
    import subprocess
    
    logs = []
    
    # Try to read application log files
    log_files = [
        "/app/logs/app.log",
        "/app/log/app.log",
        "/var/log/app.log",
        "./logs/app.log",
        "/var/log/syslog",
        "/var/log/messages",
        "/var/log/system.log",  # macOS system log
        "./backend/logs/app.log"
    ]
    
    # Try to get logs from the system
    for log_file in log_files:
        if os.path.exists(log_file) and os.path.isfile(log_file):
            try:
                with open(log_file, "r") as f:
                    # Read the last N lines
                    file_lines = f.readlines()
                    log_lines = file_lines[-lines:] if len(file_lines) > lines else file_lines
                    
                    for line in log_lines:
                        line = line.strip()
                        if not line:
                            continue
                            
                        # Try to parse timestamp and level from the log line
                        timestamp = datetime.now().isoformat()
                        level = "info"
                        source = os.path.basename(log_file).replace(".log", "")
                        message = line
                        
                        # Common log formats:
                        # 1. Timestamp + hostname + process[pid]: message
                        # 2. Timestamp [source] message
                        # 3. [source] timestamp: message
                        
                        # Try to extract timestamp if it exists (common format: 2023-05-25 15:54:31)
                        timestamp_match = re.search(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', line)
                        if timestamp_match:
                            try:
                                timestamp_str = timestamp_match.group(0).replace(' ', 'T')
                                timestamp = timestamp_str
                                message = line[timestamp_match.end():].strip()
                            except Exception:
                                pass
                        
                        # Try to extract timestamp in syslog format (May 25 15:51:02)
                        if not timestamp_match:
                            syslog_match = re.search(r'([A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})', line)
                            if syslog_match:
                                try:
                                    # Convert to ISO format with current year
                                    syslog_time = syslog_match.group(1)
                                    current_year = datetime.now().year
                                    parsed_time = datetime.strptime(f"{current_year} {syslog_time}", "%Y %b %d %H:%M:%S")
                                    timestamp = parsed_time.isoformat()
                                    message = line[syslog_match.end():].strip()
                                except Exception:
                                    pass
                        
                        # Try to extract log level
                        level_patterns = {
                            "error": ["error", "err", "fatal", "crit", "emerg", "alert"],
                            "warning": ["warn", "warning"],
                            "info": ["info", "notice", "debug"]
                        }
                        
                        for lvl, patterns in level_patterns.items():
                            if any(pattern in line.lower() for pattern in patterns):
                                level = lvl
                                break
                        
                        # Try to extract source and message from common patterns
                        
                        # Pattern: hostname process[pid]: message
                        hostname_process_match = re.search(r'\s+([\w\-\.]+)\s+([\w\-\.]+)\[(\d+)\]:\s*(.*)', message)
                        if hostname_process_match:
                            hostname = hostname_process_match.group(1)
                            process = hostname_process_match.group(2)
                            pid = hostname_process_match.group(3)
                            source = process
                            message = hostname_process_match.group(4).strip()
                            
                            # Remove any leading colons from the message
                            if message.startswith(':'):
                                message = message[1:].strip()
                        
                        # Pattern: [source] message
                        source_match = re.search(r'\[(\w+)\]\s*(.*)', message)
                        if source_match:
                            source = source_match.group(1)
                            message = source_match.group(2).strip()
                        
                        logs.append({
                            "timestamp": timestamp,
                            "level": level,
                            "message": message,
                            "source": source
                        })
                
                # If we found logs, break
                if logs:
                    break
            except Exception as e:
                logging.error(f"Error reading log file {log_file}: {str(e)}")
    
    # Try to get logs from Docker metrics if available
    if not logs:
        try:
            from backend.services.system.docker_metrics import DockerMetrics
            system_logs = DockerMetrics.get_container_logs("app", lines)
            for log in system_logs:
                level = "info"
                if "error" in log.get("message", "").lower():
                    level = "error"
                elif "warn" in log.get("message", "").lower():
                    level = "warning"
                
                logs.append({
                    "timestamp": log.get("timestamp", datetime.now().isoformat()),
                    "level": level,
                    "message": log.get("message", "No message"),
                    "source": log.get("source", "app")
                })
        except Exception as e:
            logging.warning(f"Could not get Docker logs: {str(e)}")
    
    # If still no logs, try to get system logs using journalctl if available
    if not logs:
        try:
            # Check if journalctl is available
            journalctl_cmd = ["journalctl", "-n", str(lines), "--no-pager"]
            result = subprocess.run(journalctl_cmd, capture_output=True, text=True, check=False, timeout=2)
            
            if result.returncode == 0 and result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if not line:
                        continue
                    
                    # Parse journalctl output
                    parts = line.split(' ', 3)  # Split into date, time, host, message
                    if len(parts) >= 4:
                        timestamp = f"{parts[0]}T{parts[1]}"
                        source = parts[2]
                        message = parts[3]
                        
                        # Determine log level
                        level = "info"
                        if "error" in message.lower():
                            level = "error"
                        elif "warn" in message.lower():
                            level = "warning"
                        
                        logs.append({
                            "timestamp": timestamp,
                            "level": level,
                            "message": message,
                            "source": source
                        })
        except Exception as e:
            logging.warning(f"Could not get journalctl logs: {str(e)}")
    
    # Capture system errors and warnings from the log gathering process
    system_errors = []
    
    # Try to get logs from Docker metrics if available
    if not logs:
        try:
            from backend.services.system.docker_metrics import DockerMetrics
            system_logs = DockerMetrics.get_container_logs("app", lines)
            for log in system_logs:
                level = "info"
                if "error" in log.get("message", "").lower():
                    level = "error"
                elif "warn" in log.get("message", "").lower():
                    level = "warning"
                
                logs.append({
                    "timestamp": log.get("timestamp", datetime.now().isoformat()),
                    "level": level,
                    "message": log.get("message", "No message"),
                    "source": log.get("source", "app")
                })
        except Exception as e:
            error_msg = f"Failed to get Docker logs: {str(e)}"
            logging.warning(error_msg)
            system_errors.append({
                "timestamp": datetime.now().isoformat(),
                "level": "warning",
                "message": error_msg,
                "source": "logging-system"
            })
    
    # If still no logs, try to get system logs using journalctl if available
    if not logs:
        try:
            # Check if journalctl is available
            journalctl_cmd = ["journalctl", "-n", str(lines), "--no-pager"]
            result = subprocess.run(journalctl_cmd, capture_output=True, text=True, check=False, timeout=2)
            
            if result.returncode == 0 and result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if not line:
                        continue
                    
                    # Parse journalctl output
                    parts = line.split(' ', 3)  # Split into date, time, host, message
                    if len(parts) >= 4:
                        timestamp = f"{parts[0]}T{parts[1]}"
                        source = parts[2]
                        message = parts[3]
                        
                        # Determine log level
                        level = "info"
                        if "error" in message.lower():
                            level = "error"
                        elif "warn" in message.lower():
                            level = "warning"
                        
                        logs.append({
                            "timestamp": timestamp,
                            "level": level,
                            "message": message,
                            "source": source
                        })
        except Exception as e:
            error_msg = f"Failed to get logs from journalctl: {str(e)}"
            logging.warning(error_msg)
            system_errors.append({
                "timestamp": datetime.now().isoformat(),
                "level": "warning",
                "message": error_msg,
                "source": "logging-system"
            })
    
    # If no logs were found, include the system errors and add real system information
    if not logs:
        # Add any system errors we encountered while trying to get logs
        if system_errors:
            logs.extend(system_errors)
            
            # Also add a specific message about no logs being found
            logs.append({
                "timestamp": datetime.now().isoformat(),
                "level": "info",
                "message": "No application logs found. This could be because the application just started or logs are stored in a different location.",
                "source": "logging-system"
            })
        
        # Get system information for additional context
        try:
            from backend.services.system.docker_metrics import DockerMetrics
            system_info = DockerMetrics.get_system_info()
            disk_usage = DockerMetrics.get_disk_usage()
            
            # Generate logs based on real system information
            now = datetime.now()
            
            # CPU usage log
            cpu_usage = system_info.get("cpu", {}).get("usage_percent", 0)
            cpu_level = "info"
            if cpu_usage > 90:
                cpu_level = "error"
            elif cpu_usage > 70:
                cpu_level = "warning"
            
            # Memory usage log
            memory_percent = system_info.get("memory", {}).get("percent", 0)
            memory_level = "info"
            if memory_percent > 90:
                memory_level = "error"
            elif memory_percent > 70:
                memory_level = "warning"
            
            # Disk usage log
            disk_percent = disk_usage.get("disk_stats", {}).get("use_percent", "0%").replace("%", "")
            try:
                disk_percent = float(disk_percent)
            except ValueError:
                disk_percent = 0
            
            disk_level = "info"
            if disk_percent > 90:
                disk_level = "error"
            elif disk_percent > 70:
                disk_level = "warning"
            
            # Generate system logs based on real metrics
            system_events = [
                {"timestamp": (now - timedelta(minutes=5)).isoformat(), "level": cpu_level, "message": f"CPU usage: {cpu_usage}%", "source": "monitoring"},
                {"timestamp": (now - timedelta(minutes=10)).isoformat(), "level": memory_level, "message": f"Memory usage: {memory_percent}%", "source": "monitoring"},
                {"timestamp": (now - timedelta(minutes=15)).isoformat(), "level": disk_level, "message": f"Disk usage: {disk_percent}%", "source": "storage"}
            ]
            logs.extend(system_events)
        except Exception as e:
            error_msg = f"Failed to get system metrics: {str(e)}"
            logging.warning(error_msg)
            logs.append({
                "timestamp": datetime.now().isoformat(),
                "level": "warning",
                "message": error_msg,
                "source": "monitoring"
            })
    
    # Sort by timestamp
    logs.sort(key=lambda x: x["timestamp"], reverse=True)
    
    # Limit to requested number of lines
    return logs[:lines]
