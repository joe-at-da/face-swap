import os
import json
import subprocess
from typing import Dict, List, Any, Optional
import logging
import shutil
from datetime import datetime

logger = logging.getLogger(__name__)

class DockerMetrics:
    """
    Utility class to fetch real metrics from Docker containers and the host system.
    """
    
    @staticmethod
    def get_container_stats() -> List[Dict[str, Any]]:
        """
        Get statistics for all running Docker containers.
        
        Returns:
            List of container statistics
        """
        try:
            # Run docker stats command to get container metrics
            cmd = [
                "docker", "stats", "--no-stream", "--format", 
                "{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}\t{{.PIDs}}"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
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
            
        except subprocess.SubprocessError as e:
            logger.error(f"Failed to get container stats: {str(e)}")
            return []
    
    @staticmethod
    def get_disk_usage() -> Dict[str, Any]:
        """
        Get disk usage statistics for the Docker volumes.
        
        Returns:
            Dictionary with disk usage statistics
        """
        try:
            # Get disk usage for Docker volumes
            volumes_cmd = ["docker", "volume", "ls", "-q"]
            volumes_result = subprocess.run(volumes_cmd, capture_output=True, text=True, check=True)
            volumes = volumes_result.stdout.strip().split('\n')
            
            volume_sizes = {}
            total_size = 0
            
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
                if not mountpoint:
                    continue
                
                # Get size of volume
                du_cmd = ["du", "-sb", mountpoint]
                try:
                    du_result = subprocess.run(du_cmd, capture_output=True, text=True, check=True)
                    size_str = du_result.stdout.strip().split()[0]
                    size = int(size_str)
                    volume_sizes[volume] = size
                    total_size += size
                except (subprocess.SubprocessError, ValueError, IndexError):
                    volume_sizes[volume] = 0
            
            # Get overall disk usage
            df_cmd = ["df", "-h", "/"]
            df_result = subprocess.run(df_cmd, capture_output=True, text=True, check=True)
            df_lines = df_result.stdout.strip().split('\n')
            
            disk_stats = {}
            if len(df_lines) > 1:
                parts = df_lines[1].split()
                if len(parts) >= 5:
                    disk_stats = {
                        "filesystem": parts[0],
                        "size": parts[1],
                        "used": parts[2],
                        "available": parts[3],
                        "use_percent": parts[4],
                        "mount_point": parts[5] if len(parts) > 5 else "/"
                    }
            
            return {
                "volumes": volume_sizes,
                "total_volume_bytes": total_size,
                "disk_stats": disk_stats
            }
            
        except subprocess.SubprocessError as e:
            logger.error(f"Failed to get disk usage: {str(e)}")
            return {
                "volumes": {},
                "total_volume_bytes": 0,
                "disk_stats": {}
            }
    
    @staticmethod
    def get_container_logs(container_name: str, lines: int = 100) -> List[Dict[str, Any]]:
        """
        Get logs from a specific container.
        
        Args:
            container_name: Name of the container
            lines: Number of log lines to retrieve
            
        Returns:
            List of log entries
        """
        try:
            cmd = ["docker", "logs", "--tail", str(lines), container_name]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            log_entries = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                
                # Try to parse timestamp if present
                timestamp = datetime.now().isoformat()
                message = line
                
                # Simple parsing for common log formats
                if line.startswith("["):
                    parts = line.split("]", 1)
                    if len(parts) > 1:
                        timestamp_str = parts[0].strip("[]")
                        try:
                            # Try to parse timestamp
                            timestamp = datetime.fromisoformat(timestamp_str).isoformat()
                            message = parts[1].strip()
                        except ValueError:
                            pass
                
                log_entries.append({
                    "timestamp": timestamp,
                    "message": message,
                    "source": container_name
                })
                
            return log_entries
            
        except subprocess.SubprocessError as e:
            logger.error(f"Failed to get logs for container {container_name}: {str(e)}")
            return []
    
    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """
        Get overall system information.
        
        Returns:
            Dictionary with system information
        """
        info = {}
        
        try:
            # Get Docker info
            docker_info_cmd = ["docker", "info", "--format", "{{json .}}"]
            docker_info_result = subprocess.run(docker_info_cmd, capture_output=True, text=True, check=True)
            docker_info = json.loads(docker_info_result.stdout)
            
            # Extract relevant information
            info["docker"] = {
                "version": docker_info.get("ServerVersion", "Unknown"),
                "containers": docker_info.get("Containers", 0),
                "running": docker_info.get("ContainersRunning", 0),
                "paused": docker_info.get("ContainersPaused", 0),
                "stopped": docker_info.get("ContainersStopped", 0),
                "images": docker_info.get("Images", 0)
            }
            
            # Get CPU info
            cpu_cmd = ["cat", "/proc/cpuinfo"]
            try:
                cpu_result = subprocess.run(cpu_cmd, capture_output=True, text=True, check=True)
                cpu_lines = cpu_result.stdout.strip().split('\n')
                
                cpu_count = 0
                cpu_model = "Unknown"
                
                for line in cpu_lines:
                    if "processor" in line and ":" in line:
                        cpu_count += 1
                    if "model name" in line and ":" in line:
                        cpu_model = line.split(":", 1)[1].strip()
                
                info["cpu"] = {
                    "count": cpu_count,
                    "model": cpu_model
                }
            except subprocess.SubprocessError:
                info["cpu"] = {"count": 0, "model": "Unknown"}
            
            # Get memory info
            mem_cmd = ["cat", "/proc/meminfo"]
            try:
                mem_result = subprocess.run(mem_cmd, capture_output=True, text=True, check=True)
                mem_lines = mem_result.stdout.strip().split('\n')
                
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
                    "used_bytes": mem_total - mem_free
                }
            except (subprocess.SubprocessError, ValueError, IndexError):
                info["memory"] = {"total_bytes": 0, "free_bytes": 0, "used_bytes": 0}
            
            # Get disk space info
            total, used, free = shutil.disk_usage("/")
            info["disk"] = {
                "total_bytes": total,
                "used_bytes": used,
                "free_bytes": free
            }
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get system info: {str(e)}")
            return {
                "docker": {
                    "version": "Unknown",
                    "containers": 0,
                    "running": 0,
                    "paused": 0,
                    "stopped": 0,
                    "images": 0
                },
                "cpu": {"count": 0, "model": "Unknown"},
                "memory": {"total_bytes": 0, "free_bytes": 0, "used_bytes": 0},
                "disk": {"total_bytes": 0, "used_bytes": 0, "free_bytes": 0}
            }
