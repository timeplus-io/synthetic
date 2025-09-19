#!/bin/bash

# Timeplus Prompt Mode Aliases
# Add to your .zshrc or .bashrc: source /path/to/prompt_aliases.sh

SCRIPT_DIR="/Users/ma-justin/Downloads/Coding-Adventures/Random-Stream"

# Quick aliases for prompt switching
alias tp-safe="source $SCRIPT_DIR/switch_prompt.sh safe"
alias tp-full="source $SCRIPT_DIR/switch_prompt.sh full"
alias tp-status="source $SCRIPT_DIR/switch_prompt.sh status"
alias tp-switch="source $SCRIPT_DIR/switch_prompt.sh"

# Load current prompt environment if it exists
if [ -f "$SCRIPT_DIR/.env_prompt" ]; then
    source "$SCRIPT_DIR/.env_prompt"
fi

echo "Timeplus prompt aliases loaded:"
echo "  tp-safe   - Switch to safe mode (array_element, no generate)"
echo "  tp-full   - Switch to full mode (with generate support)"  
echo "  tp-status - Show current mode status"
echo "  tp-switch - Interactive mode switcher"