# Code for testing the web user interface
sys.path.append('/home/pi/autonomous_mower')
from user_interface import web_interface
import time

def main():
    # Initialize the web interface
    web_interface.init_web_interface()

    # Start the web interface
    web_interface.start_web_interface()

    # Wait for a second before next reading
    time.sleep(1)

if __name__ == '__main__':
    main()