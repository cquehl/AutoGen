#!/bin/bash

#
# Suntory System v3 - Entry Point
# Your Distinguished AI Concierge Awaits
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Print with color
print_color() {
    color=$1
    shift
    echo -e "${color}$*${NC}"
}

print_header() {
    echo ""
    print_color "$CYAN" "═══════════════════════════════════════════════════════════"
    print_color "$CYAN" "  🥃  Suntory System v3 - Initialization"
    print_color "$CYAN" "═══════════════════════════════════════════════════════════"
    echo ""
}

print_step() {
    print_color "$BLUE" "▸ $*"
}

print_success() {
    print_color "$GREEN" "✓ $*"
}

print_warning() {
    print_color "$YELLOW" "⚠ $*"
}

print_error() {
    print_color "$RED" "✗ $*"
}

# Check if running in correct directory
if [ ! -f "Suntory.sh" ]; then
    print_error "Error: Must run from v3/ directory"
    exit 1
fi

# Print header
print_header

# Check Python version
print_step "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    echo "Please install Python 3.11 or later"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.11"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    print_error "Python $PYTHON_VERSION found, but Python $REQUIRED_VERSION or later is required"
    exit 1
fi

print_success "Python $PYTHON_VERSION found"

# Check for .env file
print_step "Checking environment configuration..."
if [ ! -f ".env" ]; then
    print_warning ".env file not found"
    echo ""
    echo "  Please create a .env file from .env.example:"
    echo "    cp .env.example .env"
    echo ""
    echo "  Then add your API keys:"
    echo "    - OPENAI_API_KEY"
    echo "    - ANTHROPIC_API_KEY"
    echo "    - GOOGLE_API_KEY"
    echo ""
    print_error "Cannot continue without .env file"
    exit 1
fi

print_success ".env file found"

# Check for API keys
if ! grep -q "OPENAI_API_KEY=sk-\|ANTHROPIC_API_KEY=sk-ant-\|GOOGLE_API_KEY=\w" .env 2>/dev/null; then
    print_warning "No API keys found in .env file"
    echo ""
    echo "  Please add at least one API key to .env:"
    echo "    - OPENAI_API_KEY=sk-..."
    echo "    - ANTHROPIC_API_KEY=sk-ant-..."
    echo "    - GOOGLE_API_KEY=..."
    echo ""
fi

# Check if virtual environment exists
print_step "Checking virtual environment..."
if [ ! -d "venv" ]; then
    print_warning "Virtual environment not found. Creating..."
    python3 -m venv venv
    print_success "Virtual environment created"
fi

# Activate virtual environment
source venv/bin/activate

# Check if dependencies are installed
print_step "Checking dependencies..."
if ! python -c "import autogen_agentchat" 2>/dev/null; then
    print_warning "Dependencies not installed. Installing..."
    pip install --upgrade pip > /dev/null 2>&1
    pip install -r requirements.txt
    print_success "Dependencies installed"
else
    print_success "Dependencies found"
fi

# Check Docker (optional but recommended)
print_step "Checking Docker..."
if ! command -v docker &> /dev/null; then
    print_warning "Docker not found (optional)"
    echo "  Docker provides sandboxed code execution for security."
    echo "  Install Docker from: https://docs.docker.com/get-docker/"
    echo ""
    echo "  Continuing without Docker sandbox..."
    echo ""
else
    if docker ps &> /dev/null; then
        print_success "Docker is running"

        # Check if containers need to be started
        if ! docker-compose ps | grep -q "suntory-chromadb.*Up" 2>/dev/null; then
            print_step "Starting Docker containers..."
            docker-compose up -d
            sleep 2
            print_success "Docker containers started"
        else
            print_success "Docker containers running"
        fi
    else
        print_warning "Docker daemon is not running"
        echo "  Please start Docker and run this script again for full functionality."
        echo ""
    fi
fi

# Create necessary directories
print_step "Preparing workspace..."
mkdir -p data logs workspace data/chroma
print_success "Workspace ready"

# Check database
if [ ! -f "data/suntory.db" ]; then
    print_step "Initializing database..."
    print_success "Database will be initialized on first run"
fi

# All checks passed
echo ""
print_color "$GREEN" "═══════════════════════════════════════════════════════════"
print_color "$GREEN" "  ✓ All checks passed! Starting Alfred..."
print_color "$GREEN" "═══════════════════════════════════════════════════════════"
echo ""

# Launch Alfred
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"
python -m src.interface.tui

# Cleanup message
echo ""
print_color "$CYAN" "Thank you for using Suntory System v3"
echo ""
