#!/bin/bash
################################################################################
# Elevator Controller WebUI Startup Script
#
# This script automates the complete setup and launch of the Web UI:
# 1. Checks Python version (3.12+)
# 2. Ensures pip is available
# 3. Installs uv if not present (no Homebrew required)
# 4. Installs project dependencies via uv sync
# 5. Starts the WebUI visualization interface
#
# Usage:
#   ./start.sh
#
# Requirements:
#   - Python 3.12 or higher
#   - Internet connection (for first-time setup)
#
# Features:
#   • Real-time elevator visualization
#   • Multiple algorithm comparison
#   • Interactive controls (pause/resume/speed)
#   • Live statistics and metrics
################################################################################

set -e  # Exit on error

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

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

        # Try to use ensurepip (built into Python 3.4+)
        if python3 -m ensurepip &> /dev/null; then
            print_success "pip installed via ensurepip"
        else
            print_error "Failed to install pip"
            echo "Please install pip manually:"
            echo "  python3 -m ensurepip --upgrade"
            echo "  Or download: https://bootstrap.pypa.io/get-pip.py"
            exit 1
        fi
    else
        print_success "pip is available"
    fi

    # Upgrade pip to latest version
    print_step "Ensuring pip is up to date..."
    python3 -m pip install --upgrade pip --quiet 2>/dev/null || true
    print_success "pip is ready"
}

check_uv() {
    print_step "Checking uv installation..."

    # Check if uv is already in PATH
    if command -v uv &> /dev/null; then
        UV_VERSION=$(uv --version 2>/dev/null | awk '{print $2}' || echo "unknown")
        print_success "uv $UV_VERSION found in PATH"
        return 0
    fi

    # Check common installation locations
    UV_PATHS=(
        "/opt/homebrew/bin/uv"
        "$HOME/.local/bin/uv"
        "$HOME/.cargo/bin/uv"
    )

    for UV_PATH in "${UV_PATHS[@]}"; do
        if [ -f "$UV_PATH" ]; then
            export PATH="$(dirname "$UV_PATH"):$PATH"
            UV_VERSION=$($UV_PATH --version 2>/dev/null | awk '{print $2}' || echo "unknown")
            print_success "uv $UV_VERSION found at $UV_PATH"
            return 0
        fi
    done

    # uv not found, install it via pip
    print_warning "uv is not installed"
    print_step "Installing uv via pip (this may take a moment)..."

    # Install uv WITHOUT --user flag to avoid virtualenv conflicts
    if python3 -m pip install uv --quiet; then
        print_success "uv installed successfully"

        # Add common binary directories to PATH
        if [[ "$OSTYPE" == "darwin"* ]] || [[ "$OSTYPE" == "linux-gnu"* ]]; then
            # Unix-like systems
            export PATH="$HOME/.local/bin:$PATH"
            PYTHON_USER_BASE=$(python3 -m site --user-base 2>/dev/null)
            if [ -n "$PYTHON_USER_BASE" ] && [ -d "$PYTHON_USER_BASE/bin" ]; then
                export PATH="$PYTHON_USER_BASE/bin:$PATH"
            fi
        fi

        # Verify installation
        if command -v uv &> /dev/null; then
            UV_VERSION=$(uv --version 2>/dev/null | awk '{print $2}' || echo "unknown")
            print_success "uv $UV_VERSION is now available"
        else
            print_error "uv installed but not found in PATH"
            echo ""
            echo "Please add uv to your PATH manually:"
            echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
            echo ""
            echo "Then restart your terminal and run this script again."
            exit 1
        fi
    else
        print_error "Failed to install uv via pip"
        echo ""
        echo "Troubleshooting steps:"
        echo "1. Upgrade pip: python3 -m pip install --upgrade pip"
        echo "2. Try again: python3 -m pip install uv"
        echo "3. Check Python version: python3 --version (need 3.12+)"
        exit 1
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
        echo ""
        echo "Troubleshooting:"
        echo "1. Check your internet connection"
        echo "2. Try: uv sync --reinstall"
        echo "3. Check pyproject.toml for syntax errors"
        exit 1
    fi
}

################################################################################
# Main Execution
################################################################################

main() {
    print_header "🚀 Elevator Controller WebUI Startup"
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

    # Step 5: Display WebUI info
    print_header "🎨 Starting WebUI"
    echo ""
    echo -e "${GREEN}📝 WebUI will be available at: http://localhost:8080${NC}"
    echo ""
    echo "Features:"
    echo "  • Real-time elevator visualization"
    echo "  • Multiple algorithm comparison"
    echo "  • Interactive controls (pause/resume/speed)"
    echo "  • Live statistics and metrics"
    echo ""
    print_step "Press Ctrl+C to stop the server"
    echo ""

    # Step 6: Start WebUI
    uv run python -m webui.app
}

################################################################################
# Entry Point
################################################################################

# Change to script directory
cd "$(dirname "$0")"

# Run main function
main "$@"
