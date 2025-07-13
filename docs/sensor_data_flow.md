# Sensor Data Flow

This document outlines the data flow for the GPS, IMU, ToF, INA3221, and BME280 sensors in the autonomous mower project.

## Visual Representation

```mermaid
graph TD
    subgraph Hardware Layer
        GPS_HW[GPS Module]
        IMU_HW[IMU Sensor BNO085]
        ToF_HW[ToF Sensors VL53L0X]
        INA3221_HW[INA3221 Power Monitor]
        BME280_HW[BME280 Environment Sensor]
    end

    subgraph Hardware Abstraction Layer
        GPS[navigation/gps.py]
        IMU[hardware/imu.py]
        ToF[hardware/tof.py]
        INA3221[hardware/ina3221.py]
        BME280[hardware/bme280.py]
    end

    subgraph Sensor Interface
        SensorInterface[hardware/sensor_interface.py]
    end

    subgraph Main Controller
        MainController[main_controller.py]
    end

    subgraph Web UI
        WebUI[ui/web_ui/web_interface.py]
    end

    %% Hardware to HAL
    GPS_HW -->|Serial Data| GPS
    IMU_HW -->|Serial Data| IMU
    ToF_HW -->|I2C Data| ToF
    INA3221_HW -->|I2C Data| INA3221
    BME280_HW -->|I2C Data| BME280

    %% HAL to Sensor Interface
    GPS --> SensorInterface
    IMU --> SensorInterface
    ToF --> SensorInterface
    INA3221 --> SensorInterface
    BME280 --> SensorInterface

    %% Sensor Interface to Main Controller
    SensorInterface -->|get_sensor_data()| MainController

    %% Main Controller to Web UI
    MainController -->|sensor_data| WebUI
```

## Data Flow Explanation:

1.  **Hardware Layer:** This layer represents the physical sensors connected to the Raspberry Pi.
2.  **Hardware Abstraction Layer (HAL):** Each sensor has a corresponding Python module in the `src/mower/hardware` or `src/mower/navigation` directory. These modules are responsible for communicating with the hardware and providing a high-level API to access the sensor data.
3.  **Sensor Interface:** The `src/mower/hardware/sensor_interface.py` module acts as a unified interface for all sensors. It initializes the sensors and provides a single method, `get_sensor_data()`, to retrieve data from all of them.
4.  **Main Controller:** The `src/mower/main_controller.py` is the core of the application. It calls the `get_sensor_data()` method from the `SensorInterface` to get the latest sensor readings.
5.  **Web UI:** The `WebInterface` receives the sensor data from the `MainController` and displays it on the web-based user interface.

This architecture allows for a clean separation of concerns, making it easier to manage and extend the sensor integration in the project.
