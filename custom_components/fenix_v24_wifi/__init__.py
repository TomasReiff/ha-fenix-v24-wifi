"""The Fenix V24 WiFi integration."""

from __future__ import annotations

import logging

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
)
from .coordinator import FenixDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.CLIMATE, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Fenix V24 WiFi from a config entry."""
    interval_seconds = entry.options.get(
        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS
    )
    coordinator = FenixDataUpdateCoordinator(
        hass,
        entry.data[CONF_EMAIL],
        entry.data[CONF_PASSWORD],
        scan_interval=timedelta(seconds=interval_seconds),
    )

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = {
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator: FenixDataUpdateCoordinator = entry.runtime_data["coordinator"]
        await coordinator.close()

    return unload_ok
