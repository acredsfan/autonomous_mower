import gpsd
import time
import logging

# Initialize logging
logging.basicConfig(filename='main.log', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

class KalmanFilter:
    def __init__(self, process_variance, measurement_variance, initial_value=0, initial_estimate=1):
        self.process_variance = process_variance
        self.measurement_variance = measurement_variance
        self.estimate = initial_value
        self.estimate_error = initial_estimate

    def update(self, measurement):
        prediction = self.estimate
        prediction_error = self.estimate_error + self.process_variance

        kalman_gain = prediction_error / (prediction_error + self.measurement_variance)
        self.estimate = prediction + kalman_gain * (measurement - prediction)
        self.estimate_error = (1 - kalman_gain) * prediction_error

        return self.estimate

class GPSInterface:
    def __init__(self):
        gpsd.connect()
        self.kf_latitude = KalmanFilter(0.1, 0.01)  # Tune these values
        self.kf_longitude = KalmanFilter(0.1, 0.01)  # Tune these values

    def read_gps_data(self):
        packet = gpsd.get_current()
        if packet.mode >= 2:  # 2D or 3D fix
            filtered_latitude = self.kf_latitude.update(packet.lat)
            filtered_longitude = self.kf_longitude.update(packet.lon)
            return {
                'latitude': filtered_latitude,
                'longitude': filtered_longitude,
                'altitude': packet.alt,
                'speed': packet.hspeed,  # Horizontal speed
                'timestamp': packet.time,
                'mode': packet.mode,
            }
        else:
            return None