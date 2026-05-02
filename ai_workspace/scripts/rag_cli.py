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

    raise RuntimeError(
        "Cannot locate RAG root. Set RAG_ROOT env var or run from ai_workspace/."
    )


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


def set_workspace(folder_parts: Optional[list[str]] = None) -> None:
    """Show or set the watched workspace folder for directory scanning."""
    folder = " ".join(folder_parts) if folder_parts else None
    rag_root = get_rag_root()
    config_path = rag_root / "config" / "default.yaml"

    if folder is None or folder == "show":
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
                new_lines.append('      recursive: true')
                path_replaced = True

    new_content = "\n".join(new_lines)
    config_path.write_text(new_content)
    ok(f"Set workspace: {folder_path}")
    info("Restart scanner or reindex for changes")


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


DOCTOR_CHECKS_PASS: int = 0
DOCTOR_CHECKS_FAIL: int = 0
DOCTOR_CHECKS_WARN: int = 0

def _check(ok_msg: str, fail_msg: str, condition: bool) -> bool:
    """Track pass/fail for doctor command and print result."""
    global DOCTOR_CHECKS_PASS, DOCTOR_CHECKS_FAIL, DOCTOR_CHECKS_WARN
    if condition:
        DOCTOR_CHECKS_PASS += 1
        return True
    DOCTOR_CHECKS_FAIL += 1
    return False


