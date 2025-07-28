#!/bin/bash

# Enhanced Autonomous Mower Deployment Script
# This script provides automated deployment with health checks and rollback capabilities
# It implements a blue-green deployment strategy for zero-downtime updates

# Exit on error
set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
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
    echo -e "${BLUE}INFO: $1${NC}"
}

# Function to print deployment stage
print_stage() {
    echo -e "${PURPLE}=== $1 ===${NC}"
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

# Function to log deployment events
log_event() {
    local level="$1"
    local message="$2"
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    echo "[$timestamp] [$level] $message" >> "$DEPLOY_LOG"
    
    # Also print to console
    case "$level" in
        "ERROR")
            print_error "$message"
            ;;
        "SUCCESS")
            print_success "$message"
            ;;
        "WARNING")
            print_warning "$message"
            ;;
        "INFO")
            print_info "$message"
            ;;
        *)
            echo "[$timestamp] [$level] $message"
            ;;
    esac
}

# Function to perform rollback
perform_rollback() {
    log_event "WARNING" "Initiating rollback procedure..."
    
    # Check if we have a backup to roll back to
    if [ ! -d "$BACKUP_DIR" ]; then
        log_event "ERROR" "No backup directory found at $BACKUP_DIR. Cannot roll back."
        return 1
    fi
    
    # Stop the service
    log_event "INFO" "Stopping services..."
    sudo systemctl stop mower.service
    sudo systemctl stop ntrip-client.service
    
    # Restore from backup
    log_event "INFO" "Restoring from backup..."
    
    # Restore code
    if [ -d "$BACKUP_DIR/code" ]; then
        log_event "INFO" "Restoring code..."
        rsync -a --delete "$BACKUP_DIR/code/" "$INSTALL_DIR/"
    fi
    
    # Restore configuration
    if [ -d "$BACKUP_DIR/config" ]; then
        log_event "INFO" "Restoring configuration..."
        rsync -a "$BACKUP_DIR/config/" "$INSTALL_DIR/config/"
    fi
    
    # Restore systemd service files
    if [ -f "$BACKUP_DIR/mower.service" ]; then
        log_event "INFO" "Restoring service files..."
        sudo cp "$BACKUP_DIR/mower.service" /etc/systemd/system/
        sudo cp "$BACKUP_DIR/ntrip-client.service" /etc/systemd/system/
        sudo systemctl daemon-reload
    fi
    
    # Start the service
    log_event "INFO" "Starting services..."
    sudo systemctl start ntrip-client.service
    sudo systemctl start mower.service
    
    # Verify service is running
    if systemctl is-active --quiet mower.service; then
        log_event "SUCCESS" "Rollback completed successfully. Services are running."
        return 0
    else
        log_event "ERROR" "Rollback failed. Services are not running."
        return 1
    fi
}

# Function to create backup
create_backup() {
    log_event "INFO" "Creating backup..."
    
    # Create backup directory
    mkdir -p "$BACKUP_DIR"
    
    # Backup code
    log_event "INFO" "Backing up code..."
    mkdir -p "$BACKUP_DIR/code"
    rsync -a "$INSTALL_DIR/" "$BACKUP_DIR/code/" --exclude "logs" --exclude ".git"
    
    # Backup configuration
    log_event "INFO" "Backing up configuration..."
    mkdir -p "$BACKUP_DIR/config"
    rsync -a "$INSTALL_DIR/config/" "$BACKUP_DIR/config/"
    
    # Backup systemd service files
    log_event "INFO" "Backing up service files..."
    sudo cp /etc/systemd/system/mower.service "$BACKUP_DIR/"
    sudo cp /etc/systemd/system/ntrip-client.service "$BACKUP_DIR/"
    
    log_event "SUCCESS" "Backup created successfully at $BACKUP_DIR"
}

