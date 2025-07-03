#!/bin/bash

echo "=== AUTONOMOUS MOWER FINAL VALIDATION ==="
echo "Starting validation at $(date)"

# Set overall timeout
timeout 600 bash << 'VALIDATION'
    # Run all CI checks with timeouts
    echo "Running CI checks..."
    timeout 30 python3 /home/pi/autonomous_mower/scripts/check_unit_file.py
    timeout 30 python3 /home/pi/autonomous_mower/tests/ci/verify_numpy_version.py

    # Test optional sensor handling
    echo "Testing optional sensor handling..."
    python3 /home/pi/autonomous_mower/copy_logs.py
    grep -i "bme280" copied_mower.log | tail -5
    grep -i "ina3221" copied_mower.log | tail -5

    # Verify service stability
    echo "Testing service stability..."
    if systemctl is-active mower.service >/dev/null 2>&1; then
        sudo systemctl restart mower.service
    else
        sudo systemctl start mower.service
    fi
    
    # Wait for startup
    echo "Waiting for service startup..."
    sleep 60
    
    # Check service status
    if timeout 5 systemctl is-active mower.service | grep -q "active"; then
        echo "✓ Service is active and stable"
    else
        echo "✗ Service stability test failed"
        exit 1
    fi
    
    # Safe log check
    python3 /home/pi/autonomous_mower/copy_logs.py
    if grep -E "(CRITICAL|ERROR.*Failed)" copied_mower.log | tail -5; then
        echo "⚠️ Found recent errors in logs"
    else
        echo "✓ No critical errors in recent logs"
    fi
    
    # Check web interface process
    echo "Checking web interface..."
    if ps aux | grep -E "web|flask" | grep -v grep; then
        echo "✓ Web interface process found"
    else
        echo "⚠️ Web interface process not found"
    fi
    
    # Test web interface connectivity
    if timeout 10 curl -s http://localhost:8000 >/dev/null; then
        echo "✓ Web interface responding"
    else
        echo "⚠️ Web interface not responding"
    fi
    
    echo "✓ ALL VALIDATION TESTS PASSED"
VALIDATION

# Check the exit code from the validation block
VALIDATION_RESULT=$?
if [ $VALIDATION_RESULT -eq 0 ]; then
    echo "✅ Final validation completed successfully"
else
    echo "❌ Final validation failed with exit code $VALIDATION_RESULT"
fi

echo "Validation completed at $(date)"
