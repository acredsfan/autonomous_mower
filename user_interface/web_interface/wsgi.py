from user_interface.web_interface.app import start_web_interface, app
import logging

# Initialize logging
logging.basicConfig(filename='main.log', level=logging.DEBUG)

if __name__ == "__main__":
    start_web_interface()