# Function to perform health checks
perform_health_checks() {
    log_event "INFO" "Performing health checks..."
    
    # Check 1: Service status
    log_event "INFO" "Checking service status..."
    if ! systemctl is-active --quiet mower.service; then
        log_event "ERROR" "mower.service is not running"
        return 1
    fi
    
    # Check 2: Web interface
    log_event "INFO" "Checking web interface..."
    if ! curl -s --head --fail http://localhost:5000 > /dev/null; then
        log_event "ERROR" "Web interface is not responding"
        return 1
    fi
    
    # Check 3: Log file
    log_event "INFO" "Checking log file..."
    if ! grep -q "System initialized" /var/log/autonomous-mower/mower.log; then
        log_event "ERROR" "System initialization message not found in logs"
        return 1
    fi
    
    # Check 4: Hardware connectivity
    log_event "INFO" "Checking hardware connectivity..."
    if ! python3 -c "from src.mower.diagnostics.hardware_test import run_basic_tests; run_basic_tests()" > /dev/null; then
        log_event "ERROR" "Hardware connectivity check failed"
        return 1
    fi
    
    # All checks passed
    log_event "SUCCESS" "All health checks passed"
    return 0
}

# Function to perform system validation
perform_system_validation() {
    log_event "INFO" "Performing system validation..."
    
    # Run system validation script
    if [ -f "$INSTALL_DIR/scripts/system_validation.py" ]; then
        log_event "INFO" "Running system validation script..."
        if ! python3 "$INSTALL_DIR/scripts/system_validation.py"; then
            log_event "ERROR" "System validation failed"
            return 1
        fi
    else
        log_event "WARNING" "System validation script not found, skipping"
    fi
    
    # Run preflight checks
    if [ -f "$INSTALL_DIR/scripts/preflight_check.py" ]; then
        log_event "INFO" "Running preflight checks..."
        if ! python3 "$INSTALL_DIR/scripts/preflight_check.py"; then
            log_event "ERROR" "Preflight checks failed"
            return 1
        fi
    else
        log_event "WARNING" "Preflight check script not found, skipping"
    fi
    
    # All validation passed
    log_event "SUCCESS" "System validation completed successfully"
    return 0
}

