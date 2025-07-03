# Systemd Service Troubleshooting

## ⚠️ IMPORTANT: Log Viewing Protocol

**NEVER use `journalctl` directly** - use the project's log copy script instead:

```bash
# ✅ CORRECT way to view logs
python3 /home/pi/autonomous_mower/copy_logs.py
cat copied_jctl_output.log | tail -100
cat copied_mower.log | tail -100

# ❌ FORBIDDEN - will hang terminal
journalctl -u mower.service -f
journalctl -u mower.service
```

## Common Issues and Solutions

### Service Stuck in StartLimitHit State

**Symptoms:**
- Service fails to start with "Start request repeated too quickly"
- `systemctl status mower` shows "start-limit-hit"

**Solution:**
```bash
# Reset the start limit
sudo systemctl reset-failed mower.service

# Check service status (use timeout)
timeout 10 systemctl status mower.service

# Restart service
sudo systemctl start mower.service

# Wait and verify (with timeout)
sleep 30
timeout 5 systemctl is-active mower.service
```

### Endless Restart Loop

**Prevention:** 
The service is configured with restart backoff:
- `RestartSec=15` - Wait 15 seconds between restarts
- `StartLimitInterval=5m` - 5-minute window for burst limit
- `StartLimitBurst=5` - Maximum 5 restarts in the interval

**Troubleshooting:**
```bash
# Check recent logs safely
python3 /home/pi/autonomous_mower/copy_logs.py
tail -50 copied_jctl_output.log

# Check for specific errors
grep -E "(ERROR|CRITICAL|Failed)" copied_jctl_output.log | tail -20

# Check mower-specific logs
tail -50 copied_mower.log
grep -E "(ERROR|CRITICAL)" copied_mower.log | tail -10
```

### Configuration Validation

**Check unit file settings:**
```bash
# Validate restart configuration (with timeout)
timeout 30 python3 /home/pi/autonomous_mower/scripts/check_unit_file.py

# View current configuration
timeout 10 systemctl cat mower.service
```

### Service Status Monitoring

**Safe status checking with timeouts:**
```bash
# Quick status check
timeout 5 systemctl is-active mower.service

# Detailed status (limited output)
timeout 10 systemctl status mower.service --no-pager -l

# Check if service is enabled
timeout 5 systemctl is-enabled mower.service
```

## Best Practices

1. **Always use timeouts** for systemctl commands
2. **Use copy_logs.py** instead of journalctl directly
3. **Check logs first** before restarting services
4. **Use reset-failed** before restarting stuck services
5. **Monitor startup time** - should complete within 60 seconds
6. **Check hardware connections** if service fails repeatedly
7. **Verify .env file** configuration before service start

## Emergency Procedures

### Safe Mode Startup
If hardware failures prevent normal startup:
```bash
# Enable safe mode
echo "SAFE_MODE_ALLOWED=true" >> /home/pi/autonomous_mower/.env

# Restart service
sudo systemctl restart mower.service

# Wait for startup (with timeout)
sleep 30
timeout 5 systemctl is-active mower.service

# Check web interface at http://[pi-ip]:8000
```

### Complete Service Reset
```bash
# Stop service (with timeout)
timeout 30 sudo systemctl stop mower.service

# Reset any failed states
sudo systemctl reset-failed mower.service

# Reload systemd configuration
sudo systemctl daemon-reload

# Start service
sudo systemctl start mower.service

# Wait and verify (with timeout)
sleep 30
timeout 5 systemctl is-active mower.service

# Enable for auto-start
sudo systemctl enable mower.service
```

### Log Analysis Commands

**Safe log analysis (always use these instead of journalctl):**
```bash
# Copy current logs
python3 /home/pi/autonomous_mower/copy_logs.py

# Recent errors
grep -E "(ERROR|CRITICAL|Failed)" copied_jctl_output.log | tail -20

# Service startup sequence
grep -A 5 -B 5 "Starting Autonomous Mower Service" copied_jctl_output.log

# Hardware initialization
grep -i "hardware\|sensor\|i2c\|gpio" copied_mower.log | tail -20

# Check for memory/resource issues
grep -E "(memory|timeout|resource)" copied_jctl_output.log | tail -10

# Web interface status
grep -i "web\|flask\|port.*8000" copied_mower.log | tail -10
```

## Timeout Recommendations

All operations should include appropriate timeouts:

- **systemctl commands**: 5-30 seconds
- **Service status checks**: 5 seconds  
- **Log copying**: 60 seconds
- **Service restart waiting**: 30-60 seconds
- **Process monitoring**: 120 seconds maximum

## Contact and Escalation

If issues persist after following this guide:
1. Copy all logs: `python3 copy_logs.py`
2. Save configuration: `systemctl cat mower.service > mower_config.txt`
3. Document exact error messages and steps taken
4. Include hardware setup details and recent changes
