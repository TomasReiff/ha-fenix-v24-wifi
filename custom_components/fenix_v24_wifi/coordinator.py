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
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Fenix V24 WiFi",
            update_interval=SCAN_INTERVAL,
        )
        self.api: FenixAPI | None = None
        self.email = email
        self.password = password

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        if self.api is None:
            session = async_get_clientsession(self.hass)
            self.api = FenixAPI(self.email, self.password, session)

        try:
            user_data = await self.api.get_user()
            if not user_data:
                raise UpdateFailed("Failed to fetch user data")

            smarthomes_list = user_data.get("smarthomes", [])
            if not smarthomes_list:
                raise UpdateFailed("No smarthomes found")

            data: dict[str, Any] = {"smarthomes": {}}

            for smarthome in smarthomes_list:
                smarthome_id = smarthome.get("smarthome_id")
                if not smarthome_id:
                    continue

                smarthome_data = await self.api.get_smarthome(smarthome_id)
                if not smarthome_data:
                    _LOGGER.warning(
                        "Failed to fetch smarthome %s, skipping", smarthome_id
                    )
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
                    current_temp = device.get("temperature_air")
                    target_temp = device.get("consigne_manuel")

                    # heating_up: "1" = heating active, "0" = idle
                    heating_up = device.get("heating_up", "0")

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
                        "target_temperature": (
                            API_TO_TEMP(int(target_temp)) if target_temp else None
                        ),
                        "heating_state": heating_up,
                    }

                data["smarthomes"][smarthome_id] = {
                    "name": installation_name,
                    "location": location,
                    "info": smarthome,
                    "devices": devices,
                }

            return data

        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Error updating data: {err}") from err

    async def close(self) -> None:
        """Close the API session (managed by Home Assistant)."""
        # Session is managed by Home Assistant, no manual cleanup needed
        pass
