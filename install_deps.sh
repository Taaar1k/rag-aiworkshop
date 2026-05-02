#!/bin/bash
# RAG Application Dependencies Installation Script for Arch Linux
# This script creates a proper virtual environment and installs all dependencies

set -e

echo "=== RAG Application Dependency Installer ==="
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

echo "Python version:"
python3 --version
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    echo "Virtual environment created."
else
    echo "Virtual environment already exists."
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip
echo ""

# Install dependencies
echo "Installing dependencies from requirements_mcp.txt..."
pip install -r requirements_mcp.txt
echo ""

# Verify installations
echo "=== Verification ==="
echo "Checking installed packages:"
pip list | grep -E "(llama-cpp|chromadb|sentence-transformers|fastmcp|langchain)"
echo ""

echo "=== Installation Complete ==="
echo ""
echo "Next steps:"
echo "1. Download embedding model (if not already downloaded):"
echo "   python -c \"from huggingface_hub import snapshot_download; snapshot_download(repo_id='nomic-ai/nomic-embed-text-v1.5', local_dir='./models/embeddings', allow_patterns='*.gguf')\""
echo ""
echo "2. Start llama.cpp server for embeddings (port 8090, override via EMBEDDING_PORT env var):"
echo "   ./llama-server --model ./models/embeddings/nomic-embed-text-v1.5.Q4_K_M.gguf --port 8090"
echo ""
echo "3. Start llama.cpp server for LLM (port 8080, override via LLAMA_SERVER_PORT env var):"
echo "   ./llama-server --model ./models/llm/Llama-3-8B-Instruct-Q4_K_M.gguf --port 8080"
echo ""
echo "4. Configure ports via .env file:"
echo "   cp .env.example .env"
echo "   # Edit .env to set LLM_ENDPOINT, EMBEDDING_ENDPOINT, RAG_SERVER_PORT"
echo ""
echo "4. Run the MCP server:"
echo "   python src/mcp_server.py"
echo ""
echo "5. Or run the RAG example:"
echo "   python scripts/rag_example.py"
echo ""