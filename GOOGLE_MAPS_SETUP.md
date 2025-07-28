# Google Maps API Setup

To enable the mapping features (boundary drawing, no-go zones, home location), you need to configure a Google Maps API key.

## Step 1: Get a Google Maps API Key

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the following APIs:
   - Maps JavaScript API
   - Places API (optional, for location search)
4. Go to "Credentials" → "Create Credentials" → "API Key"
5. Copy your API key

## Step 2: Configure the API Key

1. Edit the configuration file:
   ```bash
   sudo nano /home/pi/autonomous_mower/mower/config/config.yaml
   ```

2. Add your API key to the services section:
   ```yaml
   services:
     redis_host: localhost
     redis_port: 6379
     web_port: 8080
     google_maps_api_key: "YOUR_API_KEY_HERE"
   ```

3. Restart the mower service:
   ```bash
   sudo systemctl restart autonomous-mower-v3
   ```

## Step 3: Using the Mapping Features

1. Open the web interface: http://your-pi-ip:8080
2. In the "Yard Map & Zones" section, you can:
   - **Boundary**: Click to draw your yard boundary (keeps mower inside)
   - **No-Go**: Click to draw no-go zones (areas to avoid)
   - **Home**: Click to set the charging station location
3. Click "Save Zones" to store your settings

## Security Note

- Restrict your API key to your domain/IP address in the Google Cloud Console
- Consider setting usage quotas to prevent unexpected charges

## Alternative: Free Usage

Google Maps provides a generous free tier that should be sufficient for personal use:
- 28,000 map loads per month free
- Additional usage is charged per request

Without an API key, the interface will work but the map will show a "development purposes only" watermark.
