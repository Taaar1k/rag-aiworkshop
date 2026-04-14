#!/usr/bin/env python3
"""
Start script for the Shared RAG Server.
This script initializes and starts the FastAPI server with all dependencies.
"""

import os
import sys
import subprocess
import time
import signal
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_qdrant_running(host: str = "localhost", port: int = 6333) -> bool:
    """Check if Qdrant server is running."""
    try:
        import requests
        response = requests.get(f"http://{host}:{port}/readyz", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def start_qdrant() -> Optional[subprocess.Popen]:
    """Start Qdrant server if not running."""
    qdrant_path = os.getenv("QDRANT_PATH", None)
    
    if qdrant_path and os.path.exists(qdrant_path):
        logger.info(f"Starting Qdrant from {qdrant_path}")
        return subprocess.Popen(
            [qdrant_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
    else:
        logger.info("Qdrant not found at custom path, assuming it's running or will be started separately")
        return None


def check_python_dependencies() -> bool:
    """Check if required Python packages are installed."""
    required_packages = [
        "fastapi",
        "uvicorn",
        "qdrant-client",
        "sentence-transformers",
        "llama-cpp-python"
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing.append(package)
    
    if missing:
        logger.warning(f"Missing packages: {', '.join(missing)}")
        logger.info("Install with: pip install -r requirements_mcp.txt")
        return False
    
    return True


def start_rag_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False) -> subprocess.Popen:
    """Start the RAG server."""
    logger.info(f"Starting RAG server on {host}:{port}")
    
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "src.api.rag_server:app",
        "--host", host,
        "--port", str(port)
    ]
    
    if reload:
        cmd.append("--reload")
    
    return subprocess.Popen(cmd)


def main():
    """Main entry point for starting the RAG server."""
    print("=" * 60)
    print("Shared RAG Server - Starting...")
    print("=" * 60)
    
    # Parse command line arguments
    host = os.getenv("RAG_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("RAG_SERVER_PORT", 8000))
    reload = os.getenv("RAG_SERVER_RELOAD", "false").lower() == "true"
    
    # Check dependencies
    logger.info("Checking dependencies...")
    if not check_python_dependencies():
        logger.error("Dependency check failed. Exiting.")
        sys.exit(1)
    
    # Check/start Qdrant
    logger.info("Checking Qdrant...")
    if not check_qdrant_running():
        logger.warning("Qdrant not running. Starting Qdrant...")
        qdrant_process = start_qdrant()
        time.sleep(5)  # Wait for Qdrant to start
        
        if not check_qdrant_running():
            logger.error("Qdrant failed to start. Exiting.")
            if qdrant_process:
                qdrant_process.terminate()
            sys.exit(1)
    
    # Start RAG server
    logger.info("Starting RAG server...")
    server_process = start_rag_server(host=host, port=port, reload=reload)
    
    # Handle shutdown signals
    def signal_handler(sig, frame):
        logger.info("Shutting down RAG server...")
        server_process.terminate()
        if qdrant_process:
            qdrant_process.terminate()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Wait for server to complete
    try:
        server_process.wait()
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
        server_process.terminate()
        if qdrant_process:
            qdrant_process.terminate()


if __name__ == "__main__":
    main()
