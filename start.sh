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

check_pip() {
    print_step "Checking pip..."

    # Ensure pip is available
    if ! python3 -m pip --version &> /dev/null; then
        print_warning "pip is not available, trying to bootstrap..."

        # Try different methods to get pip
        # Method 1: Use ensurepip (built into Python 3.4+)
        if python3 -m ensurepip --user &> /dev/null; then
            print_success "pip installed via ensurepip"
        # Method 2: Download get-pip.py
        elif command -v curl &> /dev/null; then
            print_step "Downloading pip installer..."
            if curl -sSL https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py; then
                python3 /tmp/get-pip.py --user
                rm -f /tmp/get-pip.py
                print_success "pip installed via get-pip.py"
            fi
        elif command -v wget &> /dev/null; then
            print_step "Downloading pip installer..."
            if wget -q https://bootstrap.pypa.io/get-pip.py -O /tmp/get-pip.py; then
                python3 /tmp/get-pip.py --user
                rm -f /tmp/get-pip.py
                print_success "pip installed via get-pip.py"
            fi
        else
            print_error "Failed to install pip"
            echo "Please install pip manually:"
            echo "  Windows: python -m ensurepip --upgrade"
            echo "  Or download: https://bootstrap.pypa.io/get-pip.py"
            exit 1
        fi
    else
        print_success "pip is available"
    fi

    # Upgrade pip to latest version (suppress output)
    print_step "Ensuring pip is up to date..."
    python3 -m pip install --user --upgrade pip --quiet 2>/dev/null || true
    print_success "pip is ready"
}

check_uv() {
    print_step "Checking uv installation..."

    if ! command -v uv &> /dev/null; then
        print_warning "uv is not installed"
        print_step "Installing uv via pip..."

        # Install uv using pip (cross-platform: Windows, macOS, Linux)
        if python3 -m pip install --user uv; then
            print_success "uv installed via pip"

            # Determine user bin directory based on OS
            if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
                # Windows (Git Bash/MSYS/Cygwin)
                USER_SCRIPTS=$(python3 -c "import site; print(site.USER_SITE.replace('site-packages', 'Scripts'))" 2>/dev/null)
                if [ -d "$USER_SCRIPTS" ]; then
                    export PATH="$USER_SCRIPTS:$PATH"
                    print_step "Added $USER_SCRIPTS to PATH"
                fi
                # Also add Windows Python Scripts directory
                PYTHON_SCRIPTS=$(python3 -c "import os, sys; print(os.path.join(os.path.dirname(sys.executable), 'Scripts'))" 2>/dev/null)
                if [ -d "$PYTHON_SCRIPTS" ]; then
                    export PATH="$PYTHON_SCRIPTS:$PATH"
                fi
            else
                # Unix-like systems (macOS, Linux)
                USER_BIN="$HOME/.local/bin"
                if [ -d "$USER_BIN" ] && [[ ":$PATH:" != *":$USER_BIN:"* ]]; then
                    export PATH="$USER_BIN:$PATH"
                    print_step "Added $USER_BIN to PATH"
                fi

                # Also check Python user base
                PYTHON_USER_BASE=$(python3 -m site --user-base 2>/dev/null)
                if [ -n "$PYTHON_USER_BASE" ] && [ -d "$PYTHON_USER_BASE/bin" ]; then
                    export PATH="$PYTHON_USER_BASE/bin:$PATH"
                fi
            fi

            # Verify installation
            if ! command -v uv &> /dev/null; then
                print_error "uv installed but not found in PATH"
                echo ""
                echo "Please add uv to your PATH manually:"
                echo ""
                if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
                    echo "  Windows: Add Python Scripts directory to PATH"
                    echo "  Location: $(python3 -c "import os, sys; print(os.path.join(os.path.dirname(sys.executable), 'Scripts'))" 2>/dev/null || echo "C:\\Users\\<YourUser>\\AppData\\Local\\Programs\\Python\\Python3X\\Scripts")"
                else
                    echo "  Unix: Add to ~/.bashrc or ~/.zshrc:"
                    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
                fi
                echo ""
                echo "Then restart your terminal and run this script again."
                exit 1
            fi

            print_success "uv is now available"
        else
            print_error "Failed to install uv via pip"
            echo ""
            echo "Troubleshooting steps:"
            echo "1. Upgrade pip: python3 -m pip install --upgrade pip"
            echo "2. Try again: python3 -m pip install --user uv"
            echo "3. Check Python version: python3 --version (need 3.12+)"
            exit 1
        fi
    else
        UV_VERSION=$(uv --version 2>/dev/null | awk '{print $2}' || echo "unknown")
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
    # Use different methods based on OS
    if command -v lsof &> /dev/null; then
        # Unix/macOS: use lsof
        if lsof -Pi :$SIMULATOR_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
            return 0  # Running
        fi
    elif command -v netstat &> /dev/null; then
        # Windows/fallback: use netstat
        if netstat -an 2>/dev/null | grep -q ":$SIMULATOR_PORT.*LISTEN"; then
            return 0  # Running
        fi
    else
        # Fallback: try to connect
        if timeout 1 bash -c "cat < /dev/null > /dev/tcp/127.0.0.1/$SIMULATOR_PORT" 2>/dev/null; then
            return 0  # Running
        fi
    fi
    return 1  # Not running
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

    # Step 2: Check pip
    check_pip
    echo ""

    # Step 3: Check/Install uv
    check_uv
    echo ""

    # Step 4: Install dependencies
    install_dependencies
    echo ""

    # Step 5: Start simulator
    start_simulator
    echo ""

    # Step 6: Run controller
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