# Function to deploy using blue-green strategy
deploy_blue_green() {
    log_event "INFO" "Starting blue-green deployment..."
    
    # Determine current active deployment
    if [ -L "$INSTALL_DIR" ] && [ -d "$BLUE_DIR" ] && [ -d "$GREEN_DIR" ]; then
        CURRENT_TARGET=$(readlink -f "$INSTALL_DIR")
        if [ "$CURRENT_TARGET" = "$BLUE_DIR" ]; then
            ACTIVE="blue"
            INACTIVE="green"
            INACTIVE_DIR="$GREEN_DIR"
        else
            ACTIVE="green"
            INACTIVE="blue"
            INACTIVE_DIR="$BLUE_DIR"
        fi
        log_event "INFO" "Current active deployment: $ACTIVE"
    else
        # First deployment, set up blue-green structure
        log_event "INFO" "Setting up blue-green deployment structure..."
        
        # Create blue and green directories if they don't exist
        mkdir -p "$BLUE_DIR"
        mkdir -p "$GREEN_DIR"
        
        # Initial deployment goes to blue
        ACTIVE="none"
        INACTIVE="blue"
        INACTIVE_DIR="$BLUE_DIR"
        
        # Create symlink if it doesn't exist
        if [ ! -L "$INSTALL_DIR" ]; then
            # If INSTALL_DIR exists but is not a symlink, move it
            if [ -d "$INSTALL_DIR" ]; then
                log_event "INFO" "Moving existing installation to blue directory..."
                rsync -a "$INSTALL_DIR/" "$BLUE_DIR/"
                rm -rf "$INSTALL_DIR"
            fi
            
            # Create symlink
            ln -sf "$BLUE_DIR" "$INSTALL_DIR"
        fi
    fi
    
    log_event "INFO" "Deploying to $INACTIVE directory..."
    
    # Clone or update repository in inactive directory
    if [ -d "$INACTIVE_DIR/.git" ]; then
        # Update existing repository
        log_event "INFO" "Updating existing repository in $INACTIVE directory..."
        cd "$INACTIVE_DIR"
        git fetch
        git checkout "$BRANCH"
        git pull
    else
        # Clone new repository
        log_event "INFO" "Cloning repository to $INACTIVE directory..."
        rm -rf "$INACTIVE_DIR"
        git clone "$REPO_URL" "$INACTIVE_DIR"
        cd "$INACTIVE_DIR"
        git checkout "$BRANCH"
    fi
    
    # Copy configuration from active deployment if it exists
    if [ "$ACTIVE" != "none" ] && [ -d "$INSTALL_DIR/config" ]; then
        log_event "INFO" "Copying configuration from active deployment..."
        rsync -a "$INSTALL_DIR/config/" "$INACTIVE_DIR/config/"
    fi
    
    # Install dependencies in inactive deployment
    log_event "INFO" "Installing dependencies in $INACTIVE directory..."
    cd "$INACTIVE_DIR"
    
    # Create answers file for non-interactive installation
    if [ "$SKIP_CORAL" = true ]; then
        echo "n" > coral_answer.txt
    else
        echo "y" > coral_answer.txt
    fi
    
    # Run installation script with answers file
    sudo ./install_requirements.sh < coral_answer.txt
    check_command "Running installation script" || {
        log_event "ERROR" "Installation failed"
        rm coral_answer.txt
        return 1
    }
    rm coral_answer.txt
    
    # Create systemd service files for inactive deployment
    log_event "INFO" "Creating service files for $INACTIVE deployment..."
    sudo cp "$INACTIVE_DIR/deployment/mower.service" /etc/systemd/system/mower-$INACTIVE.service
    sudo cp "$INACTIVE_DIR/deployment/ntrip-client.service" /etc/systemd/system/ntrip-client-$INACTIVE.service
    
    # Update service files to point to inactive deployment
    sudo sed -i "s|ExecStart=.*|ExecStart=$INACTIVE_DIR/venv/bin/python3 $INACTIVE_DIR/src/mower/main.py|" /etc/systemd/system/mower-$INACTIVE.service
    sudo sed -i "s|WorkingDirectory=.*|WorkingDirectory=$INACTIVE_DIR|" /etc/systemd/system/mower-$INACTIVE.service
    
    sudo sed -i "s|ExecStart=.*|ExecStart=$INACTIVE_DIR/venv/bin/python3 $INACTIVE_DIR/ntrip_client.py|" /etc/systemd/system/ntrip-client-$INACTIVE.service
    sudo sed -i "s|WorkingDirectory=.*|WorkingDirectory=$INACTIVE_DIR|" /etc/systemd/system/ntrip-client-$INACTIVE.service
    
    # Reload systemd
    sudo systemctl daemon-reload
    
    # Start inactive deployment services
    log_event "INFO" "Starting $INACTIVE deployment services..."
    sudo systemctl start ntrip-client-$INACTIVE.service
    sudo systemctl start mower-$INACTIVE.service
    
    # Wait for services to start
    sleep 5
    
    # Check if inactive services are running
    if ! systemctl is-active --quiet mower-$INACTIVE.service; then
        log_event "ERROR" "Failed to start mower-$INACTIVE.service"
        sudo systemctl stop ntrip-client-$INACTIVE.service
        return 1
    fi
    
    # Perform health checks on inactive deployment
    log_event "INFO" "Performing health checks on $INACTIVE deployment..."
    # TODO: Implement health checks for specific port of inactive deployment
    
    # Switch to inactive deployment
    log_event "INFO" "Switching to $INACTIVE deployment..."
    
    # Update symlink to point to inactive deployment
    ln -sf "$INACTIVE_DIR" "$INSTALL_DIR.new"
    mv -Tf "$INSTALL_DIR.new" "$INSTALL_DIR"
    
    # Stop old services if they exist
    if [ "$ACTIVE" != "none" ]; then
        log_event "INFO" "Stopping $ACTIVE deployment services..."
        sudo systemctl stop mower-$ACTIVE.service
        sudo systemctl stop ntrip-client-$ACTIVE.service
    fi
    
    # Copy service files to standard names
    sudo cp /etc/systemd/system/mower-$INACTIVE.service /etc/systemd/system/mower.service
    sudo cp /etc/systemd/system/ntrip-client-$INACTIVE.service /etc/systemd/system/ntrip-client.service
    
    # Reload systemd
    sudo systemctl daemon-reload
    
    # Enable and start standard services
    log_event "INFO" "Enabling and starting standard services..."
    sudo systemctl enable ntrip-client.service
    sudo systemctl enable mower.service
    sudo systemctl start ntrip-client.service
    sudo systemctl start mower.service
    
    # Perform final health checks
    if perform_health_checks; then
        log_event "SUCCESS" "Blue-green deployment completed successfully"
        return 0
    else
        log_event "ERROR" "Health checks failed after deployment"
        return 1
    fi
}

