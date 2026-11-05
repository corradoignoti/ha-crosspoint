"""Config flow for the CrossPoint integration."""

from __future__ import annotations

import logging
import os
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .api.device import CrossPointDeviceClient
from .api.errors import CrossPointError
from .const import (
    CONF_BOOKS_DIR,
    CONF_LIBRARY_PATH,
    CONF_MODEL,
    CONF_SCAN_INTERVAL,
    CONF_WALLPAPERS_DIR,
    CONF_WS_PORT,
    DEFAULT_BOOKS_DIR,
    DEFAULT_HOST,
    DEFAULT_LIBRARY_PATH,
    DEFAULT_MODEL,
    DEFAULT_SCAN_INTERVAL_MIN,
    DEFAULT_WALLPAPERS_DIR,
    DEFAULT_WS_PORT,
    DOMAIN,
    MODELS,
)
from .discovery import DiscoveredDevice, async_discover

_LOGGER = logging.getLogger(__name__)

MANUAL_ENTRY = "manual"

MODEL_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        options=list(MODELS),
        mode=SelectSelectorMode.DROPDOWN,
        translation_key=CONF_MODEL,
    )
)


def _device_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, DEFAULT_HOST)): (
                TextSelector()
            ),
            vol.Required(
                CONF_MODEL, default=defaults.get(CONF_MODEL, DEFAULT_MODEL)
            ): MODEL_SELECTOR,
        }
    )


def _library_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_LIBRARY_PATH,
                default=defaults.get(CONF_LIBRARY_PATH, DEFAULT_LIBRARY_PATH),
            ): TextSelector(),
            vol.Required(
                CONF_BOOKS_DIR, default=defaults.get(CONF_BOOKS_DIR, DEFAULT_BOOKS_DIR)
            ): TextSelector(),
            vol.Required(
                CONF_WALLPAPERS_DIR,
                default=defaults.get(CONF_WALLPAPERS_DIR, DEFAULT_WALLPAPERS_DIR),
            ): TextSelector(),
        }
    )


def _guess_model(status: dict[str, Any]) -> str | None:
    """Map the firmware ``device`` field to a known model, when recognizable."""
    device = str(status.get("device", "")).lower().replace("-", " ")
    if "x3" in device:
        return "xteink_x3"
    if "x4" in device:
        return "xteink_x4"
    if "cross share" in device or "crossshare" in device:
        return "cross_share"
    return None


async def _async_probe(hass: HomeAssistant, host: str, ws_port: int) -> dict | None:
    """Return the device status, or None if the device is not reachable now."""
    client = CrossPointDeviceClient(
        async_get_clientsession(hass), host, ws_port=ws_port
    )
    try:
        return await client.get_status()
    except CrossPointError as err:
        _LOGGER.debug("CrossPoint at %s not reachable: %s", host, err)
        return None


def _validate_library(hass: HomeAssistant, user_input: dict[str, Any]) -> str | None:
    """Validate the library folder and create its subfolders (runs in executor).

    Return an error key, or None when valid.
    """
    root = os.path.abspath(user_input[CONF_LIBRARY_PATH])
    if not hass.config.is_allowed_path(root):
        return "path_not_allowed"
    if not os.path.isdir(root):
        return "path_not_found"
    for key in (CONF_BOOKS_DIR, CONF_WALLPAPERS_DIR):
        sub = user_input[key].strip().strip("/")
        if not sub or ".." in sub.split("/"):
            return "invalid_subfolder"
        os.makedirs(os.path.join(root, sub), exist_ok=True)
    return None


def _normalize_library(user_input: dict[str, Any]) -> dict[str, Any]:
    return {
        CONF_LIBRARY_PATH: os.path.abspath(user_input[CONF_LIBRARY_PATH]),
        CONF_BOOKS_DIR: user_input[CONF_BOOKS_DIR].strip().strip("/"),
        CONF_WALLPAPERS_DIR: user_input[CONF_WALLPAPERS_DIR].strip().strip("/"),
    }


class CrossPointConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for CrossPoint."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered: dict[str, DiscoveredDevice] = {}
        self._device: dict[str, Any] = {}
        self._unconfirmed_host: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow handler."""
        return CrossPointOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Search the network, then let the user pick a device or type one."""
        configured = {
            entry.data[CONF_HOST].lower() for entry in self._async_current_entries()
        }
        self._discovered = {
            device.host: device
            for device in await async_discover()
            if device.host.lower() not in configured
            and device.hostname.lower() not in configured
        }
        if not self._discovered:
            return await self.async_step_device()
        return await self.async_step_pick()

    async def async_step_pick(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose one of the discovered devices."""
        if user_input is not None:
            choice = user_input[CONF_HOST]
            if choice == MANUAL_ENTRY:
                return await self.async_step_device()
            device = self._discovered[choice]
            self._device[CONF_WS_PORT] = device.ws_port
            return await self.async_step_device({CONF_HOST: device.host}, prefill=True)

        options = [
            SelectOptionDict(value=d.host, label=f"{d.hostname} ({d.host})")
            for d in self._discovered.values()
        ]
        options.append(SelectOptionDict(value=MANUAL_ENTRY, label=MANUAL_ENTRY))
        return self.async_show_form(
            step_id="pick",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            mode=SelectSelectorMode.LIST,
                            translation_key="pick",
                        )
                    )
                }
            ),
        )

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None, *, prefill: bool = False
    ) -> ConfigFlowResult:
        """Device address and model.

        The reader is often offline (its web server only runs in File Transfer
        mode), so an unreachable device is accepted after a second confirmation.
        """
        errors: dict[str, str] = {}
        ws_port = self._device.get(CONF_WS_PORT, DEFAULT_WS_PORT)
        defaults = dict(user_input or {})

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            defaults[CONF_HOST] = host
            await self.async_set_unique_id(host.lower())
            self._abort_if_unique_id_configured()

            status = await _async_probe(self.hass, host, ws_port)
            if prefill and status and (model := _guess_model(status)):
                defaults[CONF_MODEL] = model

            if prefill:
                pass  # first display for a discovered device: let the user confirm
            elif status is not None or self._unconfirmed_host == host:
                self._device.update(
                    {
                        CONF_HOST: host,
                        CONF_MODEL: user_input[CONF_MODEL],
                        CONF_WS_PORT: ws_port,
                    }
                )
                return await self.async_step_library()
            else:
                self._unconfirmed_host = host
                errors["base"] = "cannot_connect_confirm"

        return self.async_show_form(
            step_id="device",
            data_schema=_device_schema(defaults),
            errors=errors,
        )

    async def async_step_library(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Shared library folder and its subfolders."""
        errors: dict[str, str] = {}
        if user_input is not None:
            error = await self.hass.async_add_executor_job(
                _validate_library, self.hass, user_input
            )
            if error is None:
                return self.async_create_entry(
                    title=f"CrossPoint ({self._device[CONF_HOST]})",
                    data={**self._device, **_normalize_library(user_input)},
                    options={CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL_MIN},
                )
            errors["base"] = error

        return self.async_show_form(
            step_id="library",
            data_schema=_library_schema(user_input or {}),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change device address, model or library folders."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            await self.async_set_unique_id(host.lower())
            if host.lower() != entry.unique_id:
                self._abort_if_unique_id_configured()
            error = await self.hass.async_add_executor_job(
                _validate_library, self.hass, user_input
            )
            if error is None:
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=host.lower(),
                    title=f"CrossPoint ({host})",
                    data_updates={
                        CONF_HOST: host,
                        CONF_MODEL: user_input[CONF_MODEL],
                        **_normalize_library(user_input),
                    },
                )
            errors["base"] = error

        defaults = {**entry.data, **(user_input or {})}
        schema = vol.Schema(
            {
                **_device_schema(defaults).schema,
                **_library_schema(defaults).schema,
            }
        )
        return self.async_show_form(
            step_id="reconfigure", data_schema=schema, errors=errors
        )


class CrossPointOptionsFlow(OptionsFlow):
    """Runtime options for CrossPoint."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(
                data={CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL])}
            )
        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_MIN
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCAN_INTERVAL, default=current): NumberSelector(
                        NumberSelectorConfig(
                            min=1,
                            max=1440,
                            step=1,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="min",
                        )
                    )
                }
            ),
        )
