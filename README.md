# autonomous_mower
Raspberry Pi Powered Autonomous Lawn Mower - WIP
I'm working on building a Raspberry Pi powered autonomous lawn mower. I've experiemented with using ChatGPT to help me along with the process but the size of the project limits how much I can utilize that. Feel free to jump in and make any suggestions for improving/adding to/completing the code I have started.

As for details of the project, I've printed the body from here: https://cults3d.com/en/3d-model/home/pimowrobot-case (The newer model wasn't available at the time, so mine is model C I believe.)

I started with working from this and even bought the software from this designer: http://pimowbot.tgd-consulting.de/

However, I found that the software did not meet my needs, specifically it does not geofence the robot into my yard so it was essentially a free range robot that I couldn't keep from mowing the neighbors' yards. So I decided to start my own journey of writing a program to meet my needs as described below:

Here are the requirements:

It needs to be able to detect the weather, specifically if conditions are ideal for mowing (i.e. not raining or too cold)
It needs to detect and avoid obstacles and ledges in the yard by using sensors and the camera
The robot should stay in an assigned area that can be plotted out on google maps using the Google Maps JavaScript API to allow the user to trace their yard with a polygon too.
The robot needs to mow in a pattern and track where it has and has not been
If the battery is low, it needs to stop mowing and move to an area where it can recharge the battery in the sunlight
It needs to have a web and android app based control and monitoring/camera streaming system so the user can keep track of the robot and control it manually if required. The app should also allow the user to follow the progress on a map and have the polygon input for the mowing area from requirement 3.
It needs to learn to take more efficient paths and avoid trouble areas as it operates over it’s lifetime
It needs to be able to detect if it’s being tampered with (i.e. lifted unexpectedly, kicked, etc) and stop operating immediately to avoid injury to humans or animals.
It needs to allow for scheduling for ideal mowing times and adjust if the weather is predicted to interfere with the schedule.
When the robot is done mowing it needs to go to a sunny location to charge then go to a storage location after it’s fully charged to wait for it’s next scheduled mowing window.
Bonus points if we can get it to also act as a security robot when not mowing where it can patrol the yard on a intermittent basis and send alerts if it detects anything that would be a threat.
Super bonus if we can get it to trim patterns and words into the yard in a special mode for holidays/events.
Here are the sensors and hardware I've procured for the robot:

• Raspberry Pi 4 4GB

• 64GB micro SD card

• 8 MP Raspberry pi camera module - https://a.co/d/0AwH90z

• 20 Watt 12V solar panel - https://www.offgridtec.com/offgridtecr-olp-30w-solarpanel-12v-schindeltechnologie-perc.html

• 10A 12V solar charge controller - https://a.co/d/fi02yps

• 12V 20AH LiFePO4 Battery - https://a.co/d/0YHIv9B

• TP-Link AC1300 WiFi Adapter - https://a.co/d/9hrsDR0

• BME280 sensor module - https://a.co/d/hE2FmhO

