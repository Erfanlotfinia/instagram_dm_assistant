from __future__ import annotations

import ipaddress
import logging

from fastapi import Request

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


def _trusted_proxy_networks(settings: Settings) -> list[ipaddress._BaseNetwork]:
    networks: list[ipaddress._BaseNetwork] = []
    for cidr in settings.trusted_proxy_cidrs:
        value = cidr.strip()
        if not value:
            continue
        try:
            networks.append(ipaddress.ip_network(value, strict=False))
        except ValueError:
            logger.warning("Ignoring invalid trusted proxy CIDR: %s", value)
    return networks


def _is_trusted_proxy(host: str, settings: Settings) -> bool:
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return any(address in network for network in _trusted_proxy_networks(settings))


def resolve_client_ip(request: Request, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    client_host = request.client.host if request.client and request.client.host else "unknown"
    if _is_trusted_proxy(client_host, settings):
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
    return client_host


client_identifier = resolve_client_ip
