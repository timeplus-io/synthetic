#!/bin/bash

# Timeplus Prompt Mode Switcher
# Usage: source switch_prompt.sh [simple|full|status]

PROMPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/prompt"
ENV_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.env_prompt"

# Set mode and update environment
set_mode() {
    local mode="$1"
    export TIMEPLUS_PROMPT_MODE="$mode"
    export TIMEPLUS_ACTIVE_PROMPT_FILE="$PROMPT_DIR/prompt_$mode.txt"
    
    if [ "$mode" = "simple" ]; then
        export TIMEPLUS_FORCE_SAFE_MODE=true
        echo "✅ SIMPLE mode (array_element, no generate)"
    else
        unset TIMEPLUS_FORCE_SAFE_MODE
        echo "🚀 FULL mode (with generate() function)"
    fi
    
    # Update .env_prompt file
    cat > "$ENV_FILE" << EOF
export TIMEPLUS_PROMPT_MODE="$mode"
export TIMEPLUS_ACTIVE_PROMPT_FILE="$PROMPT_DIR/prompt_$mode.txt"
EOF
    if [ "$mode" = "simple" ]; then
        echo "export TIMEPLUS_FORCE_SAFE_MODE=true" >> "$ENV_FILE"
    fi
    
    echo "📄 Active: prompt_$mode.txt"
}

# Show current status
show_status() {
    echo "=== Current Mode: ${TIMEPLUS_PROMPT_MODE:-'not set'} ==="
    echo "Prompt file: ${TIMEPLUS_ACTIVE_PROMPT_FILE:-'not set'}"
    echo "Safe mode: ${TIMEPLUS_FORCE_SAFE_MODE:-'false'}"
    echo ""
    echo "Available: simple | full | status"
}

# Main logic
case "${1:-status}" in
    "simple"|"full")
        set_mode "$1"
        ;;
    "status"|"")
        show_status
        if [ "$1" = "" ]; then
            read -p "Switch to which mode? (simple/full): " mode
            [ "$mode" = "simple" ] || [ "$mode" = "full" ] && set_mode "$mode" || echo "❌ Invalid mode"
        fi
        ;;
    *)
        echo "❌ Usage: source switch_prompt.sh [simple|full|status]"
        ;;
esac
