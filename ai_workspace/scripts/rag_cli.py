#!/usr/bin/env python3
"""
RAG CLI - Quick setup and management for RAG system.
Works from any directory if RAG_ROOT env is set.
"""

import argparse
import os
from pathlib import Path
from typing import Optional

import httpx


def get_rag_root() -> Path:
    """Get RAG_ROOT path."""
    # Check env first
    rag_root = os.environ.get("RAG_ROOT")
    if rag_root:
        return Path(rag_root)
    
    # Try to find relative to this script (scripts/ is inside ai_workspace/)
    script_dir = Path(__file__).parent
    rag_path = script_dir.parent
    
    if (rag_path / "src").exists():
        return rag_path
    
    # Default fallback
    return Path("/home/tarik/Sandbox/my-plugin/rag-project/ai_workspace")


GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


def info(msg: str) -> None:
    print(f"{BLUE}[i]{RESET} {msg}")


def ok(msg: str) -> None:
    print(f"{GREEN}[✓]{RESET} {msg}")


def err(msg: str) -> None:
    print(f"{RED}[✗]{RESET} {msg}")


def warn(msg: str) -> None:
    print(f"{YELLOW}[!]{RESET} {msg}")


def check_port(port: int, timeout: float = 2.0) -> bool:
    """Check if port is open."""
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(f"http://localhost:{port}/health")
            return response.status_code == 200
    except Exception:
        return False


def get_models(port: int) -> list:
    """Get models from server."""
    try:
        with httpx.Client(timeout=5) as client:
            response = client.get(f"http://localhost:{port}/v1/models")
            if response.status_code == 200:
                return response.json().get("data", [])
            return []
    except Exception:
        return []


def check_embedding_server() -> bool:
    """Check embedding server on 8090."""
    info("Checking embedding server on port 8090...")
    if check_port(8090):
        models = get_models(8090)
        if models:
            model = models[0]
            ok(f"Running: {model.get('id', 'unknown')}")
            dim = model.get("meta", {}).get("n_embd", "?")
            size = model.get("meta", {}).get("size", 0)
            size_mb = size / 1024 / 1024 if size else 0
            print(f"  {BOLD}Dimension:{RESET} {dim}")
            print(f"  {BOLD}Size:{RESET} {size_mb:.1f} MB")
            return True
    err("Embedding server not running on port 8090")
    return False


def check_llm_server() -> bool:
    """Check LLM server on 8080."""
    info("Checking LLM server on port 8080...")
    if check_port(8080):
        models = get_models(8080)
        if models:
            model = models[0]
            ok(f"Running: {model.get('id', 'unknown')}")
            meta = model.get("meta", {})
            print(f"  {BOLD}Vocabulary:{RESET} {meta.get('n_vocab', '?')}")
            print(f"  {BOLD}Context:{RESET} {meta.get('n_ctx_train', '?')}")
            size = meta.get("size", 0)
            size_gb = size / 1024 / 1024 / 1024 if size else 0
            print(f"  {BOLD}Size:{RESET} {size_gb:.2f} GB")
            return True
    err("LLM server not running on port 8080")
    return False


def check_qdrant() -> bool:
    """Check Qdrant."""
    info("Checking Qdrant on port 6333...")
    try:
        with httpx.Client(timeout=3) as client:
            response = client.get("http://localhost:6333/collections")
            if response.status_code == 200:
                data = response.json()
                collections = data.get("result", {}).get("collections", [])
                ok(f"Running: {len(collections)} collection(s)")
                return True
    except Exception:
        pass
    err("Qdrant not running on port 6333")
    return False


def test_embedding(text: str = "hello world") -> Optional[list]:
    """Test embedding generation."""
    info(f"Testing embedding: '{text}'...")
    try:
        with httpx.Client(timeout=10) as client:
            response = client.post(
                "http://localhost:8090/v1/embeddings",
                json={"input": text, "model": "nomic-embed-text-v1.5"}
            )
            if response.status_code == 200:
                data = response.json()
                embedding = data["data"][0]["embedding"]
                ok(f"Generated: {len(embedding)} dimensions")
                return embedding
            else:
                err(f"Error: {response.status_code}")
    except Exception as e:
        err(f"Failed: {e}")
    return None


def set_embedding_source(source: str) -> None:
    """Set embedding source in .env."""
    env_path = Path(".env")
    env = {}
    
    if env_path.exists():
        content = env_path.read_text()
        for line in content.split("\n"):
            if "=" in line:
                key, val = line.split("=", 1)
                env[key] = val
    
    env["EMBEDDING_SOURCE"] = source
    
    with open(env_path, "w") as f:
        for key, val in sorted(env.items()):
            f.write(f"{key}={val}\n")
    
    ok(f"Set EMBEDDING_SOURCE={source}")
    info("Restart server for changes to take effect")


