#!/bin/bash
#
# Test runner script for WebUI
# Usage: ./run_tests.sh [options]
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default options
INSTALL_DEPS=false
RUN_COVERAGE=false
TEST_PATH="webui/tests/"
VERBOSE="-v"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --install)
            INSTALL_DEPS=true
            shift
            ;;
        --coverage)
            RUN_COVERAGE=true
            shift
            ;;
        --quiet)
            VERBOSE=""
            shift
            ;;
        --unit)
            TEST_PATH="webui/tests/test_*.py"
            shift
            ;;
        --integration)
            TEST_PATH="webui/tests/test_integration.py"
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --install      Install test dependencies"
            echo "  --coverage     Generate coverage report"
            echo "  --quiet        Reduce output verbosity"
            echo "  --unit         Run only unit tests"
            echo "  --integration  Run only integration tests"
            echo "  --help         Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Install dependencies if requested
if [ "$INSTALL_DEPS" = true ]; then
    echo -e "${YELLOW}Installing test dependencies...${NC}"
    uv add --dev pytest pytest-asyncio pytest-timeout httpx
    echo -e "${GREEN}✓ Dependencies installed${NC}"
    echo ""
fi

# Check if pytest is available
if ! uv run python -c "import pytest" 2>/dev/null; then
    echo -e "${RED}Error: pytest not found!${NC}"
    echo -e "${YELLOW}Run with --install to install dependencies${NC}"
    exit 1
fi

# Print test configuration
echo -e "${YELLOW}Running WebUI tests...${NC}"
echo "Test path: $TEST_PATH"
if [ "$RUN_COVERAGE" = true ]; then
    echo "Coverage: enabled"
fi
echo ""

# Run tests
if [ "$RUN_COVERAGE" = true ]; then
    uv run pytest $TEST_PATH $VERBOSE \
        --cov=webui \
        --cov-report=html \
        --cov-report=term-missing

    echo ""
    echo -e "${GREEN}✓ Tests completed with coverage${NC}"
    echo -e "${YELLOW}Coverage report: htmlcov/index.html${NC}"
else
    uv run pytest $TEST_PATH $VERBOSE

    echo ""
    echo -e "${GREEN}✓ Tests completed${NC}"
fi
