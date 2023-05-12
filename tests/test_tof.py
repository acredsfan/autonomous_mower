from hardware_interface import sensor_interface


try:
    while True:
        print("tof_left: ", sensor_interface.read_tof_left())
        print("tof_right: ", sensor_interface.read_tof_right())

        time.sleep(0.1)

except KeyboardInterrupt:
    sys.exit()