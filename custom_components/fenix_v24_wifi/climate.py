"""Climate platform for Fenix V24 WiFi."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import async_get as async_get_device_registry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import TEMP_TO_API
from .const import DOMAIN, MAX_TEMP, MIN_TEMP, SCAN_INTERVAL, TEMP_PRECISION
from .coordinator import FenixDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up climate entities from a config entry."""
    coordinator: FenixDataUpdateCoordinator = entry.runtime_data["coordinator"]
    device_registry = async_get_device_registry(hass)

    entities: list[ClimateEntity] = []

    data = coordinator.data or {}
    smarthomes = data.get("smarthomes", {})

    # Register installation devices
    for smarthome_id, smarthome_data in smarthomes.items():
        installation_name = smarthome_data.get("name", f"Installation {smarthome_id}")
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, smarthome_id)},
            name=installation_name,
            manufacturer="Fenix",
            model="Installation",
        )

        devices = smarthome_data.get("devices", {})
        for device_id, device_data in devices.items():
            entities.append(
                FenixClimate(
                    coordinator,
                    smarthome_id,
                    device_id,
                    device_data["info"],
                    device_data.get("name", device_id),
                    entry.entry_id,
                )
            )

    async_add_entities(entities)


class FenixClimate(CoordinatorEntity, ClimateEntity):
    """Fenix V24 WiFi climate entity."""

    _attr_hvac_modes = [HVACMode.HEAT]
    _attr_max_temp = MAX_TEMP
    _attr_min_temp = MIN_TEMP
    _attr_target_temperature_step = TEMP_PRECISION
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE

    def __init__(
        self,
        coordinator: FenixDataUpdateCoordinator,
        smarthome_id: str,
        device_id: str,
        device_info: dict[str, Any],
        zone_name: str,
        entry_id: str,
    ) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self._smarthome_id = smarthome_id
        self._device_id = device_id
        self._entry_id = entry_id
        self._device_info = device_info

        self._attr_unique_id = f"{smarthome_id}_{device_id}"
        self._attr_name = zone_name
        self._pending_target_temp: float | None = None
        self._pending_until: datetime | None = None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            name=self._attr_name,
            manufacturer="Fenix",
            model="V24 WiFi",
            via_device=(DOMAIN, self._smarthome_id),
        )

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        data = self.coordinator.data or {}
        smarthomes = data.get("smarthomes", {})
        device_data = (
            smarthomes.get(self._smarthome_id, {}).get("devices", {})
        )
        return device_data.get(self._device_id, {}).get("current_temperature")

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature, using pending value during cooldown."""
        if self._pending_until is not None and datetime.now() < self._pending_until:
            return self._pending_target_temp
        data = self.coordinator.data or {}
        smarthomes = data.get("smarthomes", {})
        device_data = (
            smarthomes.get(self._smarthome_id, {}).get("devices", {})
        )
        return device_data.get(self._device_id, {}).get("target_temperature")

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        return HVACMode.HEAT

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set the target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        if self.coordinator.api is None:
            _LOGGER.error("API not initialized for device %s", self._device_id)
            return

        success = await self.coordinator.api.set_device_temperature(
            self._smarthome_id, self._device_id, temperature
        )
        if success:
            self._pending_target_temp = float(temperature)
            self._pending_until = datetime.now() + SCAN_INTERVAL * 2
            self.async_write_ha_state()
        else:
            _LOGGER.error(
                "Failed to set temperature for device %s", self._device_id
            )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode (currently only HEAT is supported)."""
        if hvac_mode != HVACMode.HEAT:
            _LOGGER.error("Unsupported HVAC mode: %s", hvac_mode)
            return

        if self.coordinator.api is not None:
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("API not initialized for device %s", self._device_id)
