"""Validate outbound HTTP(S) URLs to reduce SSRF risk."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


class UnsafeUrlError(ValueError):
    """Raised when a URL is rejected for safety reasons."""


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address, *, allow_private: bool) -> bool:
    if ip.is_unspecified or ip.is_multicast or ip.is_reserved:
        return True
    if ip.is_link_local:
        return True
    # Cloud metadata / CGNAT-style ranges often used in SSRF
    if isinstance(ip, ipaddress.IPv4Address):
        if ip in ipaddress.ip_network("169.254.0.0/16"):
            return True
        if ip in ipaddress.ip_network("100.64.0.0/10"):
            return True
    if not allow_private and (ip.is_private or ip.is_loopback):
        return True
    return False


def _resolve_host_ips(hostname: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    try:
        infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeUrlError(f"Cannot resolve host: {hostname}") from exc
    ips: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for info in infos:
        addr = info[4][0]
        try:
            ips.append(ipaddress.ip_address(addr))
        except ValueError:
            continue
    if not ips:
        raise UnsafeUrlError(f"Cannot resolve host: {hostname}")
    return ips


def validate_http_url(url: str, *, allow_private: bool = False) -> str:
    """Return a cleaned http(s) URL or raise UnsafeUrlError."""
    cleaned = (url or "").strip()
    if not cleaned:
        raise UnsafeUrlError("URL is empty")
    parsed = urlparse(cleaned)
    if parsed.scheme not in ("http", "https"):
        raise UnsafeUrlError("URL must use http or https")
    if not parsed.hostname:
        raise UnsafeUrlError("URL must include a hostname")
    if parsed.username or parsed.password:
        raise UnsafeUrlError("URL must not include credentials")

    host = parsed.hostname
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None

    if literal is not None:
        if _is_blocked_ip(literal, allow_private=allow_private):
            raise UnsafeUrlError("URL host is not allowed")
    else:
        for ip in _resolve_host_ips(host):
            if _is_blocked_ip(ip, allow_private=allow_private):
                raise UnsafeUrlError("URL host resolves to a blocked address")

    return cleaned
