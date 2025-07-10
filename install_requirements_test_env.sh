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
# 2. Update apt and install minimal system dependencies (fast install)
print_info "Updating apt and installing minimal system dependencies..."
sudo DEBIAN_FRONTEND=noninteractive apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    python3-pip python3-venv git curl unzip

# Note: Development headers and heavy math libraries are skipped for test env.

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
print_info "Installing Python dependencies from pyproject.toml..."
pip install .[test]


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
