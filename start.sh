#!/bin/bash
################################################################################
# Elevator Controller Startup Script
#
# This script automates the complete setup and launch process:
# 1. Checks and installs uv (Python package manager)
# 2. Installs project dependencies
# 3. Starts the simulator server in background
# 4. Runs the elevator controller
#
# Usage:
#   ./start_controller.sh
#
# Requirements:
#   - Python 3.12 or higher
#   - Internet connection (for first-time setup)
################################################################################

set -e  # Exit on error

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SIMULATOR_PORT=8000
SIMULATOR_HOST="127.0.0.1"
SIMULATOR_LOG="logs/simulator_${SIMULATOR_PORT}.log"
SIMULATOR_PID_FILE="/tmp/elevator_simulator_${SIMULATOR_PORT}.pid"

################################################################################
# Helper Functions
################################################################################

print_header() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_step() {
    echo -e "${BLUE}▶${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

################################################################################
# Cleanup Function
################################################################################

cleanup() {
    echo ""
    print_header "Cleaning up..."

    # Stop simulator if running
    if [ -f "$SIMULATOR_PID_FILE" ]; then
        SIMULATOR_PID=$(cat "$SIMULATOR_PID_FILE")
        if ps -p $SIMULATOR_PID > /dev/null 2>&1; then
            print_step "Stopping simulator (PID: $SIMULATOR_PID)..."
            kill $SIMULATOR_PID 2>/dev/null || true
            sleep 1
            # Force kill if still running
            if ps -p $SIMULATOR_PID > /dev/null 2>&1; then
                kill -9 $SIMULATOR_PID 2>/dev/null || true
            fi
            print_success "Simulator stopped"
        fi
        rm -f "$SIMULATOR_PID_FILE"
    fi

    print_success "Cleanup complete"
    exit 0
}

# Register cleanup function
trap cleanup SIGINT SIGTERM EXIT

################################################################################
# Environment Check and Setup
################################################################################

check_python() {
    print_step "Checking Python version..."

    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        echo "Please install Python 3.12 or higher from https://www.python.org/"
        exit 1
    fi

    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    REQUIRED_VERSION="3.12"

    if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
        print_error "Python $PYTHON_VERSION is installed, but Python $REQUIRED_VERSION or higher is required"
        exit 1
    fi

    print_success "Python $PYTHON_VERSION found"
}

check_uv() {
    print_step "Checking uv installation..."

    if ! command -v uv &> /dev/null; then
        print_warning "uv is not installed"
        print_step "Installing uv..."

        # Install uv based on OS
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            if command -v brew &> /dev/null; then
                print_step "Installing uv via Homebrew..."
                brew install uv
            else
                print_step "Installing uv via curl..."
                curl -LsSf https://astral.sh/uv/install.sh | sh
            fi
        else
            # Linux
            print_step "Installing uv via curl..."
            curl -LsSf https://astral.sh/uv/install.sh | sh
        fi

        # Source the shell profile to update PATH
        if [ -f "$HOME/.cargo/env" ]; then
            source "$HOME/.cargo/env"
        fi

        # Verify installation
        if ! command -v uv &> /dev/null; then
            print_error "Failed to install uv"
            echo "Please install manually: https://github.com/astral-sh/uv"
            exit 1
        fi

        print_success "uv installed successfully"
    else
        UV_VERSION=$(uv --version | awk '{print $2}')
        print_success "uv $UV_VERSION found"
    fi
}

install_dependencies() {
    print_step "Installing project dependencies..."

    # Create logs directory if it doesn't exist
    mkdir -p logs

    # Sync dependencies using uv
    if uv sync; then
        print_success "Dependencies installed successfully"
    else
        print_error "Failed to install dependencies"
        exit 1
    fi
}

################################################################################
# Simulator Management
################################################################################

check_simulator_running() {
    # Check if simulator is already running on the port
    if lsof -Pi :$SIMULATOR_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Running
    else
        return 1  # Not running
    fi
}

start_simulator() {
    print_step "Starting simulator server..."

    # Check if already running
    if check_simulator_running; then
        print_warning "Simulator is already running on port $SIMULATOR_PORT"
        print_step "Using existing simulator instance"
        return 0
    fi

    # Start simulator in background
    uv run python -m elevator_saga.server.simulator \
        --host $SIMULATOR_HOST \
        --port $SIMULATOR_PORT \
        --debug > "$SIMULATOR_LOG" 2>&1 &

    SIMULATOR_PID=$!
    echo $SIMULATOR_PID > "$SIMULATOR_PID_FILE"

    print_step "Waiting for simulator to start (PID: $SIMULATOR_PID)..."

    # Wait for simulator to be ready (max 30 seconds)
    MAX_ATTEMPTS=30
    ATTEMPT=0
    while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
        if curl -s "http://${SIMULATOR_HOST}:${SIMULATOR_PORT}/api/state" > /dev/null 2>&1; then
            print_success "Simulator is ready on http://${SIMULATOR_HOST}:${SIMULATOR_PORT}"
            print_success "Simulator logs: $SIMULATOR_LOG"
            return 0
        fi

        # Check if process is still running
        if ! ps -p $SIMULATOR_PID > /dev/null 2>&1; then
            print_error "Simulator process died unexpectedly"
            if [ -f "$SIMULATOR_LOG" ]; then
                echo "Last 20 lines of simulator log:"
                tail -20 "$SIMULATOR_LOG"
            fi
            exit 1
        fi

        ATTEMPT=$((ATTEMPT + 1))
        sleep 1
    done

    print_error "Simulator failed to start within 30 seconds"
    if [ -f "$SIMULATOR_LOG" ]; then
        echo "Last 20 lines of simulator log:"
        tail -20 "$SIMULATOR_LOG"
    fi
    exit 1
}

################################################################################
# Main Execution
################################################################################

main() {
    print_header "🚀 Elevator Controller Startup"
    echo ""

    # Step 1: Check Python
    check_python
    echo ""

    # Step 2: Check/Install uv
    check_uv
    echo ""

    # Step 3: Install dependencies
    install_dependencies
    echo ""

    # Step 4: Start simulator
    start_simulator
    echo ""

    # Step 5: Run controller
    print_header "🎮 Starting Elevator Controller"
    echo ""
    print_step "Press Ctrl+C to stop"
    echo ""

    # Run the controller with all passed arguments
    uv run python elevator_controller.py "$@"
}

################################################################################
# Entry Point
################################################################################

# Change to script directory
cd "$(dirname "$0")"

# Run main function
main "$@"
