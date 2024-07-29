from dotenv import load_dotenv, find_dotenv
import os

# Load environment variables from .env file
load_dotenv(find_dotenv())

google_maps_api_key = os.getenv('GOOGLE_MAPS_API_KEY')
wifi_networks = os.getenv('Wifi_Networks_to_Scan')

print(f"GOOGLE_MAPS_API_KEY: {google_maps_api_key}")
print(f"Wifi_Networks_to_Scan: {wifi_networks}")