# Environment Variable Setup for Mower Application

The mower application uses a `.env` file to manage various configuration settings. This file allows you to customize parameters without modifying the core application code. The settings are loaded by the application at runtime.

## Creating Your `.env` File

The project includes a template file named `.env.example`. You need to create a copy of this file and name it `.env`. This new `.env` file is where you'll set your specific configurations. It's intentionally not committed to version control to keep your sensitive information (like API keys or specific hardware settings) private.

To create your `.env` file, navigate to the root directory of the project in your terminal and run:
```bash
cp .env.example .env
```
Now, you can open the `.env` file with a text editor to modify its values.

## Critical Environment Variables for Hardware Interaction

The following environment variables are essential for the `main_controller.py` to interact correctly with the Raspberry Pi hardware and for the basic operation of the mower. Ensure these are configured accurately for your setup.

### 1. RoboHAT MM1 Motor Controller
*   `MM1_SERIAL_PORT`
    *   **Purpose**: Specifies the serial port connected to the RoboHAT MM1 motor controller.
    *   **Default in `.env.example`**: `/dev/ttyACM0` (This is a common port for USB serial devices. If your RoboHAT is connected via USB or appears as such, this might be correct).
    *   **Guidance**:
        *   The RoboHAT MM1 might also be on `/dev/ttyS0` or `/dev/ttyAMA0` depending on your Raspberry Pi model and how the HAT is interfaced (directly on GPIO vs. via an adapter).
        *   **Crucially, ensure this port is not being used by another service (like the serial console or Bluetooth).**
        *   Verify available serial ports by listing devices: `ls /dev/tty*`. Common ports include `/dev/ttyS0` (mini UART, often default console/Bluetooth), `/dev/ttyAMA0` (primary UART), and `/dev/ttyACMx` or `/dev/ttyUSBx` for USB-connected serial devices.
        *   Refer to the Raspberry Pi Configuration Guide and the RoboHAT MM1 specific guide for more details on serial port management.

### 2. GPS Module
*   `GPS_SERIAL_PORT`
    *   **Purpose**: Defines the serial port to which your GPS module is connected.
    *   **Default in `.env.example`**: `/dev/ttyACM1`
    *   **Guidance**: Similar to the RoboHAT, your GPS might be on `/dev/ttyS0`, `/dev/ttyAMA0`, `/dev/ttyACM0`, `/dev/ttyUSB0`, etc. Ensure it's the correct, available port.
*   `GPS_BAUD_RATE`
    *   **Purpose**: Sets the baud rate for communication with the GPS module.
    *   **Default in `.env.example`**: `115200`
    *   **Guidance**: Common baud rates for GPS modules are 9600, 38400, 57600, or 115200. This must match the configuration of your GPS module.

### 3. IMU (e.g., BNO085)
*   `IMU_SERIAL_PORT`
    *   **Purpose**: Specifies the serial port for the IMU if it uses a serial connection (some BNO085 variants do). If your IMU uses I2C, this variable might be ignored or set differently.
    *   **Default in `.env.example`**: `/dev/ttyAMA2`
    *   **Guidance**: If your BNO085 or other IMU connects via serial, ensure this points to the correct port. Note that `/dev/ttyAMA2` might not be available on all Raspberry Pi models or may require specific configuration. If your IMU is I2C, this setting might not be directly used for the primary IMU communication. Always check your IMU's documentation.
*   `IMU_BAUD_RATE`
    *   **Purpose**: Sets the baud rate for the serial IMU.
    *   **Default in `.env.example`**: `3000000`
    *   **Guidance**: This is a very high baud rate. Ensure your IMU and Raspberry Pi support it and are configured for it if using a serial IMU.

### 4. Camera Configuration
*   `USE_CAMERA`
    *   **Purpose**: Master switch to enable or disable camera functionality.
    *   **Default in `.env.example`**: `True`
    *   **Guidance**: Set to `True` to use the camera, `False` to disable.
*   `CAMERA_INDEX`
    *   **Purpose**: The index of the camera to be used by the system (e.g., OpenCV).
    *   **Default in `.env.example`**: `0`
    *   **Guidance**: `0` is typically the default built-in camera (e.g., Raspberry Pi camera module if configured as video0). If you have multiple cameras, you might need to change this to `1`, `2`, etc. Use tools like `ls /dev/video*` to see available camera devices.
*   `STREAMING_FPS`
    *   **Purpose**: Sets the desired frames per second for the camera video stream.
    *   **Default in `.env.example`**: `30`
    *   **Guidance**: Higher FPS provides smoother video but uses more processing power.
*   `STREAMING_RESOLUTION`
    *   **Purpose**: Defines the resolution (widthxheight) for the video stream.
    *   **Default in `.env.example`**: `640x480`
    *   **Guidance**: Higher resolution provides more detail but requires more bandwidth and processing.
*   `FRAME_BUFFER_SIZE`
    *   **Purpose**: Size of the frame buffer for video streaming.
    *   **Default in `.env.example`**: `5`
    *   **Guidance**: Affects the smoothness and latency of the stream.

### 5. Operational Mode
*   `USE_SIMULATION`
    *   **Purpose**: Determines if the application runs in simulation mode or with actual hardware.
    *   **Default in `.env.example`**: `False`
    *   **Guidance**: For operating the physical mower with Raspberry Pi hardware, this **must be set to `False`**. Setting it to `True` will bypass hardware interactions.

### 6. Logging and UI
*   `LOG_LEVEL`
    *   **Purpose**: Controls the verbosity of application logging.
    *   **Default in `.env.example`**: `INFO`
    *   **Guidance**: Common values:
        *   `DEBUG`: Very detailed logs, useful for troubleshooting.
        *   `INFO`: Standard operational messages.
        *   `WARNING`: Only warnings and errors.
        *   `ERROR`: Only error messages.
*   `ENABLE_WEB_UI`
    *   **Purpose**: Enables or disables the web-based user interface.
    *   **Default in `.env.example`**: `True`
    *   **Guidance**: Set to `True` to access the web UI, `False` to disable it.

## General Advice

The `.env.example` file contains many other variables that control various aspects of the mower application, such as API keys for Google Maps, NTRIP configuration for RTK GPS, machine learning model paths, and safety parameters.

Once you have confirmed that the critical hardware components are working correctly with the settings above, take the time to review all other variables in your `.env` file and configure them according to your specific setup and requirements for full application functionality.

---

This document should provide a good overview for setting up the environment variables.
