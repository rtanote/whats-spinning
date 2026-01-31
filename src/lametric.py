"""LaMetric Time display integration module."""

from __future__ import annotations

import urllib3
from typing import Any

import requests
from zeroconf import ServiceBrowser, ServiceListener, Zeroconf

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class LaMetricDiscoveryListener(ServiceListener):
    """Listener for LaMetric device discovery via mDNS."""

    def __init__(self):
        """Initialize listener."""
        self.ip_address: str | None = None

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Service discovered callback."""
        info = zc.get_service_info(type_, name)
        if info and info.addresses:
            # Get first IPv4 address
            for addr in info.addresses:
                if len(addr) == 4:  # IPv4
                    self.ip_address = ".".join(str(b) for b in addr)
                    break

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Service updated callback."""
        pass

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Service removed callback."""
        pass


class LaMetricClient:
    """LaMetric Time client."""

    def __init__(self, ip: str | None = None, api_key: str = "", icon: str = "i9218"):
        """
        Initialize LaMetric client.

        Args:
            ip: LaMetric device IP address. None for auto-discovery.
            api_key: LaMetric Local API key.
            icon: Default icon ID.
        """
        self.ip = ip
        self.api_key = api_key
        self.icon = icon
        self.last_notification_id: str | None = None  # Track last notification ID

        # Auto-discover if IP not provided
        if not self.ip:
            discovered_ip = self.discover()
            if discovered_ip:
                self.ip = discovered_ip
                print(f"Discovered LaMetric at {self.ip}")
            else:
                print("Warning: LaMetric device not found via mDNS")

    @staticmethod
    def discover(timeout: float = 5.0) -> str | None:
        """
        Discover LaMetric device via mDNS.

        Args:
            timeout: Discovery timeout in seconds.

        Returns:
            Device IP address if found, None otherwise.
        """
        print("Discovering LaMetric device...")
        zeroconf = Zeroconf()
        listener = LaMetricDiscoveryListener()
        browser = ServiceBrowser(zeroconf, "_lametric._tcp.local.", listener)

        # Wait for discovery
        import time

        start_time = time.time()
        while time.time() - start_time < timeout:
            if listener.ip_address:
                break
            time.sleep(0.1)

        browser.cancel()
        zeroconf.close()

        if listener.ip_address:
            print(f"Found LaMetric at {listener.ip_address}")
        else:
            print("LaMetric device not found")

        return listener.ip_address

    def push_notification(
        self,
        text: str,
        icon: str | None = None,
        priority: str = "info",
        cycles: int = 1,
        lifetime: int | None = None,
        icon_type: str = "none",
    ) -> bool:
        """
        Push notification to LaMetric Time.

        Args:
            text: Text to display.
            icon: Icon ID (e.g., "i9218"). Uses default if None.
            priority: Notification priority ("info", "warning", "critical").
            cycles: Number of display cycles. Set to 0 to keep until manually dismissed.
            lifetime: Display duration in milliseconds. Default is 120000 (2 minutes).
            icon_type: Icon type ("none", "info", "alert").

        Returns:
            True if successful, False otherwise.
        """
        if not self.ip:
            print("Error: LaMetric IP address not set")
            return False

        if not self.api_key:
            print("Error: LaMetric API key not set")
            return False

        icon = icon or self.icon
        url = f"https://{self.ip}:4343/api/v2/device/notifications"

        payload = {
            "priority": priority,
            "icon_type": icon_type,
            "model": {
                "cycles": cycles,
                "frames": [{"icon": icon, "text": text}],
            },
        }

        # Add lifetime if specified (in milliseconds)
        if lifetime is not None:
            payload["lifetime"] = lifetime

        try:
            response = requests.post(
                url,
                json=payload,
                auth=("dev", self.api_key),
                verify=False,  # Self-signed certificate
                timeout=5,
            )
            response.raise_for_status()

            # Store notification ID for later deletion
            result = response.json()
            if "success" in result and "id" in result["success"]:
                self.last_notification_id = result["success"]["id"]

            print(f"Pushed to LaMetric: {text}")
            return True

        except requests.RequestException as e:
            print(f"LaMetric API error: {e}")
            # Print response body for debugging
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    print(f"Error details: {error_detail}")
                except:
                    print(f"Response text: {e.response.text}")
            return False

    def delete_notification(self, notification_id: str | None = None) -> bool:
        """
        Delete notification from LaMetric.

        Args:
            notification_id: Notification ID to delete. Uses last notification if None.

        Returns:
            True if successful, False otherwise.
        """
        if not self.ip:
            print("Error: LaMetric IP address not set")
            return False

        if not self.api_key:
            print("Error: LaMetric API key not set")
            return False

        # Use provided ID or last notification ID
        notif_id = notification_id or self.last_notification_id
        if not notif_id:
            print("No notification ID to delete")
            return False

        url = f"https://{self.ip}:4343/api/v2/device/notifications/{notif_id}"

        try:
            response = requests.delete(
                url,
                auth=("dev", self.api_key),
                verify=False,  # Self-signed certificate
                timeout=5,
            )
            response.raise_for_status()
            print(f"Deleted LaMetric notification: {notif_id}")

            # Clear last notification ID if it was deleted
            if notif_id == self.last_notification_id:
                self.last_notification_id = None

            return True

        except requests.RequestException as e:
            print(f"LaMetric delete error: {e}")
            return False


def main():
    """CLI for LaMetric testing."""
    import argparse
    import os

    parser = argparse.ArgumentParser(description="LaMetric Client CLI")
    parser.add_argument("--discover", action="store_true", help="Discover LaMetric device")
    parser.add_argument("--push", help="Push notification text")
    parser.add_argument("--ip", help="LaMetric IP address")
    parser.add_argument("--api-key", help="LaMetric API key")
    parser.add_argument("--icon", default="i9218", help="Icon ID")
    parser.add_argument("--lifetime", type=int, help="Display duration in milliseconds (e.g., 300000 for 5 min)")
    parser.add_argument("--cycles", type=int, default=1, help="Number of cycles (0 = keep until dismissed)")

    args = parser.parse_args()

    if args.discover:
        ip = LaMetricClient.discover()
        if ip:
            print(f"LaMetric found at: {ip}")
        else:
            print("LaMetric not found")
        return

    if args.push:
        ip = args.ip or os.getenv("LAMETRIC_IP")
        api_key = args.api_key or os.getenv("LAMETRIC_API_KEY")

        if not api_key:
            print("Error: LaMetric API key required")
            print("Set via --api-key or LAMETRIC_API_KEY environment variable")
            return

        client = LaMetricClient(ip=ip, api_key=api_key, icon=args.icon)
        success = client.push_notification(
            args.push,
            cycles=args.cycles,
            lifetime=args.lifetime
        )
        if not success:
            print("Failed to push notification")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
