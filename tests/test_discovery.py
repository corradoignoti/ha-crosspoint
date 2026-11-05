"""Tests for UDP discovery reply parsing."""

from custom_components.crosspoint.discovery import parse_reply


def test_parse_valid_reply():
    device = parse_reply(b"crosspoint (on crosspoint.local);81", "192.168.1.20")
    assert device is not None
    assert device.host == "192.168.1.20"
    assert device.hostname == "crosspoint.local"
    assert device.ws_port == 81


def test_parse_foreign_reply():
    assert parse_reply(b"something else", "192.168.1.20") is None
