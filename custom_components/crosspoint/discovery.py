"""Local network discovery of CrossPoint devices (UDP broadcast)."""

from __future__ import annotations

import asyncio
import logging
import re
import socket
from dataclasses import dataclass

from .const import (
    DEFAULT_WS_PORT,
    DISCOVERY_PAYLOAD,
    DISCOVERY_PORT,
    DISCOVERY_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)

# Reply format: "crosspoint (on <hostname>);<ws_port>"
_REPLY_RE = re.compile(r"^crosspoint \(on (?P<hostname>[^)]*)\);(?P<ws_port>\d+)\s*$")


@dataclass(frozen=True, slots=True)
class DiscoveredDevice:
    """A CrossPoint device that answered the discovery broadcast."""

    host: str
    hostname: str
    ws_port: int


def parse_reply(data: bytes, address: str) -> DiscoveredDevice | None:
    """Parse a discovery reply; return None if it is not a CrossPoint reply."""
    match = _REPLY_RE.match(data.decode("utf-8", errors="replace"))
    if not match:
        return None
    return DiscoveredDevice(
        host=address,
        hostname=match["hostname"].strip(),
        ws_port=int(match["ws_port"]) or DEFAULT_WS_PORT,
    )


class _DiscoveryProtocol(asyncio.DatagramProtocol):
    def __init__(self) -> None:
        self.devices: dict[str, DiscoveredDevice] = {}

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        if device := parse_reply(data, addr[0]):
            self.devices[device.host] = device

    def error_received(self, exc: Exception) -> None:
        _LOGGER.debug("Discovery socket error: %s", exc)


async def async_discover(
    timeout: float = DISCOVERY_TIMEOUT,
) -> list[DiscoveredDevice]:
    """Broadcast a discovery request and collect replies for ``timeout`` seconds."""
    loop = asyncio.get_running_loop()
    try:
        transport, protocol = await loop.create_datagram_endpoint(
            _DiscoveryProtocol,
            local_addr=("0.0.0.0", 0),
            family=socket.AF_INET,
            allow_broadcast=True,
        )
    except OSError as err:
        _LOGGER.debug("Cannot open discovery socket: %s", err)
        return []
    try:
        transport.sendto(DISCOVERY_PAYLOAD, ("255.255.255.255", DISCOVERY_PORT))
        await asyncio.sleep(timeout)
    except OSError as err:
        _LOGGER.debug("Discovery broadcast failed: %s", err)
    finally:
        transport.close()
    return sorted(protocol.devices.values(), key=lambda d: d.host)
