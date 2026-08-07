"""Host normalization and origin URL building for mwapi requests."""

from __future__ import annotations

from urllib.parse import urlparse


def normalize_host(host: str) -> str:
    """Return hostname or IP suitable for HTTP requests.

    Accepts plain hostnames (e.g. magewell.local), IPv4/IPv6 literals, or pasted
    http(s):// URLs.
    """
    host = host.strip().rstrip("/")
    if "://" in host:
        parsed = urlparse(host)
        if parsed.hostname:
            return parsed.hostname
    return host


def build_origin_url(host: str, port: int, use_ssl: bool) -> str:
    """Build scheme + host + port origin for mwapi (no path)."""
    host = normalize_host(host)
    scheme = "https" if use_ssl else "http"
    if (use_ssl and port == 443) or (not use_ssl and port == 80):
        return f"{scheme}://{host}"
    return f"{scheme}://{host}:{port}"


def connection_unique_id(host: str, port: int, use_ssl: bool) -> str:
    """Stable config-entry key for a host/port/SSL combination."""
    return f"{normalize_host(host).lower()}-{port}-{use_ssl}"
