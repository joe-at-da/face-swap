from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import psutil
import platform
import os
import json
import subprocess
import logging
import re
from datetime import datetime, timedelta

from backend.api import deps
from backend.db.models.user import User, UserRole

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
        # Get host system info
        system_info = {
            "os": {
                "name": platform.system(),
                "version": platform.version(),
                "platform": platform.platform(),
                "architecture": platform.machine(),
                "python_version": platform.python_version()
            },
            "cpu": {
                "count": psutil.cpu_count(logical=True),
                "physical_count": psutil.cpu_count(logical=False),
                "usage_percent": psutil.cpu_percent(interval=0.1),
                "per_cpu_percent": psutil.cpu_percent(interval=0.1, percpu=True)
            },
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "used": psutil.virtual_memory().used,
                "percent": psutil.virtual_memory().percent,
                "swap_total": psutil.swap_memory().total,
                "swap_used": psutil.swap_memory().used,
                "swap_percent": psutil.swap_memory().percent
            },
            "disk": {
                "total": psutil.disk_usage('/').total,
                "used": psutil.disk_usage('/').used,
                "free": psutil.disk_usage('/').free,
                "percent": psutil.disk_usage('/').percent,
                "partitions": [
                    {
                        "device": p.device,
                        "mountpoint": p.mountpoint,
                        "fstype": p.fstype,
                        "opts": p.opts
                    } for p in psutil.disk_partitions(all=False)
                ]
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
        
        # Get process information
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_percent', 'cpu_percent', 'create_time']):
            try:
                # Only include processes related to our application
                if any(x in proc.name().lower() for x in ['python', 'uvicorn', 'gunicorn', 'node', 'npm']):
                    proc_info = proc.info
                    proc_info['create_time'] = datetime.fromtimestamp(proc_info['create_time']).isoformat() if proc_info.get('create_time') else None
                    processes.append(proc_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # Return comprehensive system info
        return {
            "host": system_info,
            "processes": processes[:10],  # Limit to top 10 processes
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        # Log the error
        logging.error(f"Error getting system info: {str(e)}")
        
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

@router.get("/processes", response_model=Dict[str, Any])
async def get_processes(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Get process statistics.
    Only accessible to admin users.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    try:
        # Get process information
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_percent', 'cpu_percent', 'create_time', 'cmdline', 'status']):
            try:
                proc_info = proc.info
                proc_info['create_time'] = datetime.fromtimestamp(proc_info['create_time']).isoformat() if proc_info.get('create_time') else None
                
                # Add additional process details
                try:
                    proc_info['memory_info'] = {
                        'rss': proc.memory_info().rss,
                        'vms': proc.memory_info().vms,
                        'rss_mb': proc.memory_info().rss / (1024 * 1024),
                        'vms_mb': proc.memory_info().vms / (1024 * 1024)
                    }
                    proc_info['num_threads'] = proc.num_threads()
                    proc_info['nice'] = proc.nice()
                    proc_info['io_counters'] = {
                        'read_count': proc.io_counters().read_count if hasattr(proc.io_counters(), 'read_count') else 0,
                        'write_count': proc.io_counters().write_count if hasattr(proc.io_counters(), 'write_count') else 0,
                        'read_bytes': proc.io_counters().read_bytes if hasattr(proc.io_counters(), 'read_bytes') else 0,
                        'write_bytes': proc.io_counters().write_bytes if hasattr(proc.io_counters(), 'write_bytes') else 0
                    }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                
                processes.append(proc_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # Sort processes by memory usage (descending)
        processes.sort(key=lambda x: x.get('memory_percent', 0), reverse=True)
        
        return {
            "processes": processes[:20],  # Limit to top 20 processes
            "count": len(processes),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        # Log the error
        logging.error(f"Error getting process stats: {str(e)}")
        
        # Return error message
        return {
            "error": str(e),
            "processes": [],
            "count": 0,
            "timestamp": datetime.now().isoformat()
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
        # Get system disk usage
        root_usage = psutil.disk_usage('/')
        
        # Format disk usage data
        disk_stats = {
            "total": f"{root_usage.total / (1024**3):.2f} GB",
            "used": f"{root_usage.used / (1024**3):.2f} GB",
            "free": f"{root_usage.free / (1024**3):.2f} GB",
            "use_percent": f"{root_usage.percent}%",
            "total_bytes": root_usage.total,
            "used_bytes": root_usage.used,
            "free_bytes": root_usage.free
        }
        
        # Get all disk partitions
        partitions = []
        for partition in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                partitions.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total": f"{usage.total / (1024**3):.2f} GB",
                    "used": f"{usage.used / (1024**3):.2f} GB",
                    "free": f"{usage.free / (1024**3):.2f} GB",
                    "use_percent": f"{usage.percent}%",
                    "total_bytes": usage.total,
                    "used_bytes": usage.used,
                    "free_bytes": usage.free
                })
            except (PermissionError, OSError):
                # Skip partitions we can't access
                pass
        
        # Get IO statistics
        io_stats = psutil.disk_io_counters(perdisk=True)
        io_summary = {}
        for disk, stats in io_stats.items():
            io_summary[disk] = {
                "read_count": stats.read_count,
                "write_count": stats.write_count,
                "read_bytes": stats.read_bytes,
                "write_bytes": stats.write_bytes,
                "read_time": stats.read_time,
                "write_time": stats.write_time,
                "read_mb": f"{stats.read_bytes / (1024**2):.2f} MB",
                "write_mb": f"{stats.write_bytes / (1024**2):.2f} MB"
            }
        
        # Check for application-specific directories
        app_directories = [
            "/app",
            "/app/data",
            "/app/uploads",
            "/app/media",
            "./uploads",
            "./media",
            "./data"
        ]
        
        directory_stats = {}
        for directory in app_directories:
            try:
                if os.path.exists(directory) and os.path.isdir(directory):
                    # Get directory size
                    total_size = 0
                    for dirpath, dirnames, filenames in os.walk(directory):
                        for f in filenames:
                            fp = os.path.join(dirpath, f)
                            if os.path.exists(fp):
                                total_size += os.path.getsize(fp)
                    
                    directory_stats[directory] = {
                        "size": f"{total_size / (1024**2):.2f} MB",
                        "size_bytes": total_size,
                        "files": len([f for dirpath, dirnames, filenames in os.walk(directory) for f in filenames])
                    }
            except (PermissionError, OSError) as e:
                directory_stats[directory] = {"error": str(e)}
        
        return {
            "disk_stats": disk_stats,
            "partitions": partitions,
            "io_stats": io_summary,
            "app_directories": directory_stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        # Log the error
        logging.error(f"Error getting disk usage: {str(e)}")
        
        # Return basic info in case of error
        return {
            "error": str(e),
            "disk_stats": {
                "total": "0 GB",
                "used": "0 GB",
                "free": "0 GB",
                "use_percent": "0%"
            },
            "timestamp": datetime.now().isoformat()
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
    
    # Create a list to track any errors we encounter while trying to get logs
    system_errors = []
    
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
    
    # Try to get logs from process monitoring
    if not logs:
        try:
            # Use psutil to get process information
            import psutil
            app_processes = []
            
            # Look for processes that might be related to our application
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
                try:
                    # Check if this process is related to our application
                    cmdline = proc.info.get('cmdline', [])
                    name = proc.info.get('name', '')
                    
                    # Look for Python processes running our app
                    if cmdline and any(x for x in cmdline if 'python' in x.lower() and ('app' in x.lower() or 'backend' in x.lower() or 'api' in x.lower())):
                        app_processes.append(proc)
                    # Also look for uvicorn/gunicorn processes
                    elif name and ('uvicorn' in name.lower() or 'gunicorn' in name.lower()):
                        app_processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            # If we found application processes, generate logs from them
            if app_processes:
                now = datetime.now()
                for i, proc in enumerate(app_processes):
                    try:
                        # Get process info
                        pid = proc.info.get('pid', 0)
                        name = proc.info.get('name', 'unknown')
                        create_time = datetime.fromtimestamp(proc.info.get('create_time', now.timestamp()))
                        uptime = now - create_time
                        
                        # Add process info as logs
                        logs.append({
                            "timestamp": now.isoformat(),
                            "level": "info",
                            "message": f"Process {name} (PID: {pid}) running for {uptime.total_seconds():.1f} seconds",
                            "source": "process-monitor"
                        })
                        
                        # Try to get memory usage
                        try:
                            mem_info = proc.memory_info()
                            logs.append({
                                "timestamp": (now - timedelta(seconds=1)).isoformat(),
                                "level": "info",
                                "message": f"Memory usage: {mem_info.rss / (1024 * 1024):.1f} MB",
                                "source": f"process-{pid}"
                            })
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                        
                        # Try to get CPU usage
                        try:
                            cpu_percent = proc.cpu_percent(interval=0.1)
                            logs.append({
                                "timestamp": (now - timedelta(seconds=2)).isoformat(),
                                "level": "info",
                                "message": f"CPU usage: {cpu_percent:.1f}%",
                                "source": f"process-{pid}"
                            })
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    except Exception as proc_err:
                        system_errors.append({
                            "timestamp": now.isoformat(),
                            "level": "warning",
                            "message": f"Error getting process info: {str(proc_err)}",
                            "source": "process-monitor"
                        })
        except Exception as e:
            error_msg = f"Failed to get process information: {str(e)}"
            logging.warning(error_msg)
            system_errors.append({
                "timestamp": datetime.now().isoformat(),
                "level": "warning",
                "message": error_msg,
                "source": "system-monitor"
            })
    
    # Create a custom handler to capture log messages
    class LogCaptureHandler(logging.Handler):
        def __init__(self):
            super().__init__()
            self.logs = []
            
        def emit(self, record):
            try:
                self.logs.append({
                    "timestamp": datetime.now().isoformat(),
                    "level": record.levelname.lower(),
                    "message": record.getMessage(),
                    "source": record.name if hasattr(record, 'name') else "application"
                })
            except Exception:
                pass
    
    # Set up log capture for this request
    log_capture = LogCaptureHandler()
    log_capture.setLevel(logging.WARNING)  # Capture warnings and errors
    logging.getLogger().addHandler(log_capture)
    
    # Log a test message to ensure our capture works
    logging.warning("Checking log capture system")
    
    # Add any captured logs to our system_errors
    if log_capture.logs:
        system_errors.extend(log_capture.logs)
    
    # Remove the handler after we're done
    logging.getLogger().removeHandler(log_capture)
    
    # Also check for common error messages in log files
    try:
        # Check the application log file if it exists
        log_files = [
            "/app/logs/app.log",
            "/var/log/app.log",
            "/tmp/app.log",
            "./logs/app.log",
            "./backend/logs/app.log"
        ]
        
        for log_file in log_files:
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    # Read the last 50 lines
                    file_lines = f.readlines()
                    last_lines = file_lines[-50:] if len(file_lines) > 50 else file_lines
                    for line in last_lines:
                        if "Failed to get logs" in line or "No logs found" in line or "Error:" in line or "error" in line.lower():
                            # Try to extract timestamp from the line
                            timestamp = datetime.now().isoformat()
                            timestamp_match = re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', line)
                            if timestamp_match:
                                timestamp_str = timestamp_match.group(0)
                                try:
                                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S").isoformat()
                                except ValueError:
                                    pass
                            
                            system_errors.append({
                                "timestamp": timestamp,
                                "level": "warning",
                                "message": line.strip(),
                                "source": "app-logs"
                            })
                    break  # Stop after finding the first valid log file
    except Exception as e:
        logging.warning(f"Failed to check log files: {str(e)}")
    
    # Always include any system errors we encountered
    if system_errors:
        logs.extend(system_errors)
    
    # If no logs were found, add system information
    if not logs:
        # Add a specific message about no logs being found
        logs.append({
            "timestamp": datetime.now().isoformat(),
            "level": "info",
            "message": "No application logs found. Using system metrics instead.",
            "source": "logging-system"
        })
        
        # Add system metrics as logs
        try:
            # Get CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            logs.append({
                "timestamp": datetime.now().isoformat(),
                "level": "info",
                "message": f"CPU usage: {cpu_percent}%",
                "source": "system-metrics"
            })
            
            # Get memory usage
            memory = psutil.virtual_memory()
            logs.append({
                "timestamp": (datetime.now() - timedelta(seconds=1)).isoformat(),
                "level": "info",
                "message": f"Memory usage: {memory.percent}% (Used: {memory.used / (1024*1024*1024):.2f} GB, Total: {memory.total / (1024*1024*1024):.2f} GB)",
                "source": "system-metrics"
            })
            
            # Get disk usage
            disk = psutil.disk_usage('/')
            logs.append({
                "timestamp": (datetime.now() - timedelta(seconds=2)).isoformat(),
                "level": "info",
                "message": f"Disk usage: {disk.percent}% (Used: {disk.used / (1024*1024*1024):.2f} GB, Total: {disk.total / (1024*1024*1024):.2f} GB)",
                "source": "system-metrics"
            })
            
            # Get network info
            net_io = psutil.net_io_counters()
            logs.append({
                "timestamp": (datetime.now() - timedelta(seconds=3)).isoformat(),
                "level": "info",
                "message": f"Network: Sent: {net_io.bytes_sent / (1024*1024):.2f} MB, Received: {net_io.bytes_recv / (1024*1024):.2f} MB",
                "source": "system-metrics"
            })
            
            # Get boot time
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            logs.append({
                "timestamp": (datetime.now() - timedelta(seconds=4)).isoformat(),
                "level": "info",
                "message": f"System uptime: {uptime.days} days, {uptime.seconds // 3600} hours, {(uptime.seconds % 3600) // 60} minutes",
                "source": "system-metrics"
            })
        except Exception as e:
            logs.append({
                "timestamp": datetime.now().isoformat(),
                "level": "warning",
                "message": f"Failed to get system metrics: {str(e)}",
                "source": "system-metrics"
            })
        
        # We've already added system metrics above, so no need for additional context
    
    # Sort by timestamp
    logs.sort(key=lambda x: x["timestamp"], reverse=True)
    
    # Limit to requested number of lines
    return logs[:lines]