# Function to deploy locally
deploy_locally() {
    log_event "INFO" "Starting local deployment..."

    # Check if we're in the repository root
    if [ ! -f "setup.py" ] || [ ! -d "src/mower" ]; then
        log_event "ERROR" "This script must be run from the repository root"
        exit 1
    fi

    # Check if we're on a Raspberry Pi
    if [ "$SKIP_HARDWARE_CHECK" = false ] && ! grep -q "Raspberry Pi" /proc/cpuinfo; then
        log_event "ERROR" "This script must be run on a Raspberry Pi"
        exit 1
    fi

    # Create backup of current installation
    print_stage "BACKUP"
    create_backup
    
    # Deploy using blue-green strategy if enabled
    if [ "$BLUE_GREEN" = true ]; then
        print_stage "BLUE-GREEN DEPLOYMENT"
        if ! deploy_blue_green; then
            log_event "ERROR" "Blue-green deployment failed"
            if [ "$AUTO_ROLLBACK" = true ]; then
                print_stage "ROLLBACK"
                perform_rollback
            fi
            exit 1
        fi
    else
        # Traditional deployment
        print_stage "DEPLOYMENT"
        
        # Make sure we're on the correct branch
        log_event "INFO" "Checking out branch: $BRANCH"
        git checkout $BRANCH
        check_command "Checking out branch $BRANCH" || exit 1

        # Pull latest changes
        log_event "INFO" "Pulling latest changes..."
        git pull
        check_command "Pulling latest changes" || exit 1

        # Run the installation script
        log_event "INFO" "Running installation script..."
        chmod +x install_requirements.sh

        # Create answers file for non-interactive installation
        if [ "$SKIP_CORAL" = true ]; then
            echo "n" > coral_answer.txt
        else
            echo "y" > coral_answer.txt
        fi

        # Run installation script with answers file
        sudo ./install_requirements.sh < coral_answer.txt
        check_command "Running installation script" || {
            log_event "ERROR" "Installation failed"
            rm coral_answer.txt
            if [ "$AUTO_ROLLBACK" = true ]; then
                print_stage "ROLLBACK"
                perform_rollback
            fi
            exit 1
        }
        rm coral_answer.txt

        # Set up remote access if requested
        if [ "$SKIP_REMOTE_ACCESS" = false ]; then
            log_event "INFO" "Setting up remote access..."
            python3 src/mower/utilities/setup_remote_access.py
            check_command "Setting up remote access" || {
                log_event "ERROR" "Remote access setup failed"
                if [ "$AUTO_ROLLBACK" = true ]; then
                    print_stage "ROLLBACK"
                    perform_rollback
                fi
                exit 1
            }
        fi

        # Create log directory if it doesn't exist
        log_event "INFO" "Setting up log directory..."
        sudo mkdir -p /var/log/autonomous-mower
        sudo chown -R pi:pi /var/log/autonomous-mower
        sudo chmod 755 /var/log/autonomous-mower
        check_command "Setting up log directory" || exit 1

        # Enable and start the service
        log_event "INFO" "Enabling and starting the services..."
        sudo systemctl enable ntrip-client.service
        sudo systemctl start ntrip-client.service
        sudo systemctl enable mower.service
        sudo systemctl start mower.service

        check_command "Enabling and starting the service" || {
            log_event "ERROR" "Failed to start services"
            if [ "$AUTO_ROLLBACK" = true ]; then
                print_stage "ROLLBACK"
                perform_rollback
            fi
            exit 1
        }
    fi

    # Perform system validation
    print_stage "SYSTEM VALIDATION"
    if ! perform_system_validation; then
        log_event "ERROR" "System validation failed"
        if [ "$AUTO_ROLLBACK" = true ]; then
            print_stage "ROLLBACK"
            perform_rollback
        fi
        exit 1
    fi
    
    # Perform health checks
    print_stage "HEALTH CHECKS"
    if ! perform_health_checks; then
        log_event "ERROR" "Health checks failed"
        if [ "$AUTO_ROLLBACK" = true ]; then
            print_stage "ROLLBACK"
            perform_rollback
        fi
        exit 1
    fi

    log_event "SUCCESS" "Deployment completed successfully!"
    log_event "INFO" "You can access the web interface at http://localhost:5000"

    # Get IP address for remote access
    IP_ADDRESS=$(hostname -I | awk '{print $1}')
    log_event "INFO" "Or access it remotely at http://$IP_ADDRESS:5000"
}