def doctor() -> None:
    """Run smoke-test to verify the RAG system is healthy."""
    global DOCTOR_CHECKS_PASS, DOCTOR_CHECKS_FAIL, DOCTOR_CHECKS_WARN
    DOCTOR_CHECKS_PASS = DOCTOR_CHECKS_FAIL = DOCTOR_CHECKS_WARN = 0

    print(f"\n{BOLD}CORE RAG Doctor — Smoke Test{RESET}")
    print("=" * 50 + "\n")

    rag_root = get_rag_root()

    # ── 1. Workspace ──
    print(f"{BOLD}[1/8] Workspace{RESET}")
    info(f"RAG root: {rag_root}")
    if _check("RAG root exists", "RAG root MISSING", rag_root.exists()):
        default_yaml = rag_root / "config" / "default.yaml"
        if default_yaml.exists():
            import yaml
            cfg = yaml.safe_load(default_yaml.read_text())
            watched = cfg.get("directory_scanning", {}).get("watched_directories", [])
            if watched:
                for entry in watched:
                    p = Path(entry["path"])
                    ok(f"Watched dir: {p}  {'✓ exists' if p.exists() else '✗ MISSING'}")
                    if not p.exists():
                        err(f"Watched directory not found: {p}")
                        DOCTOR_CHECKS_FAIL += 1
                    else:
                        files = list(p.rglob("*"))
                        print(f"    Files inside: {len(files)}")
            else:
                warn("No watched directories configured")
                DOCTOR_CHECKS_WARN += 1
        else:
            warn("config/default.yaml not found")
            DOCTOR_CHECKS_WARN += 1
    print()

    # ── 2. Scanner state ──
    print(f"{BOLD}[2/8] Scanner index state{RESET}")
    state_file = rag_root / "memory" / "index_state.json"
    if not state_file.exists():
        state_file = rag_root.parent / "ai_workspace" / "memory" / "index_state.json"
    if state_file.exists():
        import json
        state = json.loads(state_file.read_text())
        files = sorted(state.get("files", {}).keys())
        last_scan = state.get("last_scan", "unknown")
        schema = state.get("schema_version", "unknown")
        ok(f"State file: {state_file}")
        print(f"    Tracked files: {len(files)}")
        print(f"    Last scan:     {last_scan}")
        print(f"    Schema:        {schema}")
        if files:
            for f in files[:5]:
                print(f"      • {f}")
            if len(files) > 5:
                print(f"      … and {len(files)-5} more")
    else:
        warn("Scanner state file not found")
        warn("Start the RAG API/scanner first")
        DOCTOR_CHECKS_WARN += 1
    print()

    # ── 3. RAG API health ──
    print(f"{BOLD}[3/8] RAG API /health{RESET}")
    try:
        with httpx.Client(timeout=5) as client:
            r = client.get("http://localhost:8000/health")
            if r.status_code == 200:
                data = r.json()
                status = data.get("status", "unknown")
                components = data.get("components", {})
                if _check(f"HTTP 200 | status={status}", "Unhealthy", status in {"healthy", "degraded"}):
                    for name, comp in components.items():
                        cs = comp.get("status", "?")
                        icon = "✓" if cs == "healthy" else ("!" if cs == "degraded" else "✗")
                        print(f"    [{icon}] {name}: {cs}  {comp.get('message', '')[:80]}")
            else:
                _check("", f"HTTP {r.status_code}", False)
                err(f"Health endpoint returned {r.status_code}")
    except Exception as e:
        _check("", f"Cannot reach RAG API: {e}", False)
        err(f"Cannot reach RAG API on localhost:8000")
        err("  Start server: rag start")
    print()

    # ── 4. Scanner running ──
    print(f"{BOLD}[4/8] Scanner{RESET}")
    try:
        with httpx.Client(timeout=5) as client:
            r = client.get("http://localhost:8000/scanner/status")
            if r.status_code == 200:
                data = r.json()
                running = data.get("scanner_running", False)
                enabled = data.get("scanner_enabled", False)
                dirs = data.get("watched_directories", 0)
                if _check(f"Scanner {'RUNNING' if running else 'IDLE'}", "Scanner NOT running", running):
                    print(f"    Enabled: {enabled}")
                    print(f"    Watched dirs: {dirs}")
            else:
                warn("Scanner status endpoint unreachable")
                DOCTOR_CHECKS_WARN += 1
    except Exception as e:
        _check("", f"Scanner status failed: {e}", False)
        err(f"Cannot reach scanner status endpoint")
    print()

    # ── 5. RAG query ──
    print(f"{BOLD}[5/8] RAG query{RESET}")
    try:
        with httpx.Client(timeout=15) as client:
            r = client.post(
                "http://localhost:8000/rag/query",
                json={"query": "ping health check", "top_k": 2},
            )
            if r.status_code == 200:
                data = r.json()
                sources = data.get("sources", [])
                answer = data.get("answer", "")
                if _check(f"Query OK: {len(sources)} sources, {len(answer)} chars answer", "No sources returned", len(sources) > 0):
                    for s in sources[:3]:
                        print(f"    • {s.get('filename', '?')}  (score: {s.get('score', 'n/a')})")
            else:
                _check("", f"Query HTTP {r.status_code}", False)
    except Exception as e:
        _check("", f"Query failed: {e}", False)
        err(f"Query to RAG API failed")
    print()

    # ── 6. Env vars ──
    print(f"{BOLD}[6/8] Environment variables{RESET}")
    gh_token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN", "")
    brave_key = os.environ.get("BRAVE_API_KEY", "")
    groq_key = os.environ.get("GROQ_API_KEY", "")
    if gh_token:
        ok(f"GITHUB_PERSONAL_ACCESS_TOKEN: set ({len(gh_token)} chars)")
        DOCTOR_CHECKS_PASS += 1
    else:
        warn("GITHUB_PERSONAL_ACCESS_TOKEN NOT set (needed for GitHub MCP)")
        DOCTOR_CHECKS_WARN += 1
    if brave_key:
        ok(f"BRAVE_API_KEY: set ({len(brave_key)} chars)")
        DOCTOR_CHECKS_PASS += 1
    else:
        warn("BRAVE_API_KEY NOT set (needed for Brave Search MCP)")
        DOCTOR_CHECKS_WARN += 1
    if groq_key:
        ok(f"GROQ_API_KEY: set ({len(groq_key)} chars)")
        DOCTOR_CHECKS_PASS += 1
    else:
        warn("GROQ_API_KEY NOT set (needed for Telegram voice transcription)")
        DOCTOR_CHECKS_WARN += 1
    print()

    # ── 7. MCP config integrity ──
    print(f"{BOLD}[7/8] Pi MCP config integrity{RESET}")
    mcp_path = Path.home() / ".pi" / "agent" / "mcp.json"
    if mcp_path.exists():
        import json
        mcp_data = json.loads(mcp_path.read_text())
        servers = mcp_data.get("mcpServers", {})
        ok(f"MCP config: {len(servers)} servers")
        for name in sorted(servers):
            cfg = servers[name]
            env = cfg.get("env", {})
            has_token_ref = any(
                "${GITHUB" in v or "${BRAVE" in v or "${GROQ" in v
                for v in env.values()
            )
            has_hardcoded = any(
                v.startswith(("gho_", "BSA", "sk-"))
                for v in env.values()
            )
            extra = ""
            if has_hardcoded:
                extra = " ⚠️ HARDCODED TOKEN"
                DOCTOR_CHECKS_WARN += 1
            elif has_token_ref:
                extra = " (env var refs)"
            print(f"    • {name}{extra}")
    else:
        warn("Pi MCP config not found")
        DOCTOR_CHECKS_WARN += 1
    print()

    # ── 8. Summary ──
    print(f"{BOLD}[8/8] Summary{RESET}")
    total = DOCTOR_CHECKS_PASS + DOCTOR_CHECKS_FAIL + DOCTOR_CHECKS_WARN
    print(f"    Pass: {DOCTOR_CHECKS_PASS}  Fail: {DOCTOR_CHECKS_FAIL}  Warn: {DOCTOR_CHECKS_WARN}")
    if DOCTOR_CHECKS_FAIL == 0 and DOCTOR_CHECKS_WARN == 0:
        print(f"\n{GREEN}{BOLD}✨ System: PERFECT{RESET}")
    elif DOCTOR_CHECKS_FAIL == 0:
        print(f"\n{YELLOW}{BOLD}✅ System: HEALTHY ({DOCTOR_CHECKS_WARN} warning(s)){RESET}")
    elif DOCTOR_CHECKS_FAIL <= 2:
        print(f"\n{RED}{BOLD}⚠️  System: DEGRADED ({DOCTOR_CHECKS_FAIL} fail(s), {DOCTOR_CHECKS_WARN} warning(s)){RESET}")
    else:
        print(f"\n{RED}{BOLD}❌ System: BROKEN ({DOCTOR_CHECKS_FAIL} fail(s), {DOCTOR_CHECKS_WARN} warning(s)){RESET}")


