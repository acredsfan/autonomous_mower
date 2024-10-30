import os
import sys

from mower.ui.web_ui.app import WebInterface
from mower.utilities.logger_config import LoggerConfigInfo as LoggerConfig

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# Initialize logger
logging = LoggerConfig.get_logger(__name__)

if __name__ == "__main__":
    WebInterface.start()
