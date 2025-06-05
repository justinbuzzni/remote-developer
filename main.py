#!/usr/bin/env python3
"""
Remote Developer - Main entry point
Automates development tasks using Claude Code in devpod environments
"""

import click
import sys
from loguru import logger
from src.remote_developer import RemoteDeveloper
from src.config import Config

# Configure logger
logger.remove()
logger.add(sys.stdout, format="{time} {level} {message}", level="INFO")


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Remote Developer CLI - Automate development with Claude Code"""
    pass


@cli.command()
@click.option("--devpod", "-d", required=True, help="Name of the devpod")
@click.option("--config", "-c", default="config.yaml", help="Configuration file path")
def setup(devpod, config):
    """Setup Claude Code in a devpod"""
    logger.info(f"Setting up Claude Code in devpod: {devpod}")
    
    try:
        conf = Config(config)
        rd = RemoteDeveloper(devpod, conf)
        rd.setup_claude_code()
        logger.success("Claude Code setup completed successfully!")
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        sys.exit(1)

@cli.command()
@click.option("--devpod", "-d", required=True, help="Name of the devpod")
@click.option("--task", "-t", required=True, help="Development task description")
@click.option("--config", "-c", default="config.yaml", help="Configuration file path")
@click.option("--commit", is_flag=True, help="Auto-commit changes")
@click.option("--deploy", is_flag=True, help="Auto-deploy after completion")
def execute(devpod, task, config, commit, deploy):
    """Execute a development task using Claude Code"""
    logger.info(f"Executing task in devpod {devpod}: {task}")
    
    try:
        conf = Config(config)
        rd = RemoteDeveloper(devpod, conf)
        
        # Execute the task
        result = rd.execute_task(task)
        logger.info(f"Task result: {result}")
        
        # Commit if requested
        if commit:
            logger.info("Committing changes...")
            rd.commit_changes(f"Claude Code: {task}")
        
        # Deploy if requested
        if deploy:
            logger.info("Deploying changes...")
            rd.deploy()
            
        logger.success("Task execution completed successfully!")
    except Exception as e:
        logger.error(f"Task execution failed: {e}")
        sys.exit(1)


@cli.command()
@click.option("--devpod", "-d", required=True, help="Name of the devpod")
def status(devpod):
    """Check Claude Code status in devpod"""
    logger.info(f"Checking Claude Code status in devpod: {devpod}")
    
    try:
        rd = RemoteDeveloper(devpod)
        status_info = rd.get_status()
        
        logger.info("Claude Code Status:")
        for key, value in status_info.items():
            logger.info(f"  {key}: {value}")
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()