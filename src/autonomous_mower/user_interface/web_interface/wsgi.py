import os
import sys

from user_interface.web_interface.app import start_web_interface
from autonomous_mower.utilities.logger_config import LoggerConfigConfigInfo as LoggerConfig

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# Initialize logger
logging = LoggerConfig.get_logger(__name__)

if __name__ == "__main__":
    start_web_interface()
