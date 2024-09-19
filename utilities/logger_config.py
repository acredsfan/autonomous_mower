import logging


class LoggerConfigDebug:
    @staticmethod
    def configure_logging(log_file="main.log"):
        logging.basicConfig(
            filename=log_file,
            level=logging.DEBUG,
            format=(
                "%(asctime)s - %(name)s - %(levelname)s - "
                "%(filename)s:%(lineno)d - %(message)s"
            ),
        )
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        logging.getLogger().addHandler(console_handler)

    @staticmethod
    def get_logger(name):
        return logging.getLogger(name)
    

class LoggerConfigInfo:
    @staticmethod
    def configure_logging(log_file="main.log"):
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format=(
                "%(asctime)s - %(name)s - %(levelname)s - "
                "%(filename)s:%(lineno)d - %(message)s"
            ),
        )
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        logging.getLogger().addHandler(console_handler)

    @staticmethod
    def get_logger(name):
        return logging.getLogger(name)