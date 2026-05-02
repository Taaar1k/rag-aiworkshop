#!/bin/bash
# Core Start Command - Launches all RAG services
# Cross-platform support for Linux, macOS, Windows

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Detect platform
detect_platform() {
    case "$(uname -s)" in
        Linux*)     echo "linux";;
        Darwin*)    echo "macos";;
        CYGWIN*)    echo "windows";;
        MINGW*)     echo "windows";;
        MSYS*)      echo "windows";;
        *)          echo "unknown";;
    esac
}

PLATFORM=$(detect_platform)
log_info "Detected platform: $PLATFORM"

# Check if running in virtual environment
check_venv() {
    if [ -z "$VIRTUAL_ENV" ]; then
        log_warn "Virtual environment not detected, attempting to activate..."
        
        # Try different venv paths
        if [ -f "$PROJECT_DIR/.venv/bin/activate" ]; then
            source "$PROJECT_DIR/.venv/bin/activate"
            log_info "Activated virtual environment"
        elif [ -f "$PROJECT_DIR/venv/bin/activate" ]; then
            source "$PROJECT_DIR/venv/bin/activate"
            log_info "Activated virtual environment"
        else
            log_warn "No virtual environment found at expected locations"
        fi
    fi
}

# Validate dependencies before starting
validate_dependencies() {
    log_info "Validating dependencies..."
    
    # Check Python is available
    if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
        log_error "Python is not installed or not in PATH"
        return 1
    fi
    
    # Check required files exist
    if [ ! -f "$PROJECT_DIR/models/llm/Llama-3-8B-Instruct-Q4_K_M.gguf" ]; then
        log_error "LLM model file not found: models/llm/Llama-3-8B-Instruct-Q4_K_M.gguf"
        return 1
    fi
    
    if [ ! -d "$PROJECT_DIR/models/embeddings" ]; then
        log_error "Embedding model directory not found: models/embeddings"
        return 1
    fi
    
    # Check required Python packages
    python3 -c "import requests" 2>/dev/null || {
        log_error "Python package 'requests' is not installed"
        return 1
    }
    
    python3 -c "import torch" 2>/dev/null || {
        log_warn "PyTorch not installed, some features may be unavailable"
    }
    
    python3 -c "from sentence_transformers import SentenceTransformer" 2>/dev/null || {
        log_warn "sentence-transformers not installed, embedding features may be unavailable"
    }
    
    log_info "All dependencies validated"
    return 0
}

# Start a single service
start_service() {
    local service_name=$1
    local service_command=$2
    local health_check_url=$3
    local startup_timeout=${4:-30}
    
    log_info "Starting service: $service_name"
    
    # Start the service in background
    eval "$service_command" > "$PROJECT_DIR/logs/${service_name}.log" 2>&1 &
    local pid=$!
    
    log_info "Service $service_name started (PID: $pid)"
    
    # Wait for health check if URL provided
    if [ -n "$health_check_url" ]; then
        log_info "Waiting for health check: $health_check_url"
        local wait_time=0
        while [ $wait_time -lt $startup_timeout ]; do
            if curl -s -f "$health_check_url" > /dev/null 2>&1; then
                log_info "Service $service_name is healthy"
                return 0
            fi
            sleep 1
            wait_time=$((wait_time + 1))
        done
        log_error "Service $service_name failed health check after ${startup_timeout}s"
        return 1
    fi
    
    return 0
}

# Start all services
start_all_services() {
    log_info "Starting all RAG services..."
    
    # Validate dependencies
    if ! validate_dependencies; then
        log_error "Dependency validation failed"
        return 1
    fi
    
    # Start services in order
    local success=true
    
    # Start LLM service
    if ! start_service "llm" \
        "python3 $PROJECT_DIR/src/core/service_orchestrator.py start" \
        "http://localhost:8080/health" \
        30; then
        success=false
    fi
    
    # Start embedding model
    if ! start_service "embedding_model" \
        "python3 $PROJECT_DIR/src/core/service_orchestrator.py start" \
        "" \
        60; then
        success=false
    fi
    
    # Start MCP server
    if ! start_service "mcp_server" \
        "python3 $PROJECT_DIR/src/mcp_server.py" \
        "http://localhost:8000/health" \
        15; then
        success=false
    fi
    
    if [ "$success" = true ]; then
        log_info "All services started successfully"
        log_info "RAG Core system is running"
        log_info "Press Ctrl+C to stop all services"
        
        # Keep running and handle interrupts
        trap 'log_info "Stopping services..."; bash "$SCRIPT_DIR/core_stop.sh"; exit 0' INT TERM
        
        while true; do
            sleep 1
        done
    else
        log_error "Failed to start all services"
        return 1
    fi
}

# Main execution
main() {
    log_info "RAG Core Start Command"
    log_info "======================"
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --config|-c)
                CONFIG_FILE="$2"
                shift 2
                ;;
            --verbose|-v)
                VERBOSE=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  -c, --config FILE    Path to config file"
                echo "  -v, --verbose        Verbose output"
                echo "  -h, --help           Show this help message"
                exit 0
                ;;
            *)
                shift
                ;;
        esac
    done
    
    # Check if already running
    if pgrep -f "service_orchestrator" > /dev/null; then
        log_warn "RAG Core services may already be running"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 0
        fi
    fi
    
    # Activate virtual environment FIRST (before any Python commands)
    check_venv
    
    # Validate dependencies (now with venv active)
    if ! validate_dependencies; then
        log_error "Dependency validation failed"
        return 1
    fi
    
    # Start all services
    start_all_services
}

main "$@"
