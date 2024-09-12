import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from user_interface.web_interface.app import start_web_interface, app
from utils import LoggerConfig

# Initialize logger
logging = LoggerConfig.get_logger(__name__)

if __name__ == "__main__":
    start_web_interface()