# Fenix V24 WiFi — Home Assistant Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)

Home Assistant custom integration for **Fenix V24 WiFi** floor heating systems, controlled via the Fenix cloud API.

## Features

- 🌡️ **Climate control** — view and set target temperature per zone
- 🔥 **Heating state** — binary sensor showing whether a zone is actively heating
- ⚡ **Power sensor** — rated wattage per zone (from cloud)
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
