#!/bin/bash

# Autonomous Mower Deployment Script
# This script automates the deployment of the autonomous mower software to a Raspberry Pi
# It can be run remotely via SSH or locally on the Pi

# Exit on error
set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print error messages
print_error() {
    echo -e "${RED}ERROR: $1${NC}"
}

# Function to print success messages
print_success() {
    echo -e "${GREEN}SUCCESS: $1${NC}"
}

# Function to print warning messages
print_warning() {
    echo -e "${YELLOW}WARNING: $1${NC}"
}

# Function to print info messages
print_info() {
    echo -e "${YELLOW}INFO: $1${NC}"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a command succeeded
check_command() {
    if [ $? -ne 0 ]; then
        print_error "Command failed: $1"
        return 1
    fi
    return 0
}

# Function to cleanup on script failure
cleanup() {
    print_info "Cleaning up..."
    exit 1
}

# Set trap for cleanup
trap cleanup EXIT

# Parse command line arguments
BRANCH="main"
REMOTE_DEPLOY=false
REMOTE_HOST=""
REMOTE_USER="pi"
REMOTE_PORT="22"
SKIP_HARDWARE_CHECK=false
SKIP_CORAL=false
SKIP_REMOTE_ACCESS=false

# Display help message
show_help() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -h, --help                 Show this help message"
    echo "  -b, --branch BRANCH        Specify the branch to deploy (default: main)"
    echo "  -r, --remote HOST          Deploy to remote Raspberry Pi via SSH"
    echo "  -u, --user USER            Remote SSH username (default: pi)"
    echo "  -p, --port PORT            Remote SSH port (default: 22)"
    echo "  --skip-hardware-check      Skip hardware compatibility check"
    echo "  --skip-coral               Skip Coral TPU setup"
    echo "  --skip-remote-access       Skip remote access setup"
    echo ""
    echo "Examples:"
    echo "  $0                         # Deploy locally from current directory"
    echo "  $0 -b improvements         # Deploy locally from improvements branch"
    echo "  $0 -r raspberrypi.local    # Deploy to remote Pi using hostname"
    echo "  $0 -r 192.168.1.100 -u pi  # Deploy to remote Pi using IP address"
    echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -b|--branch)
            BRANCH="$2"
            shift 2
            ;;
        -r|--remote)
            REMOTE_DEPLOY=true
            REMOTE_HOST="$2"
            shift 2
            ;;
        -u|--user)
            REMOTE_USER="$2"
            shift 2
            ;;
        -p|--port)
            REMOTE_PORT="$2"
            shift 2
            ;;
        --skip-hardware-check)
            SKIP_HARDWARE_CHECK=true
            shift
            ;;
        --skip-coral)
            SKIP_CORAL=true
            shift
            ;;
        --skip-remote-access)
            SKIP_REMOTE_ACCESS=true
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Function to deploy locally
deploy_locally() {
    print_info "Starting local deployment..."

    # Check if we're in the repository root
    if [ ! -f "setup.py" ] || [ ! -d "src/mower" ]; then
        print_error "This script must be run from the repository root"
        exit 1
    fi

    # Check if we're on a Raspberry Pi
    if [ "$SKIP_HARDWARE_CHECK" = false ] && ! grep -q "Raspberry Pi" /proc/cpuinfo; then
        print_error "This script must be run on a Raspberry Pi"
        exit 1
    fi

    # Make sure we're on the correct branch
    print_info "Checking out branch: $BRANCH"
    git checkout $BRANCH
    check_command "Checking out branch $BRANCH" || exit 1

    # Pull latest changes
    print_info "Pulling latest changes..."
    git pull
    check_command "Pulling latest changes" || exit 1

    # Run the installation script
    print_info "Running installation script..."
    chmod +x install_requirements.sh

    # Create answers file for non-interactive installation
    if [ "$SKIP_CORAL" = true ]; then
        echo "n" > coral_answer.txt
    else
        echo "y" > coral_answer.txt
    fi

    # Run installation script with answers file
    sudo ./install_requirements.sh < coral_answer.txt
    check_command "Running installation script" || exit 1
    rm coral_answer.txt

    # Set up remote access if requested
    if [ "$SKIP_REMOTE_ACCESS" = false ]; then
        print_info "Setting up remote access..."
        python3 src/mower/utilities/setup_remote_access.py
        check_command "Setting up remote access" || exit 1
    fi

    # Create log directory if it doesn't exist
    print_info "Setting up log directory..."
    sudo mkdir -p /var/log/autonomous-mower
    sudo chown -R pi:pi /var/log/autonomous-mower
    sudo chmod 755 /var/log/autonomous-mower
    check_command "Setting up log directory" || exit 1

    # Enable and start the service
    print_info "Enabling and starting the services..."
    sudo systemctl enable ntrip-client.service
    sudo systemctl start ntrip-client.service
    sudo systemctl enable autonomous-mower.service
    sudo systemctl start autonomous-mower.service

    check_command "Enabling and starting the service" || exit 1

    # Check service status
    print_info "Checking service status..."
    sudo systemctl status ntrip-client.service
    sudo systemctl status autonomous-mower.service

    print_success "Deployment completed successfully!"
    print_info "You can access the web interface at http://localhost:5000"

    # Get IP address for remote access
    IP_ADDRESS=$(hostname -I | awk '{print $1}')
    print_info "Or access it remotely at http://$IP_ADDRESS:5000"
}

