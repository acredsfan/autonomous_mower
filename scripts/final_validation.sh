#!/bin/bash

# Final Validation Script
# This script performs a comprehensive validation of the autonomous mower system
# after deployment, ensuring all components work together correctly.

# Exit on error
set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# Function to run a test and report result
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    print_info "Running test: $test_name"
    
    if eval "$test_command"; then
        print_success "Test passed: $test_name"
        return 0
    else
        print_error "Test failed: $test_name"
        return 1
    fi
}

# Parse command line arguments
VERBOSE=false
SKIP_HARDWARE=false
SKIP_SERVICES=false
OUTPUT_FILE=""

# Display help message
show_help() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -h, --help             Show this help message"
    echo "  -v, --verbose          Show detailed output"
    echo "  --skip-hardware        Skip hardware tests"
    echo "  --skip-services        Skip service tests"
    echo "  -o, --output FILE      Save results to file"
    echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --skip-hardware)
            SKIP_HARDWARE=true
            shift
            ;;
        --skip-services)
            SKIP_SERVICES=true
            shift
            ;;
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Initialize results array
declare -A TEST_RESULTS

# Check if we're running on a Raspberry Pi
if [ "$SKIP_HARDWARE" = false ] && ! grep -q "Raspberry Pi" /proc/cpuinfo; then
    print_warning "This script should be run on a Raspberry Pi. Hardware tests will be skipped."
    SKIP_HARDWARE=true
fi

# Check if we're in the repository root
if [ ! -f "setup.py" ] || [ ! -d "src/mower" ]; then
    print_error "This script must be run from the repository root"
    exit 1
fi

# Create output directory if it doesn't exist
if [ -n "$OUTPUT_FILE" ]; then
    mkdir -p "$(dirname "$OUTPUT_FILE")"
fi

# Start validation
print_info "Starting final validation..."

# 1. System validation
print_info "Running system validation..."
if run_test "System validation" "python3 scripts/system_validation.py --verbose"; then
    TEST_RESULTS["system_validation"]="PASS"
else
    TEST_RESULTS["system_validation"]="FAIL"
fi

# 2. Preflight checks
print_info "Running preflight checks..."
if run_test "Preflight checks" "python3 scripts/preflight_check.py --verbose"; then
    TEST_RESULTS["preflight_checks"]="PASS"
else
    TEST_RESULTS["preflight_checks"]="FAIL"
fi

# 3. Service checks
if [ "$SKIP_SERVICES" = false ]; then
    print_info "Checking services..."
    
    # Check mower service
    if run_test "Mower service" "systemctl is-active --quiet mower.service"; then
        TEST_RESULTS["mower_service"]="PASS"
    else
        TEST_RESULTS["mower_service"]="FAIL"
    fi
    
    # Check NTRIP client service
    if run_test "NTRIP client service" "systemctl is-active --quiet ntrip-client.service"; then
        TEST_RESULTS["ntrip_service"]="PASS"
    else
        TEST_RESULTS["ntrip_service"]="FAIL"
    fi
fi

# 4. Hardware checks
if [ "$SKIP_HARDWARE" = false ]; then
    print_info "Running hardware tests..."
    
    # Check I2C devices
    if run_test "I2C devices" "i2cdetect -y 1 | grep -E '40|68|29'"; then
        TEST_RESULTS["i2c_devices"]="PASS"
    else
        TEST_RESULTS["i2c_devices"]="FAIL"
    fi
    
    # Check camera
    if run_test "Camera" "vcgencmd get_camera | grep 'detected=1'"; then
        TEST_RESULTS["camera"]="PASS"
    else
        TEST_RESULTS["camera"]="FAIL"
    fi
    
    # Check GPIO
    if run_test "GPIO" "python3 -c 'import RPi.GPIO as GPIO; print(\"GPIO available\")'"; then
        TEST_RESULTS["gpio"]="PASS"
    else
        TEST_RESULTS["gpio"]="FAIL"
    fi
    
    # Run sensor tests
    if run_test "Sensors" "python3 tools/test_sensors.py --quick"; then
        TEST_RESULTS["sensors"]="PASS"
    else
        TEST_RESULTS["sensors"]="FAIL"
    fi
fi

# 5. Web interface check
print_info "Checking web interface..."
if run_test "Web interface" "curl -s --head --fail http://localhost:5000 > /dev/null"; then
    TEST_RESULTS["web_interface"]="PASS"
else
    TEST_RESULTS["web_interface"]="FAIL"
fi

# 6. Log file check
print_info "Checking log files..."
if run_test "Log files" "test -f /var/log/autonomous-mower/mower.log"; then
    TEST_RESULTS["log_files"]="PASS"
else
    TEST_RESULTS["log_files"]="FAIL"
fi

# 7. Configuration check
print_info "Checking configuration files..."
if run_test "Configuration" "test -f config/main_config.json && python3 -c 'import json; json.load(open(\"config/main_config.json\"))'"; then
    TEST_RESULTS["configuration"]="PASS"
else
    TEST_RESULTS["configuration"]="FAIL"
fi

# 8. ML model check
print_info "Checking ML models..."
if run_test "ML models" "test -f models/coral_model_quantized_int8.tflite && test -f models/labels.txt"; then
    TEST_RESULTS["ml_models"]="PASS"
else
    TEST_RESULTS["ml_models"]="FAIL"
fi

# Print summary
print_info "Validation complete. Summary:"
echo ""
echo "========================================"
echo "FINAL VALIDATION RESULTS"
echo "========================================"
echo ""

PASS_COUNT=0
FAIL_COUNT=0

for test in "${!TEST_RESULTS[@]}"; do
    result=${TEST_RESULTS[$test]}
    if [ "$result" = "PASS" ]; then
        echo -e "${GREEN}✓ $test: $result${NC}"
        ((PASS_COUNT++))
    else
        echo -e "${RED}✗ $test: $result${NC}"
        ((FAIL_COUNT++))
    fi
done

echo ""
echo "========================================"
echo -e "${BLUE}Tests passed: $PASS_COUNT${NC}"
echo -e "${RED}Tests failed: $FAIL_COUNT${NC}"
echo "========================================"

# Save results to file if specified
if [ -n "$OUTPUT_FILE" ]; then
    print_info "Saving results to $OUTPUT_FILE..."
    
    echo "FINAL VALIDATION RESULTS" > "$OUTPUT_FILE"
    echo "Date: $(date)" >> "$OUTPUT_FILE"
    echo "=======================================" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    
    for test in "${!TEST_RESULTS[@]}"; do
        echo "$test: ${TEST_RESULTS[$test]}" >> "$OUTPUT_FILE"
    done
    
    echo "" >> "$OUTPUT_FILE"
    echo "Tests passed: $PASS_COUNT" >> "$OUTPUT_FILE"
    echo "Tests failed: $FAIL_COUNT" >> "$OUTPUT_FILE"
    
    print_success "Results saved to $OUTPUT_FILE"
fi

# Exit with status code based on test results
if [ $FAIL_COUNT -eq 0 ]; then
    print_success "All validation tests passed!"
    exit 0
else
    print_error "$FAIL_COUNT validation tests failed!"
    exit 1
fi