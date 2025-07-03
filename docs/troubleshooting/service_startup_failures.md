# Troubleshooting: Service Startup Failures

This guide covers common issues and solutions when the systemd service fails to start on Raspberry Pi.

## Symptoms

- Service does not start or stops immediately (`systemctl status` shows errors)
- Python errors on ExecStartPre or ExecStart
- Mower does not respond after enabling service

## Possible Causes and Solutions

1. Working Directory Misconfiguration

   - Verify `WorkingDirectory` matches project path (see [`mower.service`:10](../mower.service:10))
   - Correct path in service file and reload systemd:
     ```bash
     sudo systemctl daemon-reload
     sudo systemctl restart mower.service
     ```

2. Environment Variables Not Loaded

   - Ensure required env variables are set in service file or use an EnvironmentFile
   - Example:
     ```ini
     EnvironmentFile=/home/pi/autonomous_mower/.env
     ```

3. Permission Issues

   - Confirm `User` and `Group` in service file (`pi:pi` by default)
   - Check file and directory permissions for access by the service user

4. Dependency Ordering

   - Ensure `After=` and `Wants=` directives include `network.target`, `dev-i2c-1.device`, etc.
   - Add any missing dependencies for hardware initialization

5. ExecStartPre Failures

   - If `ExecStartPre` hardware tests fail, service will not start
   - Review logs for test failures and fix hardware issues

6. Log Channel and Journal Access
   - View logs with:
     ```bash
     sudo journalctl -u mower.service -f
     ```
   - Look for stack traces and error messages for troubleshooting
