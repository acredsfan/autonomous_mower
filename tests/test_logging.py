import os
import logging

# Initialize logging
log_file_path = '/home/pi/autonomous_mower/main.log'
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

# Create handlers
file_handler = logging.FileHandler(log_file_path)
file_handler.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Create formatters and add them to handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers to the logger
logger = logging.getLogger()
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Test logging
logging.debug("Testing logging setup.")
logging.debug("Available GPIO chips: %s", os.listdir('/dev/'))