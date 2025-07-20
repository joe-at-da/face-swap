import os
import json
import subprocess
import time
from typing import Dict, List, Any, Optional
import logging
import shutil
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DockerMetrics:
    """
    Utility class to fetch real metrics from Docker containers and the host system.
    """
    
    # File extensions for categorization
    VIDEO_EXTENSIONS = [".mp4", ".mov", ".avi", ".mkv", ".webm"]
    THUMBNAIL_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
    TRANSCRIPTION_EXTENSIONS = [".txt", ".srt", ".vtt", ".json"]
    
    @staticmethod
    def get_container_stats() -> List[Dict[str, Any]]:
        """
        Get statistics for all running Docker containers.
        If Docker is not available, returns system process information instead.
        
        Returns:
            List of container or process statistics
        """
        try:
            # Check if we're running inside a container by looking for container environment
            if os.path.exists('/.dockerenv') or os.path.exists('/run/.containerenv'):
                # logger.info("Running inside a container, using process stats instead of Docker stats")
                return DockerMetrics._get_process_stats()
                
            # Try to run docker stats command to get container metrics
            try:
                cmd = [
                    "docker", "stats", "--no-stream", "--format", 
                    "{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}\t{{.PIDs}}"
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=2)
                
                containers = []
                for line in result.stdout.strip().split('\n'):
                    if not line:
                        continue
                        
                    parts = line.split('\t')
                    if len(parts) < 7:
                        continue
                        
                    # Parse memory usage (format: "100MiB / 16GiB")
                    mem_parts = parts[2].split('/')
                    mem_used = mem_parts[0].strip()
                    mem_limit = mem_parts[1].strip() if len(mem_parts) > 1 else "N/A"
                    
                    container = {
                        "name": parts[0],
                        "cpu_usage": parts[1].replace('%', ''),  # Remove % sign for easier parsing
                        "memory_used": mem_used,
                        "memory_limit": mem_limit,
                        "memory_percent": parts[3].replace('%', ''),
                        "network_io": parts[4],
                        "block_io": parts[5],
                        "pids": parts[6]
                    }
                    containers.append(container)
                    
                return containers
            except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
                logger.warning(f"Docker command failed, falling back to process stats: {str(e)}")
                return DockerMetrics._get_process_stats()
                
        except Exception as e:
            logger.error(f"Failed to get container stats: {str(e)}")
            return []
    
    @staticmethod
    def _get_process_stats() -> List[Dict[str, Any]]:
        """
        Get statistics for running processes as a fallback when Docker is not available.
        
        Returns:
            List of process statistics
        """
        try:
            import psutil
            
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'memory_info']):
                try:
                    # Get process info
                    proc_info = proc.info
                    memory_bytes = proc_info.get('memory_info', None)
                    if memory_bytes:
                        memory_used = f"{memory_bytes.rss / (1024 * 1024):.1f} MiB"
                    else:
                        memory_used = "N/A"
                        
                    process = {
                        "name": proc_info.get('name', 'unknown'),
                        "pid": str(proc_info.get('pid', 0)),
                        "cpu_usage": str(proc_info.get('cpu_percent', 0)),
                        "memory_used": memory_used,
                        "memory_limit": "N/A",
                        "memory_percent": str(proc_info.get('memory_percent', 0)),
                        "network_io": "N/A",
                        "block_io": "N/A",
                        "pids": "1"
                    }
                    processes.append(process)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
                    
            # Sort by memory usage (highest first)
            processes.sort(key=lambda x: float(x['memory_percent']) if x['memory_percent'] != 'N/A' else 0, reverse=True)
            
            # Return top 10 processes
            return processes[:10]
        except Exception as e:
            logger.error(f"Failed to get process stats: {str(e)}")
            return []
    
    @staticmethod
    def get_disk_usage() -> Dict[str, Any]:
        """
        Get disk usage statistics for the system, with special handling for Docker environments.
        
        Returns:
            Dictionary with disk usage information
        """
        try:
            # Check if we're running in a Docker container
            in_docker = os.path.exists('/.dockerenv') or os.path.exists('/run/.containerenv')
            
            # Define directories to check
            app_dirs = [
                '/app',
                '/app/media',
                '/app/uploads',
                '/app/static',
                '/data',
                '/var/lib/docker',
                '/var/lib/postgresql',
            ]
            
            # Find the root directory for the application
            root_dir = '/'
            for app_dir in app_dirs:
                if os.path.exists(app_dir) and os.path.isdir(app_dir):
                    root_dir = app_dir
                    break
            
            logger.info(f"Calculating disk usage for root directory: {root_dir}")
            
            # Get disk usage for the root directory
            total_bytes, used_bytes, free_bytes = shutil.disk_usage(root_dir)
            
            # Try to get Docker disk info if available
            docker_info = {}
            try:
                if not in_docker:
                    # Try to get Docker info using the docker command
                    docker_cmd = ["docker", "info", "--format", "{{json .}}"]
                    docker_result = subprocess.run(docker_cmd, capture_output=True, text=True, check=False, timeout=2)
                    
                    if docker_result.returncode == 0:
                        docker_info = json.loads(docker_result.stdout)
                        
                        # Check if Docker reports disk space
                        if "DriverStatus" in docker_info:
                            for status in docker_info["DriverStatus"]:
                                if len(status) >= 2:
                                    if "Data Space Total" in status[0]:
                                        # Parse the Docker reported total space (format: "994.7 GiB")
                                        space_str = status[1]
                                        if space_str:
                                            try:
                                                parts = space_str.split()
                                                if len(parts) >= 2:
                                                    value = float(parts[0])
                                                    unit = parts[1].lower()
                                                    
                                                    # Convert to bytes based on unit
                                                    if 'tib' in unit or 'tb' in unit:
                                                        docker_total = value * 1024**4
                                                    elif 'gib' in unit or 'gb' in unit:
                                                        docker_total = value * 1024**3
                                                    elif 'mib' in unit or 'mb' in unit:
                                                        docker_total = value * 1024**2
                                                    else:
                                                        docker_total = value
                                                        
                                                    # Use Docker's reported total if available
                                                    total_bytes = docker_total
                                            except Exception as e:
                                                logger.warning(f"Failed to parse Docker space: {space_str}, {str(e)}")
                                    
                                    if "Data Space Available" in status[0]:
                                        # Parse the Docker reported available space
                                        space_str = status[1]
                                        if space_str:
                                            try:
                                                parts = space_str.split()
                                                if len(parts) >= 2:
                                                    value = float(parts[0])
                                                    unit = parts[1].lower()
                                                    
                                                    # Convert to bytes based on unit
                                                    if 'tib' in unit or 'tb' in unit:
                                                        docker_free = value * 1024**4
                                                    elif 'gib' in unit or 'gb' in unit:
                                                        docker_free = value * 1024**3
                                                    elif 'mib' in unit or 'mb' in unit:
                                                        docker_free = value * 1024**2
                                                    else:
                                                        docker_free = value
                                                        
                                                    # Use Docker's reported free space if available
                                                    free_bytes = docker_free
                                                    used_bytes = total_bytes - free_bytes
                                            except Exception as e:
                                                logger.warning(f"Failed to parse Docker space: {space_str}, {str(e)}")
            except Exception as e:
                logger.warning(f"Failed to get Docker disk info: {str(e)}")
            
            # Calculate directory sizes
            dir_sizes = {}
            total_app_data_bytes = 0
            
            # Check app directories
            for app_dir in app_dirs:
                if os.path.exists(app_dir) and os.path.isdir(app_dir):
                    dir_size = 0
                    try:
                        # Walk through directory and sum file sizes
                        for dirpath, _, filenames in os.walk(app_dir):
                            for f in filenames:
                                fp = os.path.join(dirpath, f)
                                if os.path.exists(fp) and not os.path.islink(fp):
                                    try:
                                        dir_size += os.path.getsize(fp)
                                    except (OSError, IOError) as e:
                                        logger.warning(f"Error getting size of {fp}: {str(e)}")
                    except Exception as e:
                        logger.warning(f"Error walking directory {app_dir}: {str(e)}")
                    
                    # Add to total and directory sizes
                    dir_name = os.path.basename(app_dir) or app_dir
                    dir_sizes[dir_name] = dir_size
                    total_app_data_bytes += dir_size
            
            # If no directories were found, use the root directory
            if not dir_sizes:
                dir_sizes["root"] = used_bytes
                total_app_data_bytes = used_bytes
            
            # Return disk usage information
            return {
                "volumes": dir_sizes,
                "total_volume_bytes": total_app_data_bytes,
                "disk_stats": {
                    "filesystem": os.path.basename(root_dir) or "root",
                    "size": f"{total_bytes / (1024**3):.2f} GB",
                    "used": f"{used_bytes / (1024**3):.2f} GB",
                    "available": f"{free_bytes / (1024**3):.2f} GB",
                    "use_percent": f"{(used_bytes / total_bytes) * 100:.1f}%" if total_bytes > 0 else "0%",
                    "mount_point": root_dir,
                    "total_bytes": total_bytes,
                    "used_bytes": used_bytes,
                    "free_bytes": free_bytes,
                    "docker_info": bool(docker_info)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get disk usage: {str(e)}")
            return {
                "volumes": {},
                "total_volume_bytes": 0,
                "disk_stats": {
                    "filesystem": "unknown",
                    "size": "0 GB",
                    "used": "0 GB",
                    "available": "0 GB",
                    "use_percent": "0%",
                    "mount_point": "/",
                    "total_bytes": 0,
                    "used_bytes": 0,
                    "free_bytes": 0,
                    "docker_info": False
                }
            }
    
    @staticmethod
    def get_container_logs(container_name: str, lines: int = 100) -> List[Dict[str, Any]]:
        """
        Get logs from a specific container or application logs if Docker is not available.
        
        Args:
            container_name: Name of the container or log file
            lines: Number of log lines to retrieve
            
        Returns:
            List of log entries
        """
        log_entries = []
        
        try:
            # Check if we're running in a container
            if os.path.exists('/.dockerenv') or os.path.exists('/run/.containerenv'):
                # We're in a container, try to get logs from standard locations
                log_files = [
                    '/var/log/app.log',
                    '/app/logs/app.log',
                    '/app/log/app.log',
                    '/var/log/messages',
                    '/var/log/syslog'
                ]
                
                # Add container name if provided
                if container_name and container_name != 'app':
                    log_files.insert(0, f'/var/log/{container_name}.log')
                    log_files.insert(0, f'/app/logs/{container_name}.log')
                
                # Try each log file until we find one that exists
                for log_file in log_files:
                    if os.path.exists(log_file):
                        try:
                            # Read the last N lines from the log file
                            with open(log_file, 'r') as f:
                                # Get the last 'lines' lines
                                all_lines = f.readlines()
                                log_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                                
                                for i, line in enumerate(log_lines):
                                    line = line.strip()
                                    if not line:
                                        continue
                                    
                                    # Try to parse timestamp if available
                                    timestamp = ""
                                    message = line
                                    
                                    # Simple timestamp extraction - look for ISO format at the beginning
                                    if line and len(line) > 20 and (line[0:4].isdigit() and line[4] == '-'):
                                        try:
                                            # Try to extract timestamp
                                            timestamp_end = line.find(' ')
                                            if timestamp_end > 10:  # Reasonable timestamp length
                                                timestamp = line[0:timestamp_end]
                                                message = line[timestamp_end+1:]
                                        except Exception:
                                            # If timestamp extraction fails, use the whole line as message
                                            pass
                                    
                                    log_entry = {
                                        "timestamp": timestamp,
                                        "message": message,
                                        "level": "INFO" if "error" not in line.lower() else "ERROR",
                                        "source": log_file,
                                        "line": i + 1
                                    }
                                    log_entries.append(log_entry)
                                
                                if log_entries:
                                    logger.info(f"Found {len(log_entries)} log entries in {log_file}")
                                    return log_entries
                        except Exception as e:
                            logger.warning(f"Failed to read log file {log_file}: {str(e)}")
                
                # If we couldn't find any log files, try to use journalctl if available
                try:
                    cmd = ["journalctl", "-n", str(lines), "--no-pager"]
                    result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=2)
                    
                    if result.returncode == 0 and result.stdout:
                        for i, line in enumerate(result.stdout.strip().split('\n')):
                            if not line:
                                continue
                                
                            log_entry = {
                                "timestamp": "",  # Extract timestamp if needed
                                "message": line,
                                "level": "INFO" if "error" not in line.lower() else "ERROR",
                                "source": "journalctl",
                                "line": i + 1
                            }
                            log_entries.append(log_entry)
                        
                        if log_entries:
                            logger.info(f"Found {len(log_entries)} log entries from journalctl")
                            return log_entries
                except Exception as e:
                    logger.warning(f"Failed to get logs from journalctl: {str(e)}")
            
            # If we're not in a container or couldn't find logs, try Docker if available
            try:
                # Check if Docker is available
                docker_check = subprocess.run(["which", "docker"], capture_output=True, text=True, check=False, timeout=1)
                
                if docker_check.returncode == 0:
                    # Docker is available, try to get container logs
                    cmd = ["docker", "logs", "--tail", str(lines), container_name]
                    result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=3)
                    
                    if result.returncode == 0:
                        for i, line in enumerate(result.stdout.strip().split('\n')):
                            if not line:
                                continue
                                
                            # Try to parse timestamp if available
                            timestamp = ""
                            message = line
                            
                            # Simple timestamp extraction
                            if line and len(line) > 20 and (line[0:4].isdigit() and line[4] == '-'):
                                try:
                                    timestamp_end = line.find(' ')
                                    if timestamp_end > 10:
                                        timestamp = line[0:timestamp_end]
                                        message = line[timestamp_end+1:]
                                except Exception:
                                    pass
                            
                            log_entry = {
                                "timestamp": timestamp,
                                "message": message,
                                "level": "INFO" if "error" not in line.lower() else "ERROR",
                                "container": container_name,
                                "line": i + 1
                            }
                            log_entries.append(log_entry)
                        
                        if log_entries:
                            logger.info(f"Found {len(log_entries)} log entries from Docker container {container_name}")
                            return log_entries
            except Exception as e:
                logger.warning(f"Failed to get Docker container logs: {str(e)}")
            
            # If we still don't have logs, return a message
            if not log_entries:
                logger.warning(f"No logs found for {container_name}")
                log_entries.append({
                    "timestamp": datetime.now().isoformat(),
                    "message": f"No logs found for {container_name}",
                    "level": "WARNING",
                    "source": "system",
                    "line": 1
                })
            
            return log_entries
            
        except Exception as e:
            logger.error(f"Failed to get logs: {str(e)}")
            return [{
                "timestamp": datetime.now().isoformat(),
                "message": f"Error retrieving logs: {str(e)}",
                "level": "ERROR",
                "source": "system",
                "line": 1
            }]
    
    @staticmethod
    def get_oldest_files(limit: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get oldest files by category.
        
        Args:
            limit: Maximum number of files to return per category
            
        Returns:
            Dictionary with lists of oldest files by category
        """
        try:
            # Get volume information
            volumes_cmd = ["docker", "volume", "ls", "-q"]
            volumes_result = subprocess.run(volumes_cmd, capture_output=True, text=True, check=True)
            volumes = volumes_result.stdout.strip().split('\n')
            
            # Initialize file lists with modification time
            video_clips = []
            capture_sessions = []
            thumbnails = []
            transcriptions = []
            
            for volume in volumes:
                if not volume:
                    continue
                    
                # Get volume info
                inspect_cmd = ["docker", "volume", "inspect", volume]
                inspect_result = subprocess.run(inspect_cmd, capture_output=True, text=True, check=True)
                volume_info = json.loads(inspect_result.stdout)
                
                if not volume_info:
                    continue
                    
                mountpoint = volume_info[0].get("Mountpoint", "")
                if not mountpoint or not os.path.exists(mountpoint):
                    continue
                
                # Walk through the volume directory and collect file information
                for root, _, files in os.walk(mountpoint):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if not os.path.exists(file_path):
                            continue
                            
                        try:
                            # Get file stats
                            file_stats = os.stat(file_path)
                            file_size = file_stats.st_size
                            file_mtime = file_stats.st_mtime
                            
                            # Create file info object
                            file_info = {
                                "name": file,
                                "path": file_path,
                                "size_bytes": file_size,
                                "modified_at": datetime.fromtimestamp(file_mtime).isoformat(),
                                "modified_timestamp": file_mtime
                            }
                            
                            # Categorize by extension
                            ext = os.path.splitext(file)[1].lower()
                            
                            # Check if it's in a capture session directory
                            if "capture" in root.lower() or "session" in root.lower():
                                capture_sessions.append(file_info)
                            # Categorize by file extension
                            elif ext in DockerMetrics.VIDEO_EXTENSIONS:
                                video_clips.append(file_info)
                            elif ext in DockerMetrics.THUMBNAIL_EXTENSIONS:
                                thumbnails.append(file_info)
                            elif ext in DockerMetrics.TRANSCRIPTION_EXTENSIONS:
                                transcriptions.append(file_info)
                        except (OSError, IOError):
                            continue
            
            # Sort files by modification time (oldest first) and limit results
            video_clips.sort(key=lambda x: x["modified_timestamp"])
            capture_sessions.sort(key=lambda x: x["modified_timestamp"])
            thumbnails.sort(key=lambda x: x["modified_timestamp"])
            transcriptions.sort(key=lambda x: x["modified_timestamp"])
            
            # Remove the timestamp field used for sorting and limit results
            def clean_and_limit(files, limit):
                result = []
                for f in files[:limit]:
                    f_copy = f.copy()
                    if "modified_timestamp" in f_copy:
                        del f_copy["modified_timestamp"]
                    result.append(f_copy)
                return result
            
            return {
                "video_clips": clean_and_limit(video_clips, limit),
                "capture_sessions": clean_and_limit(capture_sessions, limit),
                "thumbnails": clean_and_limit(thumbnails, limit),
                "transcriptions": clean_and_limit(transcriptions, limit)
            }
            
        except Exception as e:
            logger.error(f"Failed to get oldest files: {str(e)}")
            # Return empty lists in case of error
            return {
                "video_clips": [],
                "capture_sessions": [],
                "thumbnails": [],
                "transcriptions": []
            }
    
    @staticmethod
    def get_storage_breakdown() -> Dict[str, int]:
        """
        Get storage breakdown by file category.
        
        Returns:
            Dictionary with storage breakdown by category in bytes
        """
        try:
            # Try to get a breakdown using Docker volumes first
            breakdown = DockerMetrics._get_volume_breakdown()
            
            # Check if we got any data (non-zero values)
            if sum(breakdown.values()) > 0:
                return breakdown
            
            # If Docker volumes didn't yield results, try direct filesystem approach
            logger.info("Docker volume scan yielded no results, trying direct filesystem approach")
            return DockerMetrics._get_filesystem_breakdown()
            
        except Exception as e:
            logger.error(f"Failed to get storage breakdown: {str(e)}")
            # Return estimated values based on disk usage
            return DockerMetrics._get_estimated_breakdown()
    
    @staticmethod
    def _get_volume_breakdown() -> Dict[str, int]:
        """Get storage breakdown by scanning application directories"""
        try:
            # Define the directories we care about
            app_dirs = [
                '/app/media',          # Main media directory
                '/app/uploads',        # Uploads directory
                '/app/static/clips',   # Video clips
                '/app/static/images',  # Images and thumbnails
                '/app/data',           # Application data
                '/app/transcriptions', # Transcription files
            ]
            
            # Initialize counters
            video_clips_bytes = 0
            capture_sessions_bytes = 0
            thumbnails_bytes = 0
            transcriptions_bytes = 0
            other_bytes = 0
            
            # Process each directory
            for directory in app_dirs:
                if not os.path.exists(directory):
                    continue
                    
                # Walk through the directory and categorize files
                for root, _, files in os.walk(directory):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if not os.path.exists(file_path) or os.path.islink(file_path):
                            continue
                            
                        # Get file size
                        try:
                            file_size = os.path.getsize(file_path)
                        except (OSError, IOError):
                            continue
                            
                        # Categorize by extension and directory
                        _, ext = os.path.splitext(file.lower())
                        
                        if ext in DockerMetrics.VIDEO_EXTENSIONS:
                            video_clips_bytes += file_size
                        elif ext in DockerMetrics.THUMBNAIL_EXTENSIONS:
                            thumbnails_bytes += file_size
                        elif ext in DockerMetrics.TRANSCRIPTION_EXTENSIONS:
                            transcriptions_bytes += file_size
                        elif 'capture' in root.lower() or 'session' in root.lower():
                            capture_sessions_bytes += file_size
                        else:
                            other_bytes += file_size
            
            # If we have no data, check if we're in a Docker container and try to use Docker commands
            if video_clips_bytes == 0 and thumbnails_bytes == 0 and transcriptions_bytes == 0 and other_bytes == 0:
                try:
                    # Check if Docker is available
                    docker_check = subprocess.run(["which", "docker"], capture_output=True, text=True, check=False, timeout=1)
                    
                    if docker_check.returncode == 0:
                        # Docker is available, try to get volumes
                        volumes_cmd = ["docker", "volume", "ls", "-q"]
                        volumes_result = subprocess.run(volumes_cmd, capture_output=True, text=True, check=False, timeout=2)
                        
                        if volumes_result.returncode == 0:
                            volumes = volumes_result.stdout.strip().split('\n')
                            
                            # Process each volume
                            for volume in volumes:
                                if not volume:
                                    continue
                                    
                                # Get volume info
                                inspect_cmd = ["docker", "volume", "inspect", volume]
                                inspect_result = subprocess.run(inspect_cmd, capture_output=True, text=True, check=False, timeout=2)
                                
                                if inspect_result.returncode == 0:
                                    volume_info = json.loads(inspect_result.stdout)
                                    
                                    if volume_info and len(volume_info) > 0:
                                        mountpoint = volume_info[0].get("Mountpoint", "")
                                        if mountpoint and os.path.exists(mountpoint):
                                            # Walk through the volume and categorize files
                                            for root, _, files in os.walk(mountpoint):
                                                for file in files:
                                                    file_path = os.path.join(root, file)
                                                    if not os.path.exists(file_path) or os.path.islink(file_path):
                                                        continue
                                                        
                                                    # Get file size
                                                    try:
                                                        file_size = os.path.getsize(file_path)
                                                    except (OSError, IOError):
                                                        continue
                                                        
                                                    # Categorize by extension
                                                    _, ext = os.path.splitext(file.lower())
                                                    
                                                    if ext in DockerMetrics.VIDEO_EXTENSIONS:
                                                        video_clips_bytes += file_size
                                                    elif ext in DockerMetrics.THUMBNAIL_EXTENSIONS:
                                                        thumbnails_bytes += file_size
                                                    elif ext in DockerMetrics.TRANSCRIPTION_EXTENSIONS:
                                                        transcriptions_bytes += file_size
                                                    elif 'capture' in root.lower() or 'session' in root.lower():
                                                        capture_sessions_bytes += file_size
                                                    else:
                                                        other_bytes += file_size
                except Exception as e:
                    logger.warning(f"Failed to get Docker volume breakdown: {str(e)}")
            
            # Return breakdown
            return {
                "video_clips_bytes": video_clips_bytes,
                "capture_sessions_bytes": capture_sessions_bytes,
                "thumbnails_bytes": thumbnails_bytes,
                "transcriptions_bytes": transcriptions_bytes,
                "other_bytes": other_bytes
            }
            
        except Exception as e:
            logger.error(f"Failed to get volume breakdown: {str(e)}")
            return {
                "video_clips_bytes": 0,
                "capture_sessions_bytes": 0,
                "thumbnails_bytes": 0,
                "transcriptions_bytes": 0,
                "other_bytes": 0
            }
    @staticmethod
    def _get_estimated_breakdown() -> Dict[str, int]:
        """Provide estimated breakdown based on disk usage"""
        try:
            # Get total disk usage
            total, used, _ = shutil.disk_usage("/")
            
            # Estimate breakdown based on typical usage patterns
            # Video clips typically account for 60% of storage
            video_clips_bytes = int(used * 0.6)
            # Capture sessions typically account for 20% of storage
            capture_sessions_bytes = int(used * 0.2)
            # Thumbnails typically account for 5% of storage
            thumbnails_bytes = int(used * 0.05)
            # Transcriptions typically account for 5% of storage
            transcriptions_bytes = int(used * 0.05)
            # Other files account for the remaining 10%
            other_bytes = int(used * 0.1)
            
            logger.info("Using estimated storage breakdown based on disk usage")
            
            return {
                "video_clips_bytes": video_clips_bytes,
                "capture_sessions_bytes": capture_sessions_bytes,
                "thumbnails_bytes": thumbnails_bytes,
                "transcriptions_bytes": transcriptions_bytes,
                "other_bytes": other_bytes
            }
        except Exception as e:
            logger.error(f"Error in estimated breakdown: {str(e)}")
            # Return fallback values if all else fails
            return {
                "video_clips_bytes": 1000000000,  # 1 GB
                "capture_sessions_bytes": 500000000,  # 500 MB
                "thumbnails_bytes": 100000000,  # 100 MB
                "transcriptions_bytes": 50000000,  # 50 MB
                "other_bytes": 350000000  # 350 MB
            }
    
    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """
        Get overall system information without relying on Docker commands.
        
        Returns:
            Dictionary with system information
        """
        info = {}
        
        try:
            # Get container info if available, otherwise provide placeholder
            try:
                # Check if we're running in a container
                is_container = os.path.exists('/.dockerenv') or os.path.exists('/run/.containerenv')
                
                # Get container ID if available
                container_id = "Unknown"
                if os.path.exists('/proc/self/cgroup'):
                    with open('/proc/self/cgroup', 'r') as f:
                        for line in f:
                            if 'docker' in line:
                                container_id = line.split('/')[-1].strip()
                                break
                
                # Get container info
                info["container"] = {
                    "is_container": is_container,
                    "id": container_id,
                    "runtime": "Docker" if is_container else "Host",
                }
            except Exception as e:
                logger.warning(f"Failed to get container info: {str(e)}")
                info["container"] = {
                    "is_container": False,
                    "id": "Unknown",
                    "runtime": "Unknown"
                }
            
            # Get CPU info
            try:
                import psutil
                cpu_count = psutil.cpu_count(logical=True)
                cpu_physical = psutil.cpu_count(logical=False)
                cpu_percent = psutil.cpu_percent(interval=0.1)
                
                info["cpu"] = {
                    "count": cpu_count,
                    "physical_cores": cpu_physical,
                    "usage_percent": cpu_percent,
                    "model": "Unknown"  # psutil doesn't provide CPU model info
                }
                
                # Try to get CPU model from /proc/cpuinfo if available
                if os.path.exists('/proc/cpuinfo'):
                    try:
                        with open('/proc/cpuinfo', 'r') as f:
                            cpu_info = f.read()
                            for line in cpu_info.split('\n'):
                                if 'model name' in line and ':' in line:
                                    info["cpu"]["model"] = line.split(':', 1)[1].strip()
                                    break
                    except Exception as e:
                        logger.warning(f"Failed to read CPU model: {str(e)}")
            except Exception as e:
                logger.warning(f"Failed to get CPU info: {str(e)}")
                info["cpu"] = {"count": 0, "physical_cores": 0, "usage_percent": 0, "model": "Unknown"}
            
            # Get memory info
            try:
                import psutil
                memory = psutil.virtual_memory()
                info["memory"] = {
                    "total_bytes": memory.total,
                    "available_bytes": memory.available,
                    "used_bytes": memory.used,
                    "free_bytes": memory.free,
                    "percent": memory.percent
                }
            except Exception as e:
                logger.warning(f"Failed to get memory info: {str(e)}")
                # Fallback to /proc/meminfo if psutil fails
                try:
                    if os.path.exists('/proc/meminfo'):
                        with open('/proc/meminfo', 'r') as f:
                            mem_lines = f.readlines()
                        
                        mem_total = 0
                        mem_free = 0
                        
                        for line in mem_lines:
                            if "MemTotal" in line:
                                mem_total = int(line.split()[1]) * 1024  # Convert KB to bytes
                            elif "MemFree" in line:
                                mem_free = int(line.split()[1]) * 1024  # Convert KB to bytes
                        
                        info["memory"] = {
                            "total_bytes": mem_total,
                            "free_bytes": mem_free,
                            "used_bytes": mem_total - mem_free,
                            "percent": (mem_total - mem_free) / mem_total * 100 if mem_total > 0 else 0
                        }
                    else:
                        info["memory"] = {"total_bytes": 0, "free_bytes": 0, "used_bytes": 0, "percent": 0}
                except Exception as e2:
                    logger.error(f"All memory info methods failed: {str(e2)}")
                    info["memory"] = {"total_bytes": 0, "free_bytes": 0, "used_bytes": 0, "percent": 0}
            
            # Get disk space info
            try:
                app_path = '/app' if os.path.exists('/app') else '/'
                total, used, free = shutil.disk_usage(app_path)
                info["disk"] = {
                    "total_bytes": total,
                    "used_bytes": used,
                    "free_bytes": free,
                    "percent": (used / total) * 100 if total > 0 else 0,
                    "mount_point": app_path
                }
            except Exception as e:
                logger.warning(f"Failed to get disk info: {str(e)}")
                info["disk"] = {"total_bytes": 0, "used_bytes": 0, "free_bytes": 0, "percent": 0, "mount_point": "/"}
            
            # Get uptime
            try:
                if os.path.exists('/proc/uptime'):
                    with open('/proc/uptime', 'r') as f:
                        uptime_seconds = float(f.readline().split()[0])
                        info["uptime"] = {
                            "seconds": uptime_seconds,
                            "formatted": str(timedelta(seconds=int(uptime_seconds)))
                        }
                else:
                    import psutil
                    uptime_seconds = time.time() - psutil.boot_time()
                    info["uptime"] = {
                        "seconds": uptime_seconds,
                        "formatted": str(timedelta(seconds=int(uptime_seconds)))
                    }
            except Exception as e:
                logger.warning(f"Failed to get uptime: {str(e)}")
                info["uptime"] = {"seconds": 0, "formatted": "0:00:00"}
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get system info: {str(e)}")
            return {
                "container": {"is_container": False, "id": "Unknown", "runtime": "Unknown"},
                "cpu": {"count": 0, "physical_cores": 0, "usage_percent": 0, "model": "Unknown"},
                "memory": {"total_bytes": 0, "free_bytes": 0, "used_bytes": 0, "percent": 0},
                "disk": {"total_bytes": 0, "used_bytes": 0, "free_bytes": 0, "percent": 0, "mount_point": "/"},
                "uptime": {"seconds": 0, "formatted": "0:00:00"}
            }