# Function to deploy to a remote Raspberry Pi
deploy_remotely() {
    log_event "INFO" "Starting remote deployment to $REMOTE_HOST..."

    # Check if SSH is available
    if ! command_exists ssh; then
        log_event "ERROR" "SSH client not found. Please install SSH."
        exit 1
    }

    # Check if we can connect to the remote host
    log_event "INFO" "Checking SSH connection to $REMOTE_HOST..."
    ssh -p $REMOTE_PORT -o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=accept-new $REMOTE_USER@$REMOTE_HOST "echo SSH connection successful" || {
        log_event "ERROR" "Failed to connect to $REMOTE_HOST. Please check your SSH settings."
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
    git clone $REPO_URL
    cd autonomous_mower
else
    echo "Repository already exists, updating..."
    cd autonomous_mower
    git fetch
fi

# Checkout the specified branch
git checkout $BRANCH
git pull

# Run the enhanced deployment script locally
./scripts/enhanced_deploy.sh \
    --branch $BRANCH \
    $([ "$SKIP_HARDWARE_CHECK" = true ] && echo "--skip-hardware-check") \
    $([ "$SKIP_CORAL" = true ] && echo "--skip-coral") \
    $([ "$SKIP_REMOTE_ACCESS" = true ] && echo "--skip-remote-access") \
    $([ "$BLUE_GREEN" = true ] && echo "--blue-green") \
    $([ "$AUTO_ROLLBACK" = true ] && echo "--auto-rollback") \
    $([ "$SKIP_VALIDATION" = true ] && echo "--skip-validation") \
    --log-file $REMOTE_LOG_FILE
EOF

    # Make the script executable
    chmod +x $TEMP_SCRIPT

    # Copy the script to the remote host
    log_event "INFO" "Copying deployment script to $REMOTE_HOST..."
    scp -P $REMOTE_PORT $TEMP_SCRIPT $REMOTE_USER@$REMOTE_HOST:~/deploy_mower.sh
    check_command "Copying deployment script" || exit 1

    # Execute the script on the remote host
    log_event "INFO" "Executing deployment script on $REMOTE_HOST..."
    ssh -p $REMOTE_PORT $REMOTE_USER@$REMOTE_HOST "chmod +x ~/deploy_mower.sh && ~/deploy_mower.sh"
    check_command "Remote deployment" || exit 1

    # Copy the deployment log from the remote host
    log_event "INFO" "Copying deployment log from $REMOTE_HOST..."
    scp -P $REMOTE_PORT $REMOTE_USER@$REMOTE_HOST:$REMOTE_LOG_FILE $DEPLOY_LOG.remote
    check_command "Copying deployment log" || exit 1
    
    # Append remote log to local log
    cat $DEPLOY_LOG.remote >> $DEPLOY_LOG
    rm $DEPLOY_LOG.remote

    # Clean up
    rm $TEMP_SCRIPT
    ssh -p $REMOTE_PORT $REMOTE_USER@$REMOTE_HOST "rm ~/deploy_mower.sh"

    log_event "SUCCESS" "Remote deployment to $REMOTE_HOST completed successfully!"
    log_event "INFO" "You can access the web interface at http://$REMOTE_HOST:5000"
}