• SparkFun GPS-RTK-SMA Kit - https://a.co/d/ar8m13h
    NOTE:To use RTK for millimeter accuracy, you will need either a Base Station (instructions to build provided by @TCIII: [link](https://www.diyrobocars.com/2023/12/28/using-the-donkey-car-path_follow-template-with-rtk-gps/)) or access to a NTRIP server.  If you are ok with accuracy between 1.5-2.5 meters, then a NEO-M9N or NEO-M8N will suffice without the need for a base station or NTRIP server.

• DC Voltage Regulator/Buck Converter 12V to 5V - https://a.co/d/2fuTrJv

• 997 DC motor for mower blades - https://a.co/d/gA0PXvn

• 2x 12V worm gear motors for wheels - https://a.co/d/eC2qFmM

• 2x IBT-2 Motor Drivers for the Wheels - https://a.co/d/cos40lB

• MPU-9250 Compass Module - https://a.co/d/iHYSXZ7

• BNO085 IMU - 

• 2x VL53L0X Time of flight sensors - https://a.co/d/3Zd6glM

• INA3221 Power Monitor - https://a.co/d/2HxeiL3

• 2x KY-003 Hall Effect Magnetic Sensor Modules - https://a.co/d/iRczHRb

• IBT-4 Motor Driver Board - https://a.co/d/cl5WV3u

• I2C splitter - 

Considering to incorporate:
• youyeetoo RPLIDAR C1 Fusion Lidar DTOF - https://a.co/d/4W2Vmj7

I'll be happy to share any details you'd be interested in just let me know.

UPDATE 6.5.2023 - I've added a .env.template to store the API key for Google Maps, to run the mapping module you need to update the file with your API key and save it as .env

UPDATE 7.17.2023 - I've removed the 12V relay from the system and added an IBT-4 Driver for the Mower Blade Motor.

Update 8.9.2023
Here is the current folder/file structure for the project:
.
├── .env.example
├── .gitattributes
├── .gitignore
├── README.md
├── autonomous_mower_code_features_and_functions.txt
├── config.json
├── control_system
│   ├── __init__.py
│   ├── direction_controller.py
│   ├── speed_controller.py
│   └── trajectory_controller.py
├── hardware_interface
│   ├── __init__.py
│   ├── __pycache__
│   │   ├── __init__.cpython-311.pyc
│   │   └── motor_controller.cpython-311.pyc
│   ├── blade_controller.py
│   ├── motor_controller.py
│   └── sensor_interface.py
├── main.py
├── navigation_system
│   ├── __init__.py
│   ├── gps_interface.py
│   ├── localization.py
│   └── path_planning.py
├── obstacle_detection
│   ├── __init__.py
│   ├── avoidance_algorithm.py
│   ├── camera_processing.py
│   └── tof_processing.py
├── requirements.txt
├── tests
│   ├── __init__.py
│   ├── test_bme280.py
│   ├── test_camera.py
│   ├── test_gps.py
│   ├── test_hall_sensors.py
│   ├── test_ina3221.py
│   ├── test_move.py
│   ├── test_mpu9250.py
│   └── test_tof.py
└── user_interface
    ├── __init__.py
    ├── mobile_app
    │   └── __init__.py
    └── web_interface
        ├── __init__.py
        ├── app.py
        ├── appbackup.py
        ├── camera.py
        ├── static
        │   ├── css
        │   │   └── main.css
        │   └── js
        │       ├── jsmpeg.min.js
        │       └── main.js
        ├── templates
        │   ├── area.html
        │   ├── base.html
        │   ├── camera.html
        │   ├── control.html
        │   ├── index.html
        │   ├── settings.html
        │   └── status.html
        └── test_camera.py


Here is a simple dictionary of existing functions:

control_system/direction_controller.py

DirectionController: Class to control the direction of the mower.
__init__(self, motor_controller): Initializes the DirectionController.
set_direction(self, direction): Sets the direction of the mower.
control_system/speed_controller.py

SpeedController: Class to control the speed of the mower.
__init__(self, motor_controller): Initializes the SpeedController.
set_speed(self, speed): Sets the speed of the mower.
control_system/trajectory_controller.py

TrajectoryController: Class to control the trajectory of the mower.
__init__(self, motor_controller, gps_interface, compass_interface): Initializes the TrajectoryController.
set_trajectory(self, trajectory): Sets the trajectory of the mower.
hardware_interface/blade_controller.py

BladeController: Class to control the blades of the mower.
__init__(self): Initializes the BladeController.
set_speed(self, speed): Sets the speed of the blades.
hardware_interface/motor_controller.py

MotorController: Class to control the motors of the mower.
__init__(self): Initializes the MotorController.
set_speed(self, speed): Sets the speed of the motors.
set_direction(self, direction): Sets the direction of the motors.
hardware_interface/sensor_interface.py

SensorInterface: Class to interface with the sensors on the mower.
__init__(self): Initializes the SensorInterface.
read_sensor(self, sensor): Reads data from a specific sensor.
navigation_system/gps_interface.py

GPSInterface: Class to interface with the GPS module.
__init__(self): Initializes the GPSInterface.
get_location(self): Gets the current location from the GPS module.
navigation_system/localization.py

Localization: Class to handle localization of the mower.
__init__(self, gps_interface, compass_interface): Initializes the Localization.
get_location(self): Gets the current location of the mower.
get_orientation(self): Gets the current orientation of the mower.
navigation_system/path_planning.py

PathPlanning: Class to handle path planning for the mower.
__init__(self, gps_interface): Initializes the PathPlanning.
plan_path(self, start, goal): Plans a path from a start location to a goal location.
obstacle_detection/avoidance_algorithm.py

AvoidanceAlgorithm: Class to handle obstacle avoidance.
__init__(self, sensor_interface): Initializes the AvoidanceAlgorithm.
avoid_obstacles(self): Avoids obstacles based on sensor data.
obstacle_detection/camera_processing.py

CameraProcessing: Class to handle camera processing for obstacle detection.
__init__(self): Initializes the CameraProcessing.
process_frame(self, frame): Processes a frame from the camera.
obstacle_detection/tof_processing.py

ToFProcessing: Class to handle Time-of-Flight (ToF) sensor processing for obstacle detection.
__init__(self): Initializes the ToFProcessing.
process_data(self, data): Processes data from the ToF sensor.
user_interface/web_interface/app.py

start_web_interface(): Starts the web interface.
update_sensors(): Updates sensor values.
sensor_data(): Retrieves the latest sensor data.
index(): Renders the status page.
status(): Renders the status page.
control(): Renders the control page.
area(): Renders the area page.
settings(): Renders the settings page.
camera(): Renders the camera page.
video_feed(): Returns the video feed.
move(): Moves the mower in a specified direction.
toggle_mower_blades(): Toggles the mower blades.
start_mowing(): Starts the mower.
stop_mowing(): Stops the mower.
get_mowing_area(): Gets the mowing area.
get_path(): Gets the path.
save_mowing_area(): Saves the mowing area.
get_gps(): Gets the GPS data.
save_settings(): Saves the settings.
get_schedule(): Gets the mowing schedule.
calculate_next_scheduled_mow(): Calculates the next scheduled mow.
set_motor_direction(direction): Sets the motor direction.
start_mower_blades(): Starts the mower blades.
stop_mower_blades(): Stops the mower blades.
stop_motors(): Stops the motors.
gen(camera): Generates the video feed.
user_interface/web_interface/camera.py

VideoCamera: Class to handle video camera operations.
__init__(self): Initializes the VideoCamera.
get_frame(self): Gets a frame from the video camera.

INSTALLATION INSTRUCTIONS:
1. Install necessary packages:
    ```bash
    sudo apt-get install libatlas-base-dev libhdf5-dev libhdf5-serial-dev python3-dev python3-pip i2c-tools sudo apt-get install gpsd gpsd-clients python3-gps
    ```
2. Clone the repository:
    ```bash
    sudo git clone https://github.com/acredsfan/autonomous_mower.git
    ```
3. Go to new folder:
    ```bash
    cd autonomous_mower
    ```
4. Install packages from requirements.txt:
    ```bash
    sudo pip3 install -r requirements.txt
    ```
5. Download the tensorflow model file for object detection (the code in camera_processing.py looks for lite-model_qat_mobilenet_v2_retinanet_256_1.tflite in the obstacle_detection folder, so make sure to update the code if you use something different or if you move the file): https://tfhub.dev/google/lite-model/qat/mobilenet_v2_retinanet_256/1
    1. If you're transferring via WinSCP, update the folder ownership to avoid transfer errors (change'/home/pi' to the folder where you cloned the repository):
    ```bash
    sudo chown -R pi:pi /home/pi/autonomous_mower/
    ```
6. Update and save .env.example as .env with your google maps api key:
    ```bash
    sudo nano .env.example
    ```
7. Run main.py to start the program:
    ```bash
    sudo python3 main.py
    ```
8. Go to web UI at {hostname}.local:90 to set up the robot boundaries and schedules as well as to see sensor data/controls.
