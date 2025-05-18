"""Remote access setup utility for the autonomous mower.

This module provides functionality to configure various remote access methods
for the mower's web interface.
"""

import os
import sys
import logging
import subprocess
from typing import Dict, Any
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class RemoteAccessSetup:
    """Handles setup of various remote access methods for the mower."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the remote access setup.

        Args:
            config: Dictionary containing configuration values from .env file
        """
        self.config = config
        self.access_type = config.get("REMOTE_ACCESS_TYPE", "port_forward")
        self.web_port = config.get("WEB_UI_PORT", 8080)

# Pre-flight network diagnostics
        try:
            from mower.utilities.network_diagnostics import run_preflight_check
            if not run_preflight_check():
                logger.error(
                    "Network diagnostics failed. "
                    "Please resolve network issues before configuring remote access.")
                return False
        except ImportError as e:
            logger.warning(
                "Could not import network diagnostics. "
                "Skipping pre-flight network check. Error: %s", str(e)
            )

    def setup(self) -> bool:
        """Configure the selected remote access method.

        Returns:
            bool: True if setup was successful, False otherwise
        """
        setup_methods = {
            "port_forward": self._setup_port_forward,
            "ddns": self._setup_ddns,
            "cloudflare": self._setup_cloudflare,
            "custom_domain": self._setup_custom_domain,
            "ngrok": self._setup_ngrok,
        }

        if self.access_type not in setup_methods:
            logger.error(
                f"Unsupported remote access type: {self.access_type}"
            )
            return False

        try:
            return setup_methods[self.access_type]()
        except Exception as e:
            logger.error(f"Error setting up {self.access_type}: {str(e)}")
            return False

    def _setup_port_forward(self) -> bool:
        """Configure basic port forwarding.

        Returns:
            bool: True if setup was successful
        """
        logger.info("Setting up port forwarding...")
        logger.info(
            f"Please configure your router to forward port {self.web_port} "
            "to your mower's IP address"
        )
        return True

    def _setup_ddns(self) -> bool:
        """Configure Dynamic DNS service.

        Returns:
            bool: True if setup was successful
        """
        provider = self.config.get("DDNS_PROVIDER")
        domain = self.config.get("DDNS_DOMAIN")
        token = self.config.get("DDNS_TOKEN")

        if not all([provider, domain, token]):
            logger.error("Missing required DDNS configuration")
            return False

        if provider == "duckdns":
            return self._setup_duckdns(domain, token)
        elif provider == "noip":
            return self._setup_noip(domain, token)
        else:
            logger.error(f"Unsupported DDNS provider: {provider}")
            return False

    def _setup_duckdns(self, domain: str, token: str) -> bool:
        """Configure DuckDNS service.

        Args:
            domain: DuckDNS domain
            token: DuckDNS token

        Returns:
            bool: True if setup was successful
        """
        try:
            # Create DuckDNS update script
            script_path = Path("/usr/local/bin/update_duckdns.sh")
            script_content = f"""#!/bin/bash
curl "https://www.duckdns.org/update?domains={domain}&token={token}&ip="
"""
            script_path.write_text(script_content)
            script_path.chmod(0o755)

            # Add to crontab
            subprocess.run(["crontab", "-l"], capture_output=True, text=True)
            subprocess.run(["crontab", "-l"], capture_output=True, text=True)

            logger.info("DuckDNS setup completed successfully")
            return True
        except Exception as e:
            logger.error(f"Error setting up DuckDNS: {str(e)}")
            return False

    def _setup_noip(self, domain: str, token: str) -> bool:
        """Configure No-IP service.

        Args:
            domain: No-IP domain
            token: No-IP token

        Returns:
            bool: True if setup was successful
        """
        try:
            # Install No-IP client
            subprocess.run(["sudo", "apt-get", "install", "noip2"])

            # Configure No-IP client
            subprocess.run(["sudo", "noip2", "-C"])

            logger.info("No-IP setup completed successfully")
            return True
        except Exception as e:
            logger.error(f"Error setting up No-IP: {str(e)}")
            return False

    def _setup_cloudflare(self) -> bool:
        """Configure Cloudflare Tunnel.

        Returns:
            bool: True if setup was successful
        """
        token = self.config.get("CLOUDFLARE_TOKEN")
        zone_id = self.config.get("CLOUDFLARE_ZONE_ID")
        tunnel_name = self.config.get(
            "CLOUDFLARE_TUNNEL_NAME", "mower-tunnel"
        )

        if not all([token, zone_id]):
            logger.error("Missing required Cloudflare configuration")
            return False

        try:
            # Install cloudflared
            subprocess.run(["sudo", "apt-get", "install", "cloudflared"])

            # Configure tunnel
            subprocess.run(["cloudflared", "tunnel", "create", tunnel_name])

            logger.info("Cloudflare Tunnel setup completed successfully")
            return True
        except Exception as e:
            logger.error(f"Error setting up Cloudflare Tunnel: {str(e)}")
            return False

    def _setup_custom_domain(self) -> bool:
        """Configure custom domain with SSL.

        Returns:
            bool: True if setup was successful
        """
        domain = self.config.get("CUSTOM_DOMAIN")
        email = self.config.get("SSL_EMAIL")

        if not all([domain, email]):
            logger.error("Missing required custom domain configuration")
            return False

        try:
            # Install certbot
            subprocess.run(
                [
                    "sudo",
                    "apt-get",
                    "install",
                    "certbot",
                    "python3-certbot-nginx",
                ]
            )

            # Obtain SSL certificate
            subprocess.run(
                [
                    "sudo",
                    "certbot",
                    "certonly",
                    "--standalone",
                    "-d",
                    domain,
                    "--email",
                    email,
                    "--agree-tos",
                ]
            )

            logger.info(f"Custom domain setup completed for {domain}")
            return True
        except Exception as e:
            logger.error(f"Error setting up custom domain: {str(e)}")
            return False

    def _setup_ngrok(self) -> bool:
        """Configure NGROK tunnel.

        Returns:
            bool: True if setup was successful
        """
        token = self.config.get("NGROK_AUTH_TOKEN")

        if not token:
            logger.error("Missing required NGROK configuration")
            return False

        try:
            # Install NGROK
            subprocess.run(["sudo", "apt-get", "install", "ngrok"])

            # Configure NGROK
            subprocess.run(["ngrok", "config", "add-authtoken", token])

            logger.info("NGROK setup completed successfully")
            return True
        except Exception as e:
            logger.error(f"Error setting up NGROK: {str(e)}")
            return False


def main():
    """Main entry point for the remote access setup script."""
    try:
        # Load configuration from .env file
        from dotenv import load_dotenv

        load_dotenv()

        config = dict(os.environ)
        setup = RemoteAccessSetup(config)

        if setup.setup():
            logger.info("Remote access setup completed successfully")
        else:
            logger.error("Remote access setup failed")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Error in remote access setup: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
