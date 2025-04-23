# Service Startup on Raspberry Pi

This guide describes how to install and manage the autonomous mower as a systemd service on Raspberry Pi.

## Service Unit Files

Two service unit files are provided in the repository's root:

- `autonomous-mower.service`: The main service that runs the mower.
- `install-mower.service`: A one-shot service for initial installation.

## Installation

1. Copy the main service unit to the systemd directory:

```sh
sudo cp autonomous-mower.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable autonomous-mower.service
```

2. Start the service:

```sh
sudo systemctl start autonomous-mower.service
```

3. Check service status:

```sh
sudo systemctl status autonomous-mower.service
```

## ResourceManager Initialization

When the service starts, it runs:

```sh
python3 -m mower.main_controller
```

This entrypoint calls `ResourceManager.initialize()` within the `main()` function, which:

- Initializes hardware resources (GPIO, I2C sensors, camera, etc.)
- Initializes software modules (navigation, web interface, localization, etc.)
- Starts the web server via the `start_web_interface` method
- Launches the robot control thread

On shutdown or failure, `ResourceManager.cleanup()` is invoked to release all hardware resources.

## Logs

- Service logs are sent to journald. View logs with:

```sh
sudo journalctl -u autonomous-mower.service -f
```
