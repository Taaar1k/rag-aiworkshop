#!/bin/bash
# RAG CLI Installer

install_rag_cli() {
    # Add to zshrc (default on Arch)
    local shellrc="$HOME/.zshrc"
    
    if grep -q "RAG CLI" "$shellrc" 2>/dev/null; then
        echo "RAG CLI already installed."
        return
    fi
    
    cat >> "$shellrc" << 'EOF'

# RAG CLI
export RAG_ROOT="/home/tarik/Sandbox/my-plugin/rag-project/ai_workspace"

rag() {
    cd "$RAG_ROOT" && python scripts/rag_cli.py "${1:-status}"
}

rag-start() {
    cd "$RAG_ROOT" && uvicorn src.api.rag_server:app --host 0.0.0.0 --port 8000
}

rag-test() {
    cd "$RAG_ROOT" && python scripts/rag_cli.py test
}

rag-status() {
    cd "$RAG_ROOT" && python scripts/rag_cli.py status
}

rag-config() {
    cd "$RAG_ROOT" && python scripts/rag_cli.py config
}

alias rag-set="rag set-embedding"
alias rag-on="rag-start"
EOF
    
    echo "Installed to $shellrc"
    echo "Run: rag status"
}

uninstall_rag_cli() {
    sed -i '/# RAG CLI/,/alias rag-on/d' "$HOME/.zshrc" 2>/dev/null
    echo "Removed"
}

case "${1:-install}" in
    install) install_rag_cli ;;
    uninstall) uninstall_rag_cli ;;
    *) echo "Usage: $0 [install|uninstall]" ;;
esac