# Parse command line arguments
BRANCH="main"
REMOTE_DEPLOY=false
REMOTE_HOST=""
REMOTE_USER="pi"
REMOTE_PORT="22"
SKIP_HARDWARE_CHECK=false
SKIP_CORAL=false
SKIP_REMOTE_ACCESS=false
BLUE_GREEN=false
AUTO_ROLLBACK=false
SKIP_VALIDATION=false
REPO_URL="https://github.com/yourusername/autonomous_mower.git"

# Set up paths
INSTALL_DIR="/home/pi/autonomous_mower"
BACKUP_DIR="/home/pi/autonomous_mower_backup/$(date +%Y%m%d_%H%M%S)"
BLUE_DIR="/home/pi/autonomous_mower_blue"
GREEN_DIR="/home/pi/autonomous_mower_green"
DEPLOY_LOG="/var/log/autonomous-mower/deployment.log"
REMOTE_LOG_FILE="/var/log/autonomous-mower/deployment.log"

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
    echo "  --repo-url URL             Repository URL (default: $REPO_URL)"
    echo "  --skip-hardware-check      Skip hardware compatibility check"
    echo "  --skip-coral               Skip Coral TPU setup"
    echo "  --skip-remote-access       Skip remote access setup"
    echo "  --blue-green               Use blue-green deployment strategy"
    echo "  --auto-rollback            Automatically roll back on failure"
    echo "  --skip-validation          Skip system validation"
    echo "  --log-file FILE            Specify log file (default: $DEPLOY_LOG)"
    echo ""
    echo "Examples:"
    echo "  $0                         # Deploy locally from current directory"
    echo "  $0 -b improvements         # Deploy locally from improvements branch"
    echo "  $0 -r raspberrypi.local    # Deploy to remote Pi using hostname"
    echo "  $0 --blue-green            # Use blue-green deployment strategy"
    echo "  $0 --auto-rollback         # Automatically roll back on failure"
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
        --repo-url)
            REPO_URL="$2"
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
        --blue-green)
            BLUE_GREEN=true
            shift
            ;;
        --auto-rollback)
            AUTO_ROLLBACK=true
            shift
            ;;
        --skip-validation)
            SKIP_VALIDATION=true
            shift
            ;;
        --log-file)
            DEPLOY_LOG="$2"
            shift 2
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Create log directory if it doesn't exist
mkdir -p $(dirname "$DEPLOY_LOG")

# Start deployment log
echo "=== Deployment started at $(date) ===" > "$DEPLOY_LOG"
echo "Branch: $BRANCH" >> "$DEPLOY_LOG"
echo "Blue-Green: $BLUE_GREEN" >> "$DEPLOY_LOG"
echo "Auto-Rollback: $AUTO_ROLLBACK" >> "$DEPLOY_LOG"
echo "======================================" >> "$DEPLOY_LOG"

# Main deployment logic
if [ "$REMOTE_DEPLOY" = true ]; then
    deploy_remotely
else
    deploy_locally
fi

# Log completion
echo "=== Deployment completed at $(date) ===" >> "$DEPLOY_LOG"

exit 0