# Function to deploy to a remote Raspberry Pi
deploy_remotely() {
    print_info "Starting remote deployment to $REMOTE_HOST..."

    # Check if SSH is available
    if ! command_exists ssh; then
        print_error "SSH client not found. Please install SSH."
        exit 1
    fi

    # Check if we can connect to the remote host
    print_info "Checking SSH connection to $REMOTE_HOST..."
    ssh -p $REMOTE_PORT -o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=accept-new $REMOTE_USER@$REMOTE_HOST "echo SSH connection successful" || {
        print_error "Failed to connect to $REMOTE_HOST. Please check your SSH settings."
        exit 1
    }

    # Create a temporary deployment script to run on the remote host
    TEMP_SCRIPT=$(mktemp)
    cat > $TEMP_SCRIPT << EOF
#!/bin/bash

# Exit on error
set -e

# Clone the repository if it doesn't exist
if [ ! -d "autonomous_mower" ]; then
    echo "Cloning repository..."
    git clone https://github.com/yourusername/autonomous_mower.git
    cd autonomous_mower
else
    echo "Repository already exists, updating..."
    cd autonomous_mower
    git fetch
fi

# Checkout the specified branch
git checkout $BRANCH
git pull

# Run the deployment script locally
./scripts/deploy.sh $([ "$SKIP_HARDWARE_CHECK" = true ] && echo "--skip-hardware-check") \
                    $([ "$SKIP_CORAL" = true ] && echo "--skip-coral") \
                    $([ "$SKIP_REMOTE_ACCESS" = true ] && echo "--skip-remote-access")
EOF

    # Make the script executable
    chmod +x $TEMP_SCRIPT

    # Copy the script to the remote host
    print_info "Copying deployment script to $REMOTE_HOST..."
    scp -P $REMOTE_PORT $TEMP_SCRIPT $REMOTE_USER@$REMOTE_HOST:~/deploy_mower.sh
    check_command "Copying deployment script" || exit 1

    # Execute the script on the remote host
    print_info "Executing deployment script on $REMOTE_HOST..."
    ssh -p $REMOTE_PORT $REMOTE_USER@$REMOTE_HOST "chmod +x ~/deploy_mower.sh && ~/deploy_mower.sh"
    check_command "Remote deployment" || exit 1

    # Clean up
    rm $TEMP_SCRIPT
    ssh -p $REMOTE_PORT $REMOTE_USER@$REMOTE_HOST "rm ~/deploy_mower.sh"

    print_success "Remote deployment to $REMOTE_HOST completed successfully!"
    print_info "You can access the web interface at http://$REMOTE_HOST:5000"
}

# Main deployment logic
if [ "$REMOTE_DEPLOY" = true ]; then
    deploy_remotely
else
    deploy_locally
fi

# Remove trap and exit successfully
trap - EXIT
exit 0
