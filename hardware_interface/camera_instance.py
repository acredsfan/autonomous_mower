from picamera2 import Picamera2

# Initialize Picamera2 instance
camera = Picamera2()
camera_config = camera.create_video_configuration(main={"size": (640, 480)})
camera.configure(camera_config)
camera.start()

def get_camera_instance():
    return camera
