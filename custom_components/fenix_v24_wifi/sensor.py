"""Sensor platform for Fenix V24 WiFi."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import async_get as async_get_device_registry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FenixDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities from a config entry."""
    coordinator: FenixDataUpdateCoordinator = entry.runtime_data["coordinator"]
    device_registry = async_get_device_registry(hass)

    entities: list[SensorEntity] = []

    data = coordinator.data or {}
    smarthomes = data.get("smarthomes", {})

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
            zone_name = device_data.get("name", device_id)
            power_w = device_data.get("power_w", 0)

            entities.append(FenixPowerSensor(coordinator, smarthome_id, device_id, zone_name, power_w))
            entities.append(FenixEnergySensor(coordinator, smarthome_id, device_id, zone_name, power_w))

    async_add_entities(entities)


class FenixPowerSensor(CoordinatorEntity, SensorEntity):
    """Power sensor showing the rated zone power (W) from the cloud API."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: FenixDataUpdateCoordinator,
        smarthome_id: str,
        device_id: str,
        zone_name: str,
        power_w: int,
    ) -> None:
        """Initialize the power sensor."""
        super().__init__(coordinator)
        self._smarthome_id = smarthome_id
        self._device_id = device_id
        self._attr_unique_id = f"{smarthome_id}_{device_id}_power"
        self._attr_name = f"{zone_name} Power"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._smarthome_id}_{self._device_id}")},
            via_device=(DOMAIN, self._smarthome_id),
        )

    @property
    def native_value(self) -> int | None:
        """Return the rated power (W) from cloud API - always the configured wattage."""
        device = (
            (self.coordinator.data or {})
            .get("smarthomes", {})
            .get(self._smarthome_id, {})
            .get("devices", {})
            .get(self._device_id, {})
        )
        if not device:
            return None
        return device.get("power_w", 0)


class FenixEnergySensor(CoordinatorEntity, RestoreSensor):
    """Energy sensor that accumulates kWh when heating is active."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(
        self,
        coordinator: FenixDataUpdateCoordinator,
        smarthome_id: str,
        device_id: str,
        zone_name: str,
        power_w: int,
    ) -> None:
        """Initialize the energy sensor."""
        super().__init__(coordinator)
        self._smarthome_id = smarthome_id
        self._device_id = device_id
        self._attr_unique_id = f"{smarthome_id}_{device_id}_energy"
        self._attr_name = f"{zone_name} Energy"
        self._accumulated_kwh: float = 0.0
        self._last_update: datetime | None = None

    async def async_added_to_hass(self) -> None:
        """Restore accumulated energy from last known state on HA restart."""
        await super().async_added_to_hass()
        if (last_data := await self.async_get_last_sensor_data()) is not None:
            try:
                self._accumulated_kwh = float(last_data.native_value or 0.0)
            except (ValueError, TypeError):
                self._accumulated_kwh = 0.0

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._smarthome_id}_{self._device_id}")},
            via_device=(DOMAIN, self._smarthome_id),
        )

    def _handle_coordinator_update(self) -> None:
        """Accumulate energy when heating is active on each coordinator update."""
        now = datetime.now()
        device = (
            (self.coordinator.data or {})
            .get("smarthomes", {})
            .get(self._smarthome_id, {})
            .get("devices", {})
            .get(self._device_id, {})
        )

        if device and self._last_update is not None:
            heating_state = device.get("heating_state", "0")
            power_w = device.get("power_w", 0)
            try:
                if int(heating_state) > 0 and power_w > 0:
                    elapsed_hours = (now - self._last_update).total_seconds() / 3600
                    self._accumulated_kwh += (power_w / 1000) * elapsed_hours
            except (ValueError, TypeError):
                pass

        self._last_update = now
        super()._handle_coordinator_update()

    @property
    def native_value(self) -> float:
        """Return total accumulated energy in kWh."""
        return round(self._accumulated_kwh, 4)
