"""Sensor platform for Fenix V24 WiFi."""

from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfPower, UnitOfTemperature
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
            power_w = int(entry.options.get(f"power_{device_id}", device_data.get("power_w", 0)))

            entities.append(FenixRatedPowerSensor(coordinator, smarthome_id, device_id, zone_name, power_w, entry))
            entities.append(FenixPowerSensor(coordinator, smarthome_id, device_id, zone_name, power_w, entry))
            entities.append(FenixEnergySensor(coordinator, smarthome_id, device_id, zone_name, power_w, entry))

            # If a distinct floor temperature probe value is reported, add dedicated floor probe sensor
            if device_data.get("floor_temperature") is not None:
                entities.append(FenixFloorTemperatureSensor(coordinator, smarthome_id, device_id, zone_name))

    async_add_entities(entities)


class FenixRatedPowerSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing the static rated power (W) configured for the zone."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "rated_power"

    def __init__(
        self,
        coordinator: FenixDataUpdateCoordinator,
        smarthome_id: str,
        device_id: str,
        zone_name: str,
        power_w: int,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the rated power sensor."""
        super().__init__(coordinator)
        self._smarthome_id = smarthome_id
        self._device_id = device_id
        self._entry = entry
        self._default_power_w = power_w
        self._attr_unique_id = f"{smarthome_id}_{device_id}_rated_power"
        self._attr_has_entity_name = True

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._smarthome_id}_{self._device_id}")},
            via_device=(DOMAIN, self._smarthome_id),
        )

    @property
    def native_value(self) -> int | None:
        """Return the rated power (W) from options override or cloud API."""
        override = self._entry.options.get(f"power_{self._device_id}")
        if override is not None:
            return int(override)

        device = (
            (self.coordinator.data or {})
            .get("smarthomes", {})
            .get(self._smarthome_id, {})
            .get("devices", {})
            .get(self._device_id, {})
        )
        if not device:
            return self._default_power_w
        return device.get("power_w", self._default_power_w)


class FenixPowerSensor(CoordinatorEntity, SensorEntity):
    """Power sensor showing actual consumption: rated power when heating is on, 0 W when off."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "power"

    def __init__(
        self,
        coordinator: FenixDataUpdateCoordinator,
        smarthome_id: str,
        device_id: str,
        zone_name: str,
        power_w: int,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the power sensor."""
        super().__init__(coordinator)
        self._smarthome_id = smarthome_id
        self._device_id = device_id
        self._entry = entry
        self._default_power_w = power_w
        self._attr_unique_id = f"{smarthome_id}_{device_id}_power"
        self._attr_has_entity_name = True

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._smarthome_id}_{self._device_id}")},
            via_device=(DOMAIN, self._smarthome_id),
        )

    def _get_rated_power(self, device: dict) -> int:
        override = self._entry.options.get(f"power_{self._device_id}")
        if override is not None:
            return int(override)
        return device.get("power_w", self._default_power_w)

    @property
    def native_value(self) -> int | None:
        """Return rated power (W) when heating is on, 0 W when off."""
        device = (
            (self.coordinator.data or {})
            .get("smarthomes", {})
            .get(self._smarthome_id, {})
            .get("devices", {})
            .get(self._device_id, {})
        )
        if not device:
            return None
        try:
            if int(device.get("heating_state", "0")) > 0:
                return self._get_rated_power(device)
        except (ValueError, TypeError):
            pass
        return 0


class FenixEnergySensor(CoordinatorEntity, RestoreSensor):
    """Energy sensor that accumulates kWh when heating is active."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_translation_key = "energy"

    def __init__(
        self,
        coordinator: FenixDataUpdateCoordinator,
        smarthome_id: str,
        device_id: str,
        zone_name: str,
        power_w: int,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the energy sensor."""
        super().__init__(coordinator)
        self._smarthome_id = smarthome_id
        self._device_id = device_id
        self._entry = entry
        self._default_power_w = power_w
        self._attr_unique_id = f"{smarthome_id}_{device_id}_energy"
        self._attr_has_entity_name = True
        self._accumulated_kwh: float = 0.0
        self._last_update: datetime | None = None

    async def async_added_to_hass(self) -> None:
        """Restore accumulated energy from last known state on HA restart."""
        await super().async_added_to_hass()
        if (last_data := await self.async_get_last_sensor_data()) is not None:
            try:
                self._accumulated_kwh = float(last_data.native_value or 0.0)
                return
            except (ValueError, TypeError):
                pass

        if (last_state := await self.async_get_last_state()) is not None:
            try:
                if last_state.state not in (None, "unknown", "unavailable"):
                    self._accumulated_kwh = float(last_state.state)
            except (ValueError, TypeError):
                self._accumulated_kwh = 0.0

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._smarthome_id}_{self._device_id}")},
            via_device=(DOMAIN, self._smarthome_id),
        )

    def _get_rated_power(self, device: dict) -> int:
        override = self._entry.options.get(f"power_{self._device_id}")
        if override is not None:
            return int(override)
        return device.get("power_w", self._default_power_w)

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
            power_w = self._get_rated_power(device)
            try:
                if int(heating_state) > 0 and power_w > 0:
                    elapsed_seconds = (now - self._last_update).total_seconds()
                    # Guard against huge elapsed time on HA restarts (cap at 15 minutes)
                    if 0 < elapsed_seconds <= 900:
                        elapsed_hours = elapsed_seconds / 3600
                        self._accumulated_kwh += (power_w / 1000) * elapsed_hours
            except (ValueError, TypeError):
                pass

        self._last_update = now
        super()._handle_coordinator_update()

    @property
    def native_value(self) -> float:
        """Return total accumulated energy in kWh."""
        return round(self._accumulated_kwh, 4)


class FenixFloorTemperatureSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing dedicated floor probe temperature."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "floor_temperature"

    def __init__(
        self,
        coordinator: FenixDataUpdateCoordinator,
        smarthome_id: str,
        device_id: str,
        zone_name: str,
    ) -> None:
        """Initialize the floor temperature sensor."""
        super().__init__(coordinator)
        self._smarthome_id = smarthome_id
        self._device_id = device_id
        self._attr_unique_id = f"{smarthome_id}_{device_id}_floor_temperature"
        self._attr_has_entity_name = True

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._smarthome_id}_{self._device_id}")},
            via_device=(DOMAIN, self._smarthome_id),
        )

    @property
    def native_value(self) -> float | None:
        """Return the floor probe temperature."""
        device = (
            (self.coordinator.data or {})
            .get("smarthomes", {})
            .get(self._smarthome_id, {})
            .get("devices", {})
            .get(self._device_id, {})
        )
        if not device:
            return None
        return device.get("floor_temperature")
