from user_interface.web_interface.app import start_web_interface, app
import logging

# Initialize logging
logging.basicConfig(filename='main.log', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

if __name__ == "__main__":
    start_web_interface()