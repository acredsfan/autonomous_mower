# Remote Access Setup Guide

This guide provides step-by-step instructions for setting up remote access to your Autonomous Mower. You can choose from several methods, including Dynamic DNS (DDNS), Cloudflare Tunnel, NGROK, or manual port forwarding. These steps are based on the options provided in the setup wizard and are suitable for Raspberry Pi OS Bookworm (Python 3.11+).

## 1. Prerequisites
- Your mower is connected to your local network (Wi-Fi or Ethernet).
- You have completed the initial setup and can access the web interface locally.
- You have administrative access to your router (for port forwarding/DDNS).

---

## 2. Remote Access Methods

### A. Dynamic DNS (DDNS)
1. **Sign up for a DDNS provider** (e.g., DuckDNS, No-IP, DynDNS).
2. **Create a domain** (e.g., `mymower.duckdns.org`).
3. **Obtain your DDNS token/key** from your provider.
4. **Configure your router** to update your DDNS record (or use a Pi script).
5. **Set up port forwarding** on your router:
   - Forward the mower's web interface port (default: 5000) to your Pi's local IP.
   - Use a strong password and enable SSL if possible.
6. **Enter your DDNS details** in the setup wizard or `.env` file:
   - `DDNS_PROVIDER`, `DDNS_DOMAIN`, `DDNS_TOKEN`, `USE_DDNS=True`

### B. Cloudflare Tunnel
1. **Sign up for a Cloudflare account** and add your domain to Cloudflare.
2. **Navigate to the Cloudflare Dashboard:**
   - Go to `dash.cloudflare.com`.
   - Select your account and then your domain.
3. **Access Zero Trust Dashboard:**
   - In the left-hand sidebar, click on "Networks" and then "Tunnels" (or look for "Zero Trust" on the main Cloudflare dashboard and navigate to Access > Tunnels from there).
4. **Create a Tunnel:**
   - Click on "Create a tunnel".
   - Choose "Cloudflared" as the connector type and click "Next".
   - Give your tunnel a name (e.g., `mower-tunnel`) and click "Save tunnel".
5. **Install and Run `cloudflared` Connector on your Raspberry Pi:**
   - Cloudflare will now display commands to install and run the `cloudflared` connector. It will provide a token specific to your tunnel.
   - **Install `cloudflared` on your Pi (if not already installed):**
     ```bash
     curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb -o cloudflared.deb
     sudo dpkg -i cloudflared.deb
     ```
   - **Run the connector command provided by the Cloudflare dashboard.** It will look something like this (DO NOT use this exact command, use the one from YOUR dashboard):
     ```bash
     # Example command from Cloudflare dashboard - YOURS WILL BE DIFFERENT!
     cloudflared service install eyJhIjoiYOUR_TUNNEL_ID_WILL_BE_HERE........YOUR_TOKEN_WILL_BE_HERE="
     ```
     This command installs `cloudflared` as a system service, so it starts automatically.
