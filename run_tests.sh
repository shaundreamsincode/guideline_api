#!/bin/bash

# Test runner script for the guideline API
# Usage: ./run_tests.sh [options]

set -e

# Default values
TEST_TYPE="all"
COVERAGE=false
VERBOSE=false
PARALLEL=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --unit)
            TEST_TYPE="unit"
            shift
            ;;
        --integration)
            TEST_TYPE="integration"
            shift
            ;;
        --coverage)
            COVERAGE=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --parallel|-p)
            PARALLEL=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --unit              Run only unit tests"
            echo "  --integration       Run only integration tests"
            echo "  --coverage          Run with coverage report"
            echo "  --verbose, -v       Verbose output"
            echo "  --parallel, -p      Run tests in parallel"
            echo "  --help, -h          Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Set up environment
export DJANGO_SETTINGS_MODULE=app.test_settings
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Build pytest command
PYTEST_CMD="python -m pytest"

if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v"
fi

if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=jobs --cov-report=term-missing --cov-report=html"
fi

if [ "$PARALLEL" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -n auto"
fi

# Run tests based on type
case $TEST_TYPE in
    "unit")
        echo "Running unit tests..."
        $PYTEST_CMD -m "not integration" jobs/tests.py
        ;;
    "integration")
        echo "Running integration tests..."
        $PYTEST_CMD -m "integration" jobs/tests.py
        ;;
    "all")
        echo "Running all tests..."
        $PYTEST_CMD jobs/tests.py
        ;;
esac

echo "Tests completed successfully!" 