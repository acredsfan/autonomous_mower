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
1. **Sign up for a Cloudflare account** and add your domain.
2. **Install `cloudflared` on your Pi:**
   ```bash
   curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb -o cloudflared.deb
   sudo dpkg -i cloudflared.deb
   ```
3. **Create a tunnel:**
   ```bash
   cloudflared tunnel login
   cloudflared tunnel create mower-tunnel
   cloudflared tunnel route dns mower-tunnel mower.example.com
   ```
4. **Run the tunnel:**
   ```bash
   cloudflared tunnel run mower-tunnel --url http://localhost:5000
   ```
5. **Enter your Cloudflare details** in the setup wizard or `.env` file:
   - `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ZONE_ID`, `CLOUDFLARE_DOMAIN`, `USE_CLOUDFLARE=True`

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
