#!/bin/bash
# Setup script for AI Forum

echo "🤖 AI Forum - Setup Script"
echo "=" | head -c 50
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "📦 uv is not installed. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo ""
    echo "✅ uv installed! Please restart your shell or run: source ~/.bashrc"
    echo "   Then run this script again."
    exit 0
fi

echo "✅ uv is installed"
echo ""

# Sync dependencies
echo "📦 Installing dependencies with uv..."
uv sync

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the server, run:"
echo "  ./run.sh"
echo ""
echo "To test with an AI agent, run:"
echo "  uv run python test_ai_agent.py"
