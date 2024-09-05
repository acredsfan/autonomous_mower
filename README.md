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

• [8 MP Raspberry pi camera module](https://a.co/d/0AwH90z)

• [20 Watt 12V solar panel](https://www.offgridtec.com/offgridtecr-olp-30w-solarpanel-12v-schindeltechnologie-perc.html)

• [10A 12V solar charge controller](https://a.co/d/fi02yps)

• [12V 20AH LiFePO4 Battery](https://a.co/d/0YHIv9B)

• [TP-Link AC1300 WiFi Adapter](https://a.co/d/9hrsDR0)

• [BME280 sensor module](https://a.co/d/hE2FmhO)

• [SparkFun GPS-RTK-SMA Kit](https://a.co/d/ar8m13h)

    > **NOTE:** 
    > To use RTK for millimeter accuracy, you will need either a Base Station (instructions to build provided by @TCIII: [link](https://www.diyrobocars.com/2023/12/28/using-the-donkey-car-path_follow-template-with-rtk-gps/)) or access to a NTRIP server. 
    > If you are ok with accuracy between 1.5-2.5 meters, then a NEO-M9N or NEO-M8N will suffice without the need for a base station or NTRIP server.


• [DC Voltage Regulator/Buck Converter 12V to 5V](https://a.co/d/2fuTrJv)

• [997 DC motor for mower blades](https://a.co/d/gA0PXvn)

• 2x [12V worm gear motors for wheels](https://a.co/d/eC2qFmM)

• [10Amp 7V-30V DC Motor Driver for R/C (2 Channels)](https://www.cytron.io/p-10amp-7v-30v-dc-motor-driver-for-rc-2-channels)

• [MPU-9250 Compass Module](https://a.co/d/iHYSXZ7)

• [BNO085 IMU](https://www.adafruit.com/product/4754)

• 2x [VL53L0X Time of flight sensors](https://a.co/d/3Zd6glM)

• [INA3221 Power Monitor](https://a.co/d/2HxeiL3)

• 2x [KY-003 Hall Effect Magnetic Sensor Modules](https://a.co/d/iRczHRb)

• [IBT-4 Motor Driver Board](https://a.co/d/cl5WV3u)

• [I2C splitter](https://www.aliexpress.us/item/3256801588962655.html?gatewayAdapt=glo2usa4itemAdapt)

Considering to incorporate:
• [youyeetoo RPLIDAR C1 Fusion Lidar DTOF](https://a.co/d/4W2Vmj7)

I'll be happy to share any details you'd be interested in just let me know.

INSTALLATION INSTRUCTIONS:
1. Install necessary packages:
    ```bash
    sudo apt-get install libatlas-base-dev libhdf5-dev libhdf5-serial-dev python3-dev python3-pip i2c-tools gpsd gpsd-clients python3-gps python3-libgpiod libportaudio2 libportaudiocpp0 portaudio19-dev
    ```
    Note: to get gpiod to work within the venv, you must run the following command after your venv is created, replacing "/path/to/venv" with the correct path to your venv:
    ```bash
    python3 -m venv --system-site-packages /path/to/venv
    ```


2. Clone the repository:
    ```bash
    sudo git clone https://github.com/acredsfan/autonomous_mower.git
    ```

3. Go to the new folder:
    ```bash
    cd autonomous_mower
    ```

4. Set up a virtual environment and activate it:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

5. Install packages from requirements.txt:
    ```bash
    pip install -r requirements.txt
    ```

6. Download the TensorFlow model file for object detection (the code in `camera_processing.py` looks for `lite-model_qat_mobilenet_v2_retinanet_256_1.tflite` in the `obstacle_detection` folder, so make sure to update the code if you use something different or if you move the file): [TensorFlow Model](https://tfhub.dev/google/lite-model/qat/mobilenet_v2_retinanet_256/1)
    1. If you're transferring via WinSCP, update the folder ownership to avoid transfer errors (change '/home/pi' to the folder where you cloned the repository):
    ```bash
    sudo chown -R pi:pi /home/pi/autonomous_mower/
    ```

7. Obtain a Google Maps JavaScript API key following the instructions here: [Get API Key](https://developers.google.com/maps/documentation/javascript/get-api-key#create-api-keys)

8. Update and save `.env.example` as `.env` with your Google Maps API key:
    ```bash
    cp .env.example .env
    nano .env
    ```
    Add your API key to the `.env` file and save it.

9. Run `main.py` to start the program:
    ```bash
    python main.py
    ```

10. Go to the web UI at `{hostname}.local:90` to set up the robot boundaries and schedules as well as to see sensor data/controls.
