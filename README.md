# Fenix V24 WiFi — Home Assistant Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)

Home Assistant custom integration for the **Fenix V24 WiFi** thermostat, controlled via the Fenix cloud API.

## Features

- 🌡️ **Climate control** — view and set target temperature, switch HVAC mode (Heat / Off), and control preset modes (Comfort, Eco, Frost Protection, Boost, Manual)
- 🔥 **Live heating state** — dynamic `hvac_action` (Heating vs Idle) and binary sensor
- 🪫 **Battery warning** — binary sensor alerting on low battery for wireless room thermostats
- ⚡ **Rated Power sensor** — rated wattage per zone (cloud or manual override)
- 💡 **Power sensor** — actual consumption: rated wattage when heating is active, 0 W when off
- 🔋 **Energy sensor** — accumulated kWh with restart persistence and downtime spike protection
- ⚙️ **Options Flow** — configure scan interval and override zone wattages directly from the Home Assistant UI

## Installation via HACS

1. Open HACS in Home Assistant
2. Go to **Integrations** → three-dot menu → **Custom repositories**
3. Add URL: `https://github.com/tomasreiff/ha-fenix-v24-wifi` with category **Integration**
4. Install **Fenix V24 WiFi** from HACS
5. Restart Home Assistant
6. Go to **Settings → Integrations → Add Integration** and search for **Fenix V24 WiFi**
7. Enter your Fenix cloud account email and password

## Manual Installation

Copy the `custom_components/fenix_v24_wifi` folder into your Home Assistant `config/custom_components/` directory and restart.

## Requirements

- Home Assistant 2024.1 or newer
- Fenix V24 WiFi system with a cloud account at [v24.fenixgroup.eu](https://v24.fenixgroup.eu)

## Changelog

### 1.2.3
- Fix: resolve OptionsFlow initialization and missing `@callback` decorator that caused "Config flow could not be loaded : 500" error in modern Home Assistant
- Use Home Assistant shared aiohttp client session during config flow validation

### 1.2.2
- Make Central Air Temperature sensor strictly conditional so no unavailable phantom entity is created when the V24 master unit does not report internal air temperature

### 1.2.1
- Added Central Air Temperature sensor on the main installation device (measuring room air from the central V24 WiFi wall unit)
- Explicitly mapped zone temperature to floor probe reading and provided dedicated Floor Temperature sensor per zone

### 1.2.0
- Added `hvac_action` (Heating / Idle / Off) for dynamic flame indicators on climate cards
- Added `HVACMode.OFF` and `HVACMode.HEAT` with on/off switching
- Added preset modes support (Comfort, Eco, Away / Frost Protection, Boost, Manual)
- Added Battery Low binary sensor for wireless RF thermostats
- Added dedicated Floor Temperature sensor when floor probe data is present
- Added Options Flow UI to configure update interval (10-300s) and manual zone heating wattage overrides
- Hardened energy accumulation against spikes across Home Assistant restarts and downtime

### 1.1.4
- Added MIT LICENSE file
- Increased scan interval from 10s to 30s to reduce cloud API load and prevent rate limiting / timeouts
- Cached smarthomes discovery to eliminate redundant API requests every cycle
- Added coordinator resilience with cached state fallback during transient cloud outages

### 1.1.3
- Fix manifest key ordering (required by Hassfest)

### 1.1.2
- Added `issue_tracker` to manifest (required for HACS default list)
- Added GitHub Actions for HACS and Hassfest validation

### 1.1.1
- Fixed missing icon in HACS search
- Updated integration description

### 1.1.0
- Added **Rated Power** sensor showing the static configured wattage per zone
- Updated **Power** sensor to reflect actual consumption: rated wattage when heating is on, `0 W` when heating is off

### 1.0.0
- Initial release
