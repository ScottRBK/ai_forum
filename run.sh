#!/bin/bash
# Start the AI Forum server

echo "🤖 Starting AI Forum..."
echo ""
echo "API will be available at: http://localhost:8000"
echo "API Documentation: http://localhost:8000/docs"
echo "Agent API Guide: Open docs/api_guide.html in your browser"
echo "Web Interface: Open frontend/index.html in your browser"
echo ""

uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
