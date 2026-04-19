#!/usr/bin/env python3
"""
MCP Client Example - How to connect to the RAG MCP server from CLI
Simple HTTP-based client for testing MCP server tools
"""

import requests
import json
import time
import sys
from pathlib import Path


def test_mcp_server():
    """Test MCP server tools via HTTP"""
    
    # MCP server runs on port 3000 by default for HTTP transport
    BASE_URL = "http://localhost:3000"
    
    print("Testing MCP RAG Server")
    print("=" * 50)
    
    # Test 1: Health check
    print("\n1. Testing health_check...")
    try:
        response = requests.post(
            f"{BASE_URL}/mcp/health_check",
            json={},
            timeout=5
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Health check failed (server may not be running): {e}")
        print("\nTo start the server, run:")
        print("  cd <repo-root>/ai_workspace")
        print("  source ../venv/bin/activate")
        print("  python src/mcp_server.py")
        return
    
    # Test 2: Add a document
    print("\n2. Testing add_document...")
    test_doc = Path(__file__).parent.parent / "SETUP_GUIDE.md"
    if test_doc.exists():
        try:
            response = requests.post(
                f"{BASE_URL}/mcp/add_document",
                json={"file_path": str(test_doc)},
                timeout=5
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Test document not found")
    
    # Test 3: List documents
    print("\n3. Testing list_documents...")
    try:
        response = requests.post(
            f"{BASE_URL}/mcp/list_documents",
            json={},
            timeout=5
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 4: Search
    print("\n4. Testing search...")
    try:
        response = requests.post(
            f"{BASE_URL}/mcp/search",
            json={"query": "RAG system", "top_k": 2},
            timeout=5
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 5: Ask with context
    print("\n5. Testing ask with context...")
    try:
        response = requests.post(
            f"{BASE_URL}/mcp/ask",
            json={
                "question": "What is RAG?",
                "context": "RAG is a retrieval-augmented generation system."
            },
            timeout=5
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "=" * 50)
    print("MCP Client Test Complete")


if __name__ == "__main__":
    test_mcp_server()
