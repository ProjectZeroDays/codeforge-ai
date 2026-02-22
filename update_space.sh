#!/bin/bash
# =============================================================================
# CodeForge AI - Quick Update Script for HuggingFace Spaces
# =============================================================================
# Usage: ./update_space.sh [options]
#
# Options:
#   --space-name NAME    Space name (default: codeforge-ai)
#   --gradio             Update Gradio-only version
#   --sync-secrets       Also sync .env secrets
# =============================================================================

set -e

# Default values
SPACE_NAME="codeforge-ai"
GRADIO_ONLY=""
SYNC_SECRETS=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --space-name)
            SPACE_NAME="$2"
            shift 2
            ;;
        --gradio)
            GRADIO_ONLY="--gradio-only"
            shift
            ;;
        --sync-secrets)
            SYNC_SECRETS="--sync-secrets"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "================================================="
echo "  CodeForge AI - Quick Update"
echo "================================================="
echo ""
echo "Space: $SPACE_NAME"
echo "Mode: ${GRADIO_ONLY:-Full deployment}"
echo ""

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required"
    exit 1
fi

# Check for huggingface_hub
python3 -c "import huggingface_hub" 2>/dev/null || {
    echo "Installing huggingface_hub..."
    pip install huggingface_hub
}

# Run deployment script
echo "Starting update..."
python3 deploy_to_huggingface.py \
    --space-name "$SPACE_NAME" \
    --update \
    $GRADIO_ONLY \
    $SYNC_SECRETS

echo ""
echo "Update complete!"
echo "Visit: https://huggingface.co/spaces/$(whoami)/$SPACE_NAME"
