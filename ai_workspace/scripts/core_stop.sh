#!/bin/bash
# Core Stop Command - Gracefully stops all RAG services
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

# Stop a single service
stop_service() {
    local service_name=$1
    local pid=$2
    local timeout=${3:-5}
    
    if [ -z "$pid" ] || [ "$pid" == "0" ]; then
        log_warn "Service $service_name not running (no PID)"
        return 0
    fi
    
    log_info "Stopping service: $service_name (PID: $pid)"
    
    # Try graceful termination first
    if [ "$PLATFORM" == "windows" ]; then
        taskkill /F /PID $pid > /dev/null 2>&1 || true
    else
        kill -TERM $pid 2>/dev/null || true
    fi
    
    # Wait for process to terminate
    local wait_time=0
    while kill -0 $pid 2>/dev/null; do
        if [ $wait_time -ge $timeout ]; then
            log_warn "Service $service_name did not stop gracefully, forcing kill..."
            if [ "$PLATFORM" == "windows" ]; then
                taskkill /F /PID $pid > /dev/null 2>&1 || true
            else
                kill -KILL $pid 2>/dev/null || true
            fi
            break
        fi
        sleep 1
        wait_time=$((wait_time + 1))
    done
    
    log_info "Service $service_name stopped"
    return 0
}

# Find service PIDs
find_service_pids() {
    local services=("mcp_server" "embedding_model" "llm")
    local pids=()
    
    for service in "${services[@]}"; do
        local pid
        if [ "$PLATFORM" == "windows" ]; then
            pid=$(pgrep -f "service_orchestrator" 2>/dev/null | head -1)
        else
            pid=$(pgrep -f "service_orchestrator" 2>/dev/null | head -1)
        fi
        
        if [ -n "$pid" ]; then
            pids+=("$service:$pid")
        fi
    done
    
    echo "${pids[@]}"
}

# Stop all services
stop_all_services() {
    local timeout=${1:-5}
    
    log_info "Stopping all RAG services..."
    log_info "Timeout: ${timeout}s"
    
    # Stop services in reverse order
    local services=("mcp_server" "embedding_model" "llm")
    local success=true
    
    for service in "${services[@]}"; do
        local pid=""
        
        # Find PID for this service
        if [ "$PLATFORM" == "windows" ]; then
            pid=$(pgrep -f "$service" 2>/dev/null | head -1)
        else
            pid=$(pgrep -f "$service" 2>/dev/null | head -1)
        fi
        
        if [ -n "$pid" ]; then
            if ! stop_service "$service" "$pid" "$timeout"; then
                success=false
            fi
        else
            log_warn "Service $service not running"
        fi
    done
    
    # Also stop any remaining orchestrator processes
    local orchestrator_pids=$(pgrep -f "service_orchestrator" 2>/dev/null || true)
    if [ -n "$orchestrator_pids" ]; then
        for pid in $orchestrator_pids; do
            stop_service "orchestrator" "$pid" "$timeout"
        done
    fi
    
    if [ "$success" = true ]; then
        log_info "All services stopped successfully"
    else
        log_error "Some services failed to stop"
        return 1
    fi
}

# Main execution
main() {
    local timeout=5
    
    log_info "RAG Core Stop Command"
    log_info "====================="
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --timeout|-t)
                timeout=$2
                shift 2
                ;;
            --force|-f)
                timeout=0
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  -t, --timeout SEC    Shutdown timeout in seconds (default: 5)"
                echo "  -f, --force          Force stop without graceful shutdown"
                echo "  -h, --help           Show this help message"
                exit 0
                ;;
            *)
                shift
                ;;
        esac
    done
    
    log_info "Stopping services with ${timeout}s timeout"
    
    # Stop all services
    stop_all_services "$timeout"
}

main "$@"
