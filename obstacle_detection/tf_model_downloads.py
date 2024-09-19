import kagglehub

# Download mobilenet-v2 for object and surface detection and save to object_detection folder
kagglehub.download("kaggle/input/obstacle-detection-tf-models/mobilenet_v2_1.0_224_quant.tflite", "obstacle_detection")
# Print path to downloaded model
print("Downloaded model to obstacle_detection folder.")
