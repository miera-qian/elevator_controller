#!/bin/bash
# Start Elevator Scheduling WebUI
# This script starts the web visualization interface

echo "🚀 Starting Elevator Scheduling WebUI..."
echo ""
echo "📝 WebUI will be available at: http://localhost:8080"
echo ""
echo "Features:"
echo "  • Real-time elevator visualization"
echo "  • Multiple algorithm comparison"
echo "  • Interactive controls (pause/resume/speed)"
echo "  • Live statistics"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

uv run python -m webui.app