def show_config() -> None:
    """Show current config."""
    rag_root = get_rag_root()
    info(f"RAG Root: {rag_root}")
    info("Current configuration:")
    
    # Check .env
    env_path = rag_root / ".env"
    if env_path.exists():
        content = env_path.read_text()
        for line in content.split("\n"):
            if "EMBEDDING" in line or "LLM" in line:
                print(f"  {line}")
    
    # Check config files
    config_dir = rag_root / "config"
    if config_dir.exists():
        for config_file in config_dir.glob("*.yaml"):
            name = config_file.name
            if "embed" in name or "model" in name:
                print(f"\n{BOLD}=== {name} ==={RESET}")
                print(config_file.read_text()[:500])


def status() -> None:
    """Show system status."""
    print(f"\n{BOLD}RAG System Status{RESET}")
    print("=" * 40)
    
    check_embedding_server()
    print()
    check_llm_server()
    print()
    check_qdrant()
    print()


def main():
    parser = argparse.ArgumentParser(
        description="RAG CLI - Quick setup and management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
epilog="""
Examples:
  rag status          # Check all servers
  rag test           # Test embedding generation
  rag set local     # Set local API
  rag config        # Show configuration
  rag start         # Show how to start server
  rag stop          # Stop servers
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # status
    subparsers.add_parser("status", help="Check all servers")
    
    # test
    subparsers.add_parser("test", help="Test embedding generation")
    
    # set-embedding
    set_parser = subparsers.add_parser("set-embedding", help="Set embedding source")
    set_parser.add_argument("source", choices=["local", "sentence_transformers"], help="Source")
    
    # config
    subparsers.add_parser("config", help="Show configuration")
    
    # start
    start_parser = subparsers.add_parser("start", help="Start RAG server", add_help=False)
    
    # workspace
    workspace_parser = subparsers.add_parser("workspace", help="Set workspace folder to scan")
    workspace_parser.add_argument("path", nargs="*", help="Folder path")
    
    # stop
    subparsers.add_parser("stop", help="Stop all servers")

    args = parser.parse_args()
    
    # Handle start - start the server
    if args.command == "start":
        rag_root = get_rag_root()
        
        import subprocess
        import os
        
        print(f"\n{BOLD}Starting RAG Server on port 8000...{RESET}\n")
        
        env = os.environ.copy()
        env["PYTHONPATH"] = str(rag_root)
        
        try:
            subprocess.Popen(
                ["python", "-m", "uvicorn", "src.api.rag_server:app", 
                 "--host", "0.0.0.0", "--port", "8000"],
                cwd=str(rag_root),
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            ok(f"RAG server started!")
            print(f"   Check: curl http://localhost:8000/health")
            print(f"   Logs: tail -f /tmp/rag_server.log")
        except Exception as e:
            err(f"Failed to start: {e}")
            print(f"\nManual start:")
            print(f"  cd {rag_root}")
            print(f"  PYTHONPATH={rag_root} uvicorn src.api.rag_server:app --host 0.0.0.0 --port 8000")
        
        return
    
    if args.command == "status" or args.command is None:
        status()
    
    elif args.command == "test":
        test_embedding()
    
    elif args.command == "set-embedding":
        source = "local_api" if args.source == "local" else "sentence_transformers"
        set_embedding_source(source)
    
    elif args.command == "config":
        show_config()
    
    elif args.command == "workspace":
        folder_parts = args.path or []
        folder = " ".join(folder_parts) if folder_parts else None
        
        if folder is None or folder == "show":
            # Show current workspace
            rag_root = get_rag_root()
            config_path = rag_root / "config" / "default.yaml"
            content = config_path.read_text()
            for line in content.split("\n"):
                if 'path:' in line and 'watched' not in line:
                    current = line.split('"')[1] if '"' in line else None
                    if current:
                        ok(f"Current workspace: {current}")
                        return
            err("No workspace configured")
            return
        
        folder_path = Path(folder).resolve()
        
        if not folder_path.exists():
            err(f"Folder not found: {folder}")
            return
        
        if not folder_path.is_dir():
            err(f"Not a directory: {folder}")
            return
        
        rag_root = get_rag_root()
        config_path = rag_root / "config" / "default.yaml"
        
        content = config_path.read_text()
        
        # Find watched_directories and replace the path
        lines = content.split("\n")
        new_lines = []
        in_watched = False
        path_replaced = False
        
        for line in lines:
            if "watched_directories:" in line:
                in_watched = True
                new_lines.append(line)
            elif in_watched and "- path:" in line:
                new_lines.append(f'    - path: "{folder_path}"')
                path_replaced = True
                in_watched = False
            else:
                new_lines.append(line)
        
        if not path_replaced:
            # Insert after watched_directories if not found
            new_lines = []
            for line in lines:
                new_lines.append(line)
                if "watched_directories:" in line:
                    new_lines.append(f'    - path: "{folder_path}"')
                    new_lines.append(f'      recursive: true')
                    path_replaced = True
        
        new_content = "\n".join(new_lines)
        config_path.write_text(new_content)
        ok(f"Set workspace: {folder_path}")
        info("Restart scanner or reindex for changes")
    
    elif args.command == "stop":
        import subprocess
        import signal
        
        # Kill uvicorn processes
        try:
            subprocess.run(["pkill", "-f", "uvicorn"], check=False)
            ok("RAG server stopped")
        except Exception:
            pass


if __name__ == "__main__":
    main()