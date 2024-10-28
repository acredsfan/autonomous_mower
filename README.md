# autonomous_mower

**Raspberry Pi Powered Autonomous Lawn Mower - WIP**

I'm working on building a Raspberry Pi powered autonomous lawn mower. I've experimented with using ChatGPT to help me along with the process, but the size of the project limits how much I can utilize that. Feel free to jump in and make any suggestions for improving/adding to/completing the code I have started.

## **Project Overview**

As for details of the project, I've printed the body from [Cults3D - PimoWRobot Case](https://cults3d.com/en/3d-model/home/pimowrobot-case) (The newer model wasn't available at the time, so mine is model C I believe.)

I started with working from this and even bought the software from this designer: [pimowbot.tgd-consulting.de](http://pimowbot.tgd-consulting.de/)

However, I found that the software did not meet my needs, specifically it does not geofence the robot into my yard so it was essentially a free range robot that I couldn't keep from mowing the neighbors' yards. So I decided to start my own journey of writing a program to meet my needs as described below:

### **Project Requirements**

1. **Weather Detection**: Detect if conditions are ideal for mowing (i.e., not raining or too cold).
2. **Obstacle Detection and Avoidance**: Use sensors and the camera to detect and avoid obstacles and ledges in the yard.
3. **Geofencing**: Stay within an assigned area plotted on Google Maps using the Google Maps JavaScript API, allowing the user to trace their yard with a polygon.
4. **Mowing Pattern Tracking**: Mow in a pattern and track areas already mowed.
5. **Battery Management**: Stop mowing and move to a recharging area if the battery is low.
6. **Control and Monitoring App**: Web and Android app for control, monitoring, and camera streaming. Allows users to track progress on a map and set mowing boundaries.
7. **Path Optimization**: Learn to take more efficient paths and avoid problematic areas over time.
8. **Tampering Detection**: Detect if the robot is being tampered with (e.g., lifted, kicked) and stop operation to prevent injury.
9. **Scheduling**: Allow scheduling of mowing times and adjust based on weather forecasts.
10. **Post-Mowing Behavior**: Move to a sunny location to charge and then to a storage location after charging.
11. **Bonus Features**:
    - **Security Mode**: Act as a security robot when not mowing, patrolling the yard and sending alerts if threats are detected.
    - **Pattern Trimming**: Trim patterns and words into the yard for holidays/events.

### **Hardware Components**

- **Raspberry Pi 4 4GB**
- **64GB micro SD card**
- **[8 MP Raspberry Pi Camera Module](https://a.co/d/0AwH90z)**
- **[20 Watt 12V Solar Panel](https://www.offgridtec.com/offgridtecr-olp-30w-solarpanel-12v-schindeltechnologie-perc.html)**
- **[10A 12V Solar Charge Controller](https://a.co/d/fi02yps)**
- **[12V 20AH LiFePO4 Battery](https://a.co/d/0YHIv9B)**
- **[TP-Link AC1300 WiFi Adapter](https://a.co/d/9hrsDR0)**
- **[BME280 Sensor Module](https://a.co/d/hE2FmhO)**
- **[SparkFun GPS-RTK-SMA Kit](https://a.co/d/ar8m13h)**
  > **NOTE:**  
  > To use RTK for millimeter accuracy, you will need either a Base Station ([instructions provided here](https://www.diyrobocars.com/2023/12/28/using-the-donkey-car-path_follow-template-with-rtk-gps/)) or access to an NTRIP server.  
  > If accuracy between 1.5-2.5 meters suffices, a NEO-M9N or NEO-M8N will suffice without needing a base station or NTRIP server.
- **[DC Voltage Regulator/Buck Converter 12V to 5V](https://a.co/d/2fuTrJv)**
- **[997 DC Motor for Mower Blades](https://a.co/d/gA0PXvn)**
- **2x [12V Worm Gear Motors for Wheels](https://a.co/d/eC2qFmM)**
- **[10Amp 7V-30V DC Motor Driver for R/C (2 Channels)](https://www.cytron.io/p-10amp-7v-30v-dc-motor-driver-for-rc-2-channels)**
- **[MPU-9250 Compass Module](https://a.co/d/iHYSXZ7)**
- **[BNO085 IMU](https://www.adafruit.com/product/4754)**
- **2x [VL53L0X Time of Flight Sensors](https://a.co/d/3Zd6glM)**
- **[INA3221 Power Monitor](https://a.co/d/2HxeiL3)**
- **2x [KY-003 Hall Effect Magnetic Sensor Modules](https://a.co/d/iRczHRb)**
- **[IBT-4 Motor Driver Board](https://a.co/d/cl5WV3u)**
- **[I2C Splitter](https://www.aliexpress.us/item/3256801588962655.html?gatewayAdapt=glo2usa4itemAdapt)**

**Considering to incorporate:**

- **[youyeetoo RPLIDAR C1 Fusion Lidar DTOF](https://a.co/d/4W2Vmj7)**

I'll be happy to share any details you'd be interested in; just let me know.

---

## **Installation Instructions**

You have two options to set up and run the `autonomous_mower` project:

1. **Using the Shell Script (`install_requirements.sh`)**
2. **Using Docker**

### **Option 1: Using the Shell Script**

Follow these steps to set up the project using the provided shell script:

1. **Clone the Repository:**

    ```bash
    git clone https://github.com/acredsfan/autonomous_mower.git
    ```

2. **Navigate to the Project Directory:**

    ```bash
    cd autonomous_mower
    ```

3. **Make `install_requirements.sh` Executable:**

    ```bash
    chmod +x install_requirements.sh
    ```

4. **Run the Installation Script:**

    ```bash
    ./install_requirements.sh
    ```

    **NOTE:** This script will install system dependencies, create a virtual environment, and install Python packages. It will output a list of any packages that failed to install; review this list to address any issues.

5. **Download TensorFlow Model for Object Detection:**

    ```bash
    wget https://storage.googleapis.com/tfhub-lite-models/tensorflow/lite-model/mobilenet_v2_1.0_224/1/metadata/1.tflite -O /PATH/TO/autonomous_mower/mobilenet_v2_1.0_224.tflite
    ```

    **Note:** If transferring via WinSCP, update the folder ownership to avoid transfer errors (change `/home/pi` to the folder where you cloned the repository):

    ```bash
    sudo chown -R pi:pi /home/pi/autonomous_mower/
    ```

6. **Obtain a Google Maps JavaScript API Key and Map ID:**

    Follow the steps outlined below to obtain and configure your Google Maps API credentials.

7. **Update and Save `.env.example` as `.env`:**

    Populate the `.env` file with all necessary information, including your API keys and other configurations.

8. **If Using roboHat:**

    Take `rp2040_code.py` from the `robohat_files` directory, load it onto the RP2040, and rename it to `code.py`.

9. **Run `robot.py` to Start the Program:**

    ```bash
    python -m autonomous_mower.robot
    ```

10. **Access the Web UI:**

    Navigate to `http://{hostname}.local:8080` to set up the robot boundaries and schedules, as well as to view sensor data and controls.

### **Option 2: Using Docker**

Docker provides a consistent environment for running your application across different systems. Follow these steps to set up and run the project using Docker:

#### **a. Prerequisites**

- **Docker Installed**: Ensure Docker is installed on your system. You can download it from [here](https://www.docker.com/get-started).

#### **b. Building the Docker Image**

1. **Clone the Repository:**

    ```bash
    git clone https://github.com/acredsfan/autonomous_mower.git
    ```

2. **Navigate to the Project Directory:**

    ```bash
    cd autonomous_mower
    ```

3. **Build the Docker Image:**

    ```bash
    docker build -t autonomous_mower:latest .
    ```

    **Explanation:**
    - `docker build`: Builds a Docker image from the Dockerfile.
    - `-t autonomous_mower:latest`: Tags the image as `autonomous_mower` with the `latest` tag.
    - `.`: Specifies the current directory as the build context.

#### **c. Running the Docker Container**

1. **Create a `.env` File:**

    Copy the example environment variables to create your own `.env` file.

    ```bash
    cp .env.example .env
    ```

    **Populate `.env` with Necessary Variables:**

    Open the `.env` file in a text editor and update it with your specific information:

    ```
    GOOGLE_MAPS_API_KEY=your-google-maps-api-key
    GOOGLE_MAPS_MAP_ID=your-google-maps-map-id
    # Add other environment variables as needed
    ```

2. **Run the Docker Container:**

    ```bash
    docker run -d \
      --name autonomous_mower_container \
      -p 5000:5000 \
      -p 8080:8080 \
      --restart unless-stopped \
      --env-file .env \
      autonomous_mower:latest
    ```

    **Explanation:**
    - `docker run`: Runs a new container from an image.
    - `-d`: Runs the container in detached mode (in the background).
    - `--name autonomous_mower_container`: Names the container for easier reference.
    - `-p 5000:5000`: Maps port `5000` of the host to port `5000` of the container.
    - `-p 8080:8080`: Maps port `8080` of the host to port `8080` of the container.
    - `--restart unless-stopped`: Automatically restarts the container unless it is explicitly stopped.
    - `--env-file .env`: Passes environment variables from the `.env` file to the container.
    - `autonomous_mower:latest`: Specifies the image to use.

3. **Verify the Container is Running:**

    ```bash
    docker ps
    ```

    You should see `autonomous_mower_container` listed as running.

4. **Access the Application:**

    Navigate to `http://{hostname}.local:8080` to access the web UI.

#### **d. Managing the Docker Container**

- **View Running Containers:**

    ```bash
    docker ps
    ```

- **Stop the Container:**

    ```bash
    docker stop autonomous_mower_container
    ```

- **Start the Container Again:**

    ```bash
    docker start autonomous_mower_container
    ```

- **View Logs:**

    ```bash
    docker logs -f autonomous_mower_container
    ```

- **Remove the Container:**

    ```bash
    docker rm -f autonomous_mower_container
    ```

#### **e. Updating the Application**

To update the Docker image after making changes to your code:

1. **Rebuild the Docker Image:**

    ```bash
    docker build -t autonomous_mower:latest .
    ```

2. **Restart the Container:**

    ```bash
    docker stop autonomous_mower_container
    docker rm autonomous_mower_container
    docker run -d \
      --name autonomous_mower_container \
      -p 5000:5000 \
      -p 8080:8080 \
      --restart unless-stopped \
      --env-file .env \
      autonomous_mower:latest
    ```

---

## **Google Maps API Key and Map ID Configuration**

### **Steps to Obtain a Google Maps API Key and Map ID**

1. **Get a Google Maps API Key:**
   - Visit the [Google Cloud Console](https://console.cloud.google.com/).
   - Create or select a project.
   - Enable the **Maps JavaScript API** in the "APIs & Services > Library" section.
   - Navigate to **APIs & Services > Credentials**, and click **Create Credentials > API Key**.
   - Copy the generated API key.

2. **Get a Map ID:**
   - In the Google Cloud Console, navigate to **Google Maps Platform > Maps**.
   - Click **Create Map ID**, provide a name, and configure any settings.
   - Copy the generated Map ID.

3. **Update the `.env` File:**
   - After obtaining your API key and Map ID, update the `.env` file with these values:

     ```
     GOOGLE_MAPS_API_KEY=your-google-maps-api-key
     GOOGLE_MAPS_MAP_ID=your-google-maps-map-id
     ```

4. **Save and Restart