def main():
    parser = argparse.ArgumentParser(
        description="RAG CLI - Quick setup and management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
epilog="""
Commands:
  rag -h                 # Show this command list
  rag status             # Check all servers
  rag test               # Test embedding generation
  rag config             # Show configuration
  rag start              # Start server
  rag stop               # Stop servers
  rag doctor             # Smoke-test: workspace, scanner, API, env vars
  rag dashboard          # Generate sprint progress HTML dashboard
  rag watch              # Start CORE watcher (auto-index + dashboard)
  rag -w                 # Show current workspace folder
  rag -w /path/to/dir    # Set workspace folder
  rag -l                 # Use local embedding API
  rag -st                # Use sentence-transformers embeddings
        """
    )
    parser.add_argument("-w", nargs="*", metavar="PATH", help="Show or set watched workspace folder")
    parser.add_argument("-l", action="store_true", help="Use local embedding API")
    parser.add_argument("-st", action="store_true", help="Use sentence-transformers embeddings")
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # status
    subparsers.add_parser("status", help="Check all servers")
    
    # test
    subparsers.add_parser("test", help="Test embedding generation")
    
    # config
    subparsers.add_parser("config", help="Show configuration")
    
    # start
    start_parser = subparsers.add_parser("start", help="Start RAG server", add_help=False)
    
    # doctor
    subparsers.add_parser("doctor", help="Run smoke-test to verify system health")
    
    # dashboard
    subparsers.add_parser("dashboard", help="Generate sprint progress HTML dashboard")
    
    # watch
    subparsers.add_parser("watch", help="Start CORE watcher (auto-index + dashboard)")
    
    # stop
    subparsers.add_parser("stop", help="Stop all servers")

    args = parser.parse_args()

    if args.w is not None:
        set_workspace(args.w)
        return

    if args.l:
        set_embedding_source("local_api")
        return

    if args.st:
        set_embedding_source("sentence_transformers")
        return
    
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
    
    elif args.command == "doctor":
        doctor()
    
    elif args.command == "dashboard":
        import subprocess, sys as _sys
        dashboard_script = Path(__file__).parent / "goals_dashboard.py"
        result = subprocess.run(
            [_sys.executable, str(dashboard_script)],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            html = result.stdout
            print(html[-1500:])
            ok(f"Dashboard: {Path.home()/'CORE'/'dashboard.html'}")
        else:
            err(result.stderr.strip()[:200])
    
    elif args.command == "watch":
        import subprocess, sys as _sys
        watch_script = Path(__file__).parent / "core_watcher.py"
        info("Starting CORE watcher...")
        subprocess.run([_sys.executable, str(watch_script)])
    
    elif args.command == "config":
        show_config()
    
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