6. **Configure the Tunnel to Route Traffic (Public Hostname):**
   - Back in the Cloudflare dashboard for your tunnel, go to the "Public Hostnames" tab.
   - Click "Add a public hostname".
   - **Subdomain:** Enter a subdomain (e.g., `mower`) for your domain (e.g., `example.com`, so it becomes `mower.example.com`).
   - **Service Type:** Select `HTTP`.
   - **URL:** Enter `localhost:5000` (or whatever port your mower's web interface runs on).
   - You can configure additional settings under "Additional application settings" if needed (e.g., HTTPS settings, access policies).
   - Click "Save hostname".
7. **Verify:** Your mower should now be accessible via the public hostname you configured (e.g., `https://mower.example.com`).
8. **Enter your Cloudflare details** in the setup wizard or `.env` file (if the application requires them for API interactions, otherwise this step might not be needed if the tunnel is managed purely from Cloudflare's side):
   - `CLOUDFLARE_DOMAIN=yourmowerdomain.example.com` (the full public hostname)
   - `USE_CLOUDFLARE=True`
   - Note: `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ZONE_ID` might not be strictly necessary for the application if the tunnel is fully managed via the dashboard, but some applications use these for dynamic DNS updates or other Cloudflare API interactions. Check your application's specific needs.

### C. NGROK
1. **Sign up for an NGROK account** and get your authtoken.
2. **Install NGROK on your Pi:**
   ```bash
   curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
   echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
   sudo apt update && sudo apt install ngrok
   ngrok config add-authtoken <YOUR_AUTHTOKEN>
   ```
3. **Expose the web interface:**
   ```bash
   ngrok http 5000
   ```
4. **Enter your NGROK details** in the setup wizard or `.env` file:
   - `NGROK_AUTHTOKEN`, `USE_NGROK=True`

### D. Manual/Port Forwarding
1. **Log in to your router's admin interface.**
2. **Set up port forwarding:**
   - Forward the mower's web interface port (default: 5000) to your Pi's local IP.
   - Use a strong password and enable SSL if possible.
3. **(Optional) Use a static IP or DHCP reservation** for your Pi.

### E. Securing with HTTPS using Let's Encrypt (Certbot)

For any remote access method that exposes your mower directly to the internet (especially DDNS or Manual Port Forwarding), it is **highly recommended** to secure the web interface with HTTPS. Let's Encrypt provides free SSL/TLS certificates, and Certbot is a tool to automate their issuance and renewal.

**Prerequisites for Let's Encrypt:**

*   **A registered domain name:** You need a domain name (e.g., `mymower.example.com`) that points to your Raspberry Pi's public IP address. This is often used in conjunction with DDNS.
*   **Port 80 (and optionally 443) open:** Your router must forward port 80 (for HTTP validation) and ideally port 443 (for HTTPS) from the internet to your Raspberry Pi.

**Installation and Setup:**

1.  **Install Certbot:**
    ```bash
    sudo apt update
    sudo apt install certbot python3-certbot-nginx # Or python3-certbot-apache if using Apache
    ```
    If you are running a simple Python web server (like Flask, often used in these projects) without a full web server like Nginx or Apache in front of it, you might use Certbot's standalone mode or webroot mode. For standalone:
    ```bash
    sudo apt install certbot
    ```

2.  **Obtain a Certificate (Standalone Mode Example):**
    This mode temporarily runs a small web server on port 80 to validate your domain. Stop any service currently using port 80 (e.g., your mower's web app if it's on port 80, or Nginx/Apache if installed but not used for this).
    ```bash
    sudo certbot certonly --standalone -d yourmowerdomain.example.com
    ```
    Replace `yourmowerdomain.example.com` with your actual domain name. Follow the prompts, including providing an email address for renewal reminders.

3.  **Obtain a Certificate (Webroot Mode Example):**
    If your mower's Python web application serves files from a specific directory (webroot) over HTTP on port 80, you can use this mode.
    Let's say your application serves from `/var/www/html/mower_app`.
    ```bash
    sudo certbot certonly --webroot -w /var/www/html/mower_app -d yourmowerdomain.example.com
    ```

4.  **Certificate Files:**
    If successful, Certbot will place your certificate files in `/etc/letsencrypt/live/yourmowerdomain.example.com/`:
    *   `fullchain.pem`: Your full certificate chain (certificate + intermediate).
    *   `privkey.pem`: Your private key.
    **These files are sensitive, especially `privkey.pem`. Ensure they are readable only by root or the user running your web application.**

5.  **Configure Your Mower Application for HTTPS:**
    You'll need to modify your Python web application (e.g., Flask, FastAPI) to use these certificate files to serve HTTPS traffic. This usually involves:
    *   Pointing the web server to `fullchain.pem` and `privkey.pem`.
    *   Listening on port 443 (or another port, then port forward 443 to it).

    **Example for Flask (conceptual):**
    ```python
    # In your main Flask app file
    # from flask import Flask
    # app = Flask(__name__)
    # ... your routes ...
    # if __name__ == '__main__':
    #     context = ('/etc/letsencrypt/live/yourmowerdomain.example.com/fullchain.pem', 
    #                '/etc/letsencrypt/live/yourmowerdomain.example.com/privkey.pem')
    #     app.run(host='0.0.0.0', port=5000, ssl_context=context) # Or port 443 directly
    ```
    Update your `.env` or configuration to reflect HTTPS usage:
    `WEB_INTERFACE_USE_HTTPS=True`
    `WEB_INTERFACE_CERT_PATH=/etc/letsencrypt/live/yourmowerdomain.example.com/fullchain.pem`
    `WEB_INTERFACE_KEY_PATH=/etc/letsencrypt/live/yourmowerdomain.example.com/privkey.pem`

6.  **Automate Renewal:**
    Let's Encrypt certificates are valid for 90 days. Certbot typically sets up a cron job or systemd timer to automatically renew them. You can test renewal with:
    ```bash
    sudo certbot renew --dry-run
    ```
    If your application needs to be restarted after renewal to pick up the new certificate, you might need to add a `--deploy-hook` to your Certbot renewal command (e.g., `sudo certbot renew --deploy-hook "sudo systemctl restart mower-app.service"`).

**Important Considerations:**

*   **Firewall:** Ensure your Raspberry Pi's firewall (if configured, e.g., `ufw`) allows traffic on port 80 and 443.
*   **Permissions:** The user running your web application needs read access to the certificate and private key. Be careful with permissions.
*   **Web Server Integration:** If you decide to use Nginx or Apache as a reverse proxy in front of your Python application, Certbot's Nginx/Apache plugins can automate much of the HTTPS configuration for those servers.

---

## 3. Security Recommendations
- Always use strong, unique passwords for remote access.
- Enable SSL/HTTPS for the web interface.
- Restrict access by IP if possible.
- Regularly update your Pi and mower software.

---

## 4. Troubleshooting
- If you cannot access the mower remotely, check:
  - Your Pi's local IP and port
  - Router port forwarding rules
  - DDNS/tunnel/NGROK status
  - Firewall settings
- For more help, see the [troubleshooting guide](../troubleshooting/index.md).

---

## 5. References
- [DuckDNS](https://www.duckdns.org/)
- [No-IP](https://www.noip.com/)
- [Cloudflare Tunnel Docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [NGROK Docs](https://ngrok.com/docs)

---

*This guide is based on the options and logic in `setup_wizard.py` and is suitable for Raspberry Pi OS Bookworm (Python 3.11+).*
