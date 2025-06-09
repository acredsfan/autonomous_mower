#!/bin/bash

# Helper script to restart the autonomous-mower service
# and monitor the logs

echo "Stopping autonomous-mower service..."
sudo systemctl stop autonomous-mower

echo "Waiting 5 seconds for clean shutdown..."
sleep 5

# Optional: Reset I2C bus if needed 
# This is commented out by default as it may affect other I2C devices
# echo "Resetting I2C bus..."
# sudo rmmod i2c_bcm2835
# sudo modprobe i2c_bcm2835

echo "Starting autonomous-mower service..."
sudo systemctl start autonomous-mower

echo "Service status:"
sudo systemctl status autonomous-mower

echo "Showing logs (press Ctrl+C to exit):"
sudo journalctl -u autonomous-mower -f
