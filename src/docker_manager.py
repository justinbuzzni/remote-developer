import docker
import subprocess
import logging
from typing import Optional, Dict, Any
import time

logger = logging.getLogger(__name__)

class DockerManager:
    """Manage Docker containers for remote development"""
    
    def __init__(self):
        try:
            self.client = docker.from_env()
        except docker.errors.DockerException as e:
            logger.error(f"Failed to connect to Docker: {e}")
            raise
    
    def create_or_get_container(self, container_name: str) -> Optional[str]:
        """Create or get existing container"""
        try:
            # Check if container exists
            try:
                container = self.client.containers.get(container_name)
                logger.info(f"Container {container_name} already exists")
                
                # Start if not running
                if container.status != 'running':
                    container.start()
                    logger.info(f"Started container {container_name}")
                    time.sleep(2)  # Wait for container to be ready
                    
                return container.id
            except docker.errors.NotFound:
                # Create new container
                logger.info(f"Creating new container: {container_name}")
                
                # Use Ubuntu with development tools
                container = self.client.containers.run(
                    "ubuntu:22.04",
                    name=container_name,
                    detach=True,
                    tty=True,
                    command="/bin/bash",
                    volumes={
                        '/var/run/docker.sock': {'bind': '/var/run/docker.sock', 'mode': 'rw'}
                    },
                    environment={
                        'DEBIAN_FRONTEND': 'noninteractive'
                    }
                )
                
                # Wait for container to be ready
                time.sleep(3)
                
                # Install basic tools
                self.exec_command(container_name, 
                    "apt-get update && apt-get install -y git curl wget sudo build-essential python3 python3-pip nodejs npm")
                
                logger.info(f"Container {container_name} created successfully")
                return container.id
                
        except Exception as e:
            logger.error(f"Error managing container: {e}")
            return None
    
    def exec_command(self, container_name: str, command: str, workdir: str = None) -> Dict[str, Any]:
        """Execute command in container"""
        try:
            container = self.client.containers.get(container_name)
            
            exec_kwargs = {
                'cmd': ['bash', '-c', command],
                'stdout': True,
                'stderr': True,
                'stream': False,
                'demux': True
            }
            
            if workdir:
                exec_kwargs['workdir'] = workdir
                
            result = container.exec_run(**exec_kwargs)
            
            stdout = result.output[0].decode('utf-8') if result.output[0] else ""
            stderr = result.output[1].decode('utf-8') if result.output[1] else ""
            
            return {
                'exit_code': result.exit_code,
                'stdout': stdout,
                'stderr': stderr
            }
            
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            return {
                'exit_code': 1,
                'stdout': '',
                'stderr': str(e)
            }
    
    def copy_to_container(self, container_name: str, src_path: str, dest_path: str):
        """Copy file to container"""
        try:
            container = self.client.containers.get(container_name)
            
            # Use docker cp command
            cmd = f"docker cp {src_path} {container_name}:{dest_path}"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"Failed to copy file: {result.stderr}")
                
        except Exception as e:
            logger.error(f"Error copying file: {e}")
            raise
    
    def stop_container(self, container_name: str):
        """Stop container"""
        try:
            container = self.client.containers.get(container_name)
            container.stop()
            logger.info(f"Stopped container {container_name}")
        except docker.errors.NotFound:
            logger.warning(f"Container {container_name} not found")
        except Exception as e:
            logger.error(f"Error stopping container: {e}")