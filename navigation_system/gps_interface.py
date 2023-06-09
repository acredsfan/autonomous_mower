import serial
from gpsd import gpsd

class GPSInterface:
    def __init__(self, port='/dev/serial0', baud_rate=9600, timeout=1):
        self.serial = serial.Serial(port, baud_rate, timeout)
        self.serial.flush()
        self.gpsd = gpsd.GPSD(port=port, baudrate=baud_rate, timeout=timeout)

    def read_gps_data(self):
        data = self.gpsd.next()
        if data['class'] == 'TPV':
            return {
                'latitude': data['lat'],
                'longitude': data['lon'],
                'altitude': data['alt'],
                'speed': data['speed'],
                'timestamp': data['time'],
                'satellites': data['satellites'],
                'quality': data['fix'],
                'pdop': data['pdop'],
                'hdop': data['hdop'],
                'vdop': data['vdop'],
            }
        else:
            return None

    def close(self):
        self.gpsd.close()

