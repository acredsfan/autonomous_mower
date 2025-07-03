## Deploying the Mower Service

To deploy the autonomous mower as a systemd service, follow these steps:

1.  **Copy the service file:**

    ```bash
    sudo cp deployment/mower.service /etc/systemd/system/
    ```

2.  **Reload the systemd daemon:**

    This command reloads the systemd manager configuration, making it aware of the new `mower.service` file.

    ```bash
    sudo systemctl daemon-reload
    ```

3.  **Enable the service:**

    This command enables the service to start automatically on boot.

    ```bash
    sudo systemctl enable mower.service
    ```

4.  **Start or restart the service:**

    To start the service for the first time or to apply changes, use the restart command.

    ```bash
    sudo systemctl restart mower.service
    ```

5.  **Verify the service status:**

    Check the status of the service to ensure it is running correctly. Use a timeout to prevent the command from hanging.

    ```bash
    timeout 10 systemctl status mower.service
    ```

    To check if the service is active without all the details:

    ```bash
    systemctl is-active mower.service
    ```
