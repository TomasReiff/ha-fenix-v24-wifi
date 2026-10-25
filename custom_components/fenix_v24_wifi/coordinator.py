"""Data update coordinator for Fenix V24 WiFi."""

from __future__ import annotations

import logging

from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import FenixAPI, API_TO_TEMP
from .const import SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class FenixDataUpdateCoordinator(DataUpdateCoordinator):
    """Data update coordinator for Fenix V24 WiFi."""

    def __init__(
        self,
        hass: HomeAssistant,
        email: str,
        password: str,
        scan_interval: timedelta = SCAN_INTERVAL,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Fenix V24 WiFi",
            update_interval=scan_interval,
        )
        self.api: FenixAPI | None = None
        self.email = email
        self.password = password
        self._smarthomes_list: list[dict[str, Any]] = []

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        if self.api is None:
            session = async_get_clientsession(self.hass)
            self.api = FenixAPI(self.email, self.password, session)

        try:
            if not self._smarthomes_list:
                user_data = await self.api.get_user()
                if not user_data:
                    if self.data and self.data.get("smarthomes"):
                        _LOGGER.warning(
                            "Failed to fetch user data; keeping cached state"
                        )
                        return self.data
                    raise UpdateFailed("Failed to fetch user data")

                self._smarthomes_list = user_data.get("smarthomes", [])
                if not self._smarthomes_list:
                    raise UpdateFailed("No smarthomes found")

            data: dict[str, Any] = {"smarthomes": {}}

            for smarthome in self._smarthomes_list:
                smarthome_id = smarthome.get("smarthome_id")
                if not smarthome_id:
                    continue

                smarthome_data = await self.api.get_smarthome(smarthome_id)
                if not smarthome_data:
                    _LOGGER.warning(
                        "Failed to fetch smarthome %s from cloud API, using cached state if available",
                        smarthome_id,
                    )
                    if self.data and smarthome_id in self.data.get("smarthomes", {}):
                        data["smarthomes"][smarthome_id] = self.data["smarthomes"][smarthome_id]
                    continue

                installation_name = smarthome.get("label") or f"Installation {smarthome_id}"
                location = smarthome.get("address_position") or ""

                devices_list = smarthome_data.get("devices", [])
                zones_list = smarthome_data.get("zones", [])
                devices: dict[str, Any] = {}

                # Build num_zone -> zone_label mapping from zones list
                zone_name_map: dict[str, str] = {}
                for zone in zones_list:
                    num_zone = str(zone.get("num_zone", ""))
                    zone_label = zone.get("zone_label") or f"Zone {num_zone}"
                    zone_name_map[num_zone] = zone_label

                for device in devices_list:
                    device_id = device.get("id_device")
                    if not device_id:
                        continue

                    # Convert temperature values from API format to Celsius
                    current_temp = (
                        device.get("temperature_air")
                        if device.get("temperature_air") is not None
                        else device.get("temperature_sol")
                    )
                    floor_temp = device.get("temperature_sol")
                    target_temp = device.get("consigne_manuel")

                    # heating_up: "1" = heating active, "0" = idle
                    heating_up = device.get("heating_up", "0")

                    # Modes and status
                    gv_mode = str(device.get("gv_mode", "15"))
                    nv_mode = str(device.get("nv_mode", "15"))
                    error_code = int(device.get("error_code", 0))

                    # Power in Watts from API
                    puissance_app = device.get("puissance_app")
                    power_w = int(puissance_app) if puissance_app else 0

                    # Zone name from zones list matched by num_zone
                    num_zone = str(device.get("num_zone", ""))
                    zone_name = zone_name_map.get(num_zone) or device.get("nom_appareil") or device.get("label_interface") or device_id

                    devices[device_id] = {
                        "info": device,
                        "name": zone_name,
                        "power_w": power_w,
                        "current_temperature": (
                            API_TO_TEMP(int(current_temp)) if current_temp else None
                        ),
                        "floor_temperature": (
                            API_TO_TEMP(int(floor_temp)) if floor_temp else None
                        ),
                        "target_temperature": (
                            API_TO_TEMP(int(target_temp)) if target_temp else None
                        ),
                        "heating_state": heating_up,
                        "gv_mode": gv_mode,
                        "nv_mode": nv_mode,
                        "error_code": error_code,
                    }

                data["smarthomes"][smarthome_id] = {
                    "name": installation_name,
                    "location": location,
                    "info": smarthome,
                    "devices": devices,
                }

            if not data["smarthomes"]:
                if self.data and self.data.get("smarthomes"):
                    _LOGGER.warning(
                        "All smarthome updates failed; retaining cached state"
                    )
                    self._smarthomes_list = []
                    return self.data
                raise UpdateFailed("Failed to fetch any smarthome data")

            return data

        except aiohttp.ClientError as err:
            self._smarthomes_list = []
            if self.data and self.data.get("smarthomes"):
                _LOGGER.warning(
                    "Network error communicating with Fenix API: %s; retaining cached state",
                    err,
                )
                return self.data
            raise UpdateFailed(f"Error communicating with API: {err}") from err
        except Exception as err:
            self._smarthomes_list = []
            if self.data and self.data.get("smarthomes"):
                _LOGGER.warning(
                    "Error updating Fenix data: %s; retaining cached state",
                    err,
                )
                return self.data
            raise UpdateFailed(f"Error updating data: {err}") from err

    async def close(self) -> None:
        """Close the API session (managed by Home Assistant)."""
        # Session is managed by Home Assistant, no manual cleanup needed
        pass
