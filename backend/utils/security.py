import socket
import ipaddress
import os
from urllib.parse import urlparse

# Set allow_local to True for local environment testing
ALLOW_LOCAL_NETWORKS = os.getenv("ALLOW_LOCAL_NETWORKS", "true").lower() in ("true", "1", "yes")

def validate_url(url: str, allow_local: bool = ALLOW_LOCAL_NETWORKS) -> bool:
    """
    Validates a URL to prevent SSRF (Server-Side Request Forgery).
    Checks that the URL structure is valid, the scheme is http/https, 
    and the target IP is not a private/reserved network address (unless allowed).
    """
    try:
        if not url:
            return False

        parsed_url = urlparse(url)
        if parsed_url.scheme not in ("http", "https"):
            return False

        hostname = parsed_url.hostname
        if not hostname:
            return False

        # Resolve hostname to IP address
        try:
            ip_info = socket.getaddrinfo(hostname, None)
            # Check all resolved IPs (IPv4 and IPv6)
            for item in ip_info:
                ip_str = item[4][0]
                ip = ipaddress.ip_address(ip_str)

                # Local loopbacks are allowed if allow_local is True
                if ip.is_loopback:
                    if allow_local:
                        continue
                    else:
                        return False

                # Check for other private or link-local networks
                if ip.is_private or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                    if allow_local:
                        continue
                    else:
                        return False
        except socket.gaierror:
            # Hostname could not be resolved, potentially invalid URL or domain
            return False

        return True
    except Exception:
        return False

def sanitize_input(text: str) -> str:
    """Sanitizes text to avoid basic injection attempts."""
    if not text:
        return ""
    # Strip potential control characters
    return "".join(c for c in text if c.isprintable() or c in ("\n", "\r", "\t"))
