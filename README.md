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

• Raspberry Pi 4 2GB
• 64GB micro SD card
• 5 MP Raspberry pi camera module - https://www.amazon.com/gp/product/B07RXKZ1KN/ref=ppx_yo_dt_b_search_asin_title?ie=UTF8&th=1
• 20 Watt 12V solar panel - https://www.offgridtec.com/offgridtecr-olp-30w-solarpanel-12v-schindeltechnologie-perc.html
• 10A 12V solar charge controller - https://www.amazon.com/gp/product/B07VDRN9LK/ref=ppx_yo_dt_b_search_asin_title?ie=UTF8&th=1
• 12V 18AH SLA Battery - https://www.amazon.com/gp/product/B00K8V2PF4/ref=ppx_yo_dt_b_search_asin_title?ie=UTF8&th=1
• TP-Link AC1300 WiFi Adapter - https://www.amazon.com/gp/product/B08D72GSMS/ref=ppx_yo_dt_b_search_asin_title?ie=UTF8&psc=1
• BME280 sensor module - https://www.amazon.com/gp/product/B07KR24P6P/ref=ppx_yo_dt_b_search_asin_title?ie=UTF8&psc=1
• Neo-8M GPS Module - https://www.amazon.com/Shapea-NEO-8M-NEO8MV2-Control-Antenna/dp/B0BKL87C74/ref=sr_1_1?keywords=neo+8m&qid=1683213881&sr=8-1
• 12V 2 Channel Relay - https://www.amazon.com/gp/product/B0057OC6D8/ref=ppx_yo_dt_b_search_asin_title?ie=UTF8&th=1
• DC Voltage Regulator/Buck Converter 12V to 5V - https://www.amazon.com/gp/product/B08CHMJM9J/ref=ppx_yo_dt_b_search_asin_title?ie=UTF8&th=1
• 997 DC motor for mower blades - https://www.amazon.com/Powerful-Voltage-DC12-36V-Silent-Bearing/dp/B08R73MQF1/ref=sr_1_3?hvadid=631587578546&hvdev=c&hvlocphy=9015649&hvnetw=g&hvqmt=e&hvrand=15298291863334120737&hvtargid=kwd-352957084306&hydadcr=19964_13472495&keywords=997%2Bmotor&qid=1683309933&sr=8-3&th=1
• 2x 12V worm gear motors for wheels - https://www.amazon.com/gp/product/B00NMDPQAQ/ref=ppx_yo_dt_b_search_asin_title?ie=UTF8&psc=1
• L298 12V Dual H Bridge motor speed controller - https://www.amazon.com/gp/product/B09X18KHB8/ref=ppx_yo_dt_b_search_asin_title?ie=UTF8&psc=1
• MPU-9250 Compass Module - https://www.amazon.com/gp/product/B07D55TK6Z/ref=ppx_yo_dt_b_search_asin_title?ie=UTF8&psc=1
• 2x VL53L0X Time of flight sensors - https://www.amazon.com/gp/product/B07XXTMRR2/ref=ppx_yo_dt_b_search_asin_title?ie=UTF8&th=1
• INA3221 Power Monitor - https://www.amazon.com/gp/product/B0946L63LC/ref=ppx_yo_dt_b_search_asin_title?ie=UTF8&th=1
• 2x KY-003 Hall Effect Magnetic Sensor Modules - https://www.amazon.com/gp/product/B085KVV82D/ref=ppx_yo_dt_b_search_asin_title?ie=UTF8&psc=1

I'll be happy to share any details you'd be interested in just let me know.

UPDATE 6.5.2023 - I've added a .env.template to store the API key for Google Maps, to run the mapping module you need to update the file with your API key and save it as .env