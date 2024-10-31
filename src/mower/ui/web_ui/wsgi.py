import os
import sys

from mower.ui.web_ui.app import WebInterface
from mower.utilities.logger_config import LoggerConfigInfo as LoggerConfig

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def start_web_interface():
    # Check if the web interface is already running
    if WebInterface.is_running():
        logging.warning("Web interface is already running.")
        return
    WebInterface.start()


# Initialize logger
logging = LoggerConfig.get_logger(__name__)

if __name__ == "__main__":
    start_web_interface()
