"""Binary sensor platform for Fenix V24 WiFi."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import async_get as async_get_device_registry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FenixDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor entities from a config entry."""
    coordinator: FenixDataUpdateCoordinator = entry.runtime_data["coordinator"]
    device_registry = async_get_device_registry(hass)

    entities: list[BinarySensorEntity] = []

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
                FenixHeatingBinarySensor(
                    coordinator,
                    smarthome_id,
                    device_id,
                    device_data["info"],
                    device_data.get("name", device_id),
                    entry.entry_id,
                )
            )

    async_add_entities(entities)


class FenixHeatingBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for Fenix heating status."""

    _attr_icon = "mdi:fire"

    def __init__(
        self,
        coordinator: FenixDataUpdateCoordinator,
        smarthome_id: str,
        device_id: str,
        device_info: dict[str, Any],
        zone_name: str,
        entry_id: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._smarthome_id = smarthome_id
        self._device_id = device_id
        self._entry_id = entry_id
        self._device_info = device_info

        self._attr_unique_id = f"{smarthome_id}_{device_id}_heating"
        self._attr_name = f"{zone_name} Heating"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._smarthome_id}_{self._device_id}")},
            name=self._attr_name.replace(" Heating", ""),
            manufacturer="Fenix",
            model="V24 WiFi",
            via_device=(DOMAIN, self._smarthome_id),
        )

    @property
    def is_on(self) -> bool | None:
        """Return True if heating is currently active."""
        data = self.coordinator.data or {}
        smarthomes = data.get("smarthomes", {})
        device_data = (
            smarthomes.get(self._smarthome_id, {}).get("devices", {})
        )
        device = device_data.get(self._device_id, {})

        heating_state = device.get("heating_state")
        
        # If no heating_state data, return unavailable
        if heating_state is None or heating_state == "":
            return None

        # heating_state > 0 means heating is active
        # 0 = idle, 1-15 = heating with varying intensities
        try:
            state_value = int(heating_state)
            return state_value > 0
        except (ValueError, TypeError):
            return None
