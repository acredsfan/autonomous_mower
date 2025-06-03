#!/bin/bash

# Autonomous Mower Test Environment Requirements Installer
# For: Ubuntu 24.04 (virtualized/test environment)
# This script installs all Python and system requirements needed to run the autonomous_mower project
# in a non-hardware, non-Google Coral, non-emergency-stop, non-interactive test environment.
#
# Usage: bash install_requirements_test_env.sh
#
# Follows project coding standards (see .github/copilot-instructions-gemini.md)

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${YELLOW}INFO:${NC} $1"
}
print_success() {
    echo -e "${GREEN}SUCCESS:${NC} $1"
}
print_error() {
    echo -e "${RED}ERROR:${NC} $1"
}

# 1. Check OS
if ! grep -qi 'ubuntu' /etc/os-release || ! grep -q '24.04' /etc/os-release; then
    print_error "This script is intended for Ubuntu 24.04 only."
    exit 1
fi
print_info "Ubuntu 24.04 detected."

# 2. Update and install system dependencies
print_info "Updating apt and installing system dependencies..."
sudo DEBIAN_FRONTEND=noninteractive apt-get -y -qq update
sudo DEBIAN_FRONTEND=noninteractive apt-get -y -qq --no-install-recommends install python3 python3-pip \
    python3-venv python3-dev build-essential git libffi-dev libssl-dev \
    libjpeg-dev zlib1g-dev libopenblas-dev liblapack-dev libhdf5-dev libatlas-base-dev libpq-dev \
    libxml2-dev libxslt1-dev libyaml-dev libfreetype6-dev pkg-config

# 3. (Optional) Install additional system packages for test/dev
sudo apt-get install -y net-tools curl unzip

# 4. Set up Python virtual environment
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
    print_info "Creating Python virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"
print_success "Virtual environment activated."

# 5. Upgrade pip and wheel
pip install --upgrade pip wheel setuptools

# 6. Install Python requirements
REQ_FILE="requirements-ubuntu2404.txt"
if [ ! -f "$REQ_FILE" ]; then
    print_error "requirements-ubuntu2404.txt not found!"
    exit 1
fi
print_info "Installing Python dependencies from $REQ_FILE..."
	pip install --only-binary=:all: -r "$REQ_FILE"

# 7. (Optional) Install dev/test requirements if present
if [ -f "requirements-ubuntu2404.txt" ]; then
    print_info "Installing dev dependencies from requirements-ubuntu2404.txt..."
    pip install -r requirements-ubuntu2404.txt
fi

# 8. (Optional) Pre-commit hooks
if [ -f ".pre-commit-config.yaml" ]; then
    print_info "Installing pre-commit hooks..."
    pip install pre-commit
    pre-commit install
fi

# 9. Print summary
print_success "All requirements installed for test environment."
print_info "To activate the virtual environment later, run: source $VENV_DIR/bin/activate"
print_info "You can now run tests with: pytest"

# 10. Reminder: Hardware features are not installed in this environment
print_info "Note: Hardware setup (I2C, GPIO, Coral, emergency stop, etc.) is skipped in this test environment."

exit 0
