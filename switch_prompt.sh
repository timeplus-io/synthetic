#!/bin/bash

# Timeplus Prompt Mode Switcher
# Usage: source switch_prompt.sh [mode]
# Modes: safe, full, status

PROMPT_DIR="/Users/ma-justin/Downloads/Coding-Adventures/Random-Stream/prompt"
ENV_FILE="/Users/ma-justin/Downloads/Coding-Adventures/Random-Stream/.env_prompt"

# Function to switch to safe mode
switch_to_safe() {
    export TIMEPLUS_PROMPT_MODE="safe"
    export TIMEPLUS_ACTIVE_PROMPT_FILE="$PROMPT_DIR/prompt_safe.txt"
    export TIMEPLUS_FORCE_SAFE_MODE=true
    
    # Update .env_prompt file
    cat > "$ENV_FILE" << EOF
# Timeplus Prompt Configuration - Safe Mode Active
export TIMEPLUS_PROMPT_MODE="safe"
export TIMEPLUS_ACTIVE_PROMPT_FILE="$PROMPT_DIR/prompt_safe.txt"
export TIMEPLUS_FORCE_SAFE_MODE=true

# Safe mode uses array_element() and other compatible functions
# No generate() function calls will be used
EOF
    
    echo "✅ Switched to SAFE mode (no generate() function)"
    echo "📄 Active prompt: prompt_safe.txt"
    echo "🔒 TIMEPLUS_FORCE_SAFE_MODE=true"
}

# Function to switch to full mode
switch_to_full() {
    export TIMEPLUS_PROMPT_MODE="full"
    export TIMEPLUS_ACTIVE_PROMPT_FILE="$PROMPT_DIR/prompt_full.txt"
    unset TIMEPLUS_FORCE_SAFE_MODE
    
    # Update .env_prompt file
    cat > "$ENV_FILE" << EOF
# Timeplus Prompt Configuration - Full Mode Active
export TIMEPLUS_PROMPT_MODE="full"
export TIMEPLUS_ACTIVE_PROMPT_FILE="$PROMPT_DIR/prompt_full.txt"
# TIMEPLUS_FORCE_SAFE_MODE is not set (allowing generate() function)

# Full mode includes generate() function support
# Use when generate() function becomes available in Timeplus
EOF
    
    echo "🚀 Switched to FULL mode (with generate() function support)"
    echo "📄 Active prompt: prompt_full.txt"
    echo "🔓 TIMEPLUS_FORCE_SAFE_MODE unset"
}

# Function to show current status
show_status() {
    echo "=== Timeplus Prompt Mode Status ==="
    echo "Current mode: ${TIMEPLUS_PROMPT_MODE:-'not set'}"
    echo "Active prompt file: ${TIMEPLUS_ACTIVE_PROMPT_FILE:-'not set'}"
    echo "Safe mode forced: ${TIMEPLUS_FORCE_SAFE_MODE:-'false'}"
    echo ""
    echo "Available modes:"
    echo "  safe - Use array_element() and compatible functions only"
    echo "  full - Include generate() function support (for future use)"
    echo ""
    echo "Usage: source switch_prompt.sh [safe|full|status]"
}

# Main logic
case "$1" in
    "safe")
        switch_to_safe
        ;;
    "full")
        switch_to_full
        ;;
    "status")
        show_status
        ;;
    "")
        show_status
        echo ""
        read -p "Switch to which mode? (safe/full): " mode
        case "$mode" in
            "safe") switch_to_safe ;;
            "full") switch_to_full ;;
            *) echo "❌ Invalid mode. Use 'safe' or 'full'" ;;
        esac
        ;;
    *)
        echo "❌ Invalid argument. Use: safe, full, or status"
        show_status
        ;;
esac