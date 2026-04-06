"""Fenix V24 WiFi API client."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
from aiohttp import ClientSession

from .const import API_BASE_URL, API_TIMEOUT, AUTH_URL

_LOGGER = logging.getLogger(__name__)

# Temperature conversion: y = 18x + 320, where x is temp in Celsius and y is API value
TEMP_TO_API = lambda celsius: int(18 * celsius + 320)
API_TO_TEMP = lambda api_value: round((api_value - 320) / 18, 1)


class FenixAPI:
    """Fenix V24 WiFi API client.
    
    Supports:
    - Temperature control via consigne_manuel (current implementation)
    - Programme/schedule control (future enhancement)
    - Mode control: gv_mode, nv_mode (future enhancement)
    """

    def __init__(self, email: str, password: str, session: ClientSession) -> None:
        """Initialize API client."""
        self.email = email
        self.password = password
        self.session = session
        self.access_token: str | None = None
        self.refresh_token: str | None = None

    async def login(self) -> bool:
        """Authenticate and get access tokens."""
        try:
            data = {
                "grant_type": "password",
                "username": self.email,
                "password": self.password,
                "client_id": "app-front",
            }

            response = await self.session.post(
                f"{AUTH_URL}token",
                data=data,
                timeout=aiohttp.ClientTimeout(total=API_TIMEOUT),
            )

            if response.status == 200:
                result = await response.json()
                self.access_token = result.get("access_token")
                self.refresh_token = result.get("refresh_token")
                return self.access_token is not None

            _LOGGER.error("Login failed with status %s", response.status)
            return False
        except aiohttp.ClientError as err:
            _LOGGER.error("Login request error: %s", err)
            return False

    async def _refresh_token_if_needed(self) -> bool:
        """Refresh access token if needed."""
        if not self.refresh_token:
            return await self.login()

        try:
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": "app-front",
            }

            response = await self.session.post(
                f"{AUTH_URL}token",
                data=data,
                timeout=aiohttp.ClientTimeout(total=API_TIMEOUT),
            )

            if response.status == 200:
                result = await response.json()
                self.access_token = result.get("access_token")
                self.refresh_token = result.get("refresh_token", self.refresh_token)
                return True

            return await self.login()
        except aiohttp.ClientError:
            return await self.login()

    async def get_user(self) -> dict[str, Any] | None:
        """Fetch user info and smarthomes list."""
        if not self.access_token:
            if not await self.login():
                return None

        try:
            payload = {
                "token": self.access_token,
                "email": self.email,
                "lang": "en_GB",
            }

            response = await self.session.post(
                f"{API_BASE_URL}user/read/",
                data=payload,
                timeout=aiohttp.ClientTimeout(total=API_TIMEOUT),
                headers={"Authorization": f"Bearer {self.access_token}"},
            )

            if response.status == 200:
                result = await response.json()
                if result.get("code", {}).get("code") == "8":
                    return result.get("data")
            elif response.status == 401:
                await self._refresh_token_if_needed()
                return await self.get_user()

            _LOGGER.error("Failed to fetch user: %s", response.status)
            return None
        except aiohttp.ClientError as err:
            _LOGGER.error("Error fetching user: %s", err)
            return None

    async def get_smarthome(self, smarthome_id: str) -> dict[str, Any] | None:
        """Fetch detailed smarthome data with devices."""
        if not self.access_token:
            if not await self.login():
                return None

        try:
            payload = {
                "token": self.access_token,
                "smarthome_id": smarthome_id,
                "lang": "en_GB",
            }

            response = await self.session.post(
                f"{API_BASE_URL}smarthome/read/",
                data=payload,
                timeout=aiohttp.ClientTimeout(total=API_TIMEOUT),
                headers={"Authorization": f"Bearer {self.access_token}"},
            )

            if response.status == 200:
                result = await response.json()
                if result.get("code", {}).get("code") == "1":
                    return result.get("data")
            elif response.status == 401:
                await self._refresh_token_if_needed()
                return await self.get_smarthome(smarthome_id)

            _LOGGER.error("Failed to fetch smarthome: %s", response.status)
            return None
        except aiohttp.ClientError as err:
            _LOGGER.error("Error fetching smarthome: %s", err)
            return None

    async def set_device_temperature(
        self, smarthome_id: str, device_id: str, temperature: float
    ) -> bool:
        """Set the target temperature for a device."""
        if not self.access_token:
            if not await self.login():
                return False

        try:
            api_temp = TEMP_TO_API(temperature)

            payload = {
                "token": self.access_token,
                "context": "1",
                "smarthome_id": smarthome_id,
                "query[id_device]": device_id,
                "query[consigne_manuel]": str(api_temp),
                "query[gv_mode]": "15",
                "query[nv_mode]": "15",
                "peremption": "20000",
                "lang": "en_GB",
            }

            response = await self.session.post(
                f"{API_BASE_URL}query/push/",
                data=payload,
                timeout=aiohttp.ClientTimeout(total=API_TIMEOUT),
                headers={"Authorization": f"Bearer {self.access_token}"},
            )

            if response.status == 200:
                result = await response.json()
                if result.get("code", {}).get("code") == "8":
                    return True
                _LOGGER.error("Failed to set device temperature, API response: %s", result)
                return False
            elif response.status == 401:
                await self._refresh_token_if_needed()
                return await self.set_device_temperature(
                    smarthome_id, device_id, temperature
                )

            _LOGGER.error("Failed to set device temperature: %s", response.status)
            return False
        except aiohttp.ClientError as err:
            _LOGGER.error("Error setting device temperature: %s", err)
            return False

