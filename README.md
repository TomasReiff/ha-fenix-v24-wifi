# Fenix V24 WiFi — Home Assistant Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)

Home Assistant custom integration for the **Fenix V24 WiFi** thermostat, controlled via the Fenix cloud API.

## Features

- 🌡️ **Climate control** — view and set target temperature per zone
- 🔥 **Heating state** — binary sensor showing whether a zone is actively heating
- ⚡ **Rated Power sensor** — static rated wattage per zone (from cloud configuration)
- 💡 **Power sensor** — actual power consumption per zone: rated wattage when heating is active, 0 W when off
- 🔋 **Energy sensor** — accumulated kWh per zone while heating is active (persisted across restarts)

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
