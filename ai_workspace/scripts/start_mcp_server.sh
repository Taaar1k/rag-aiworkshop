#!/bin/bash
# MCP Server Startup Script

echo "Starting MCP RAG Server..."
echo "============================"

# Activate virtual environment
source ../venv/bin/activate

# Start the server
python src/mcp_server.py
