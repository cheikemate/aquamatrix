# AQUAmatrix SMASVFX Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Hassfest](https://github.com/cheikemate/aquamatrix/actions/workflows/ci.yaml/badge.svg)](https://github.com/cheikemate/aquamatrix/actions/workflows/ci.yaml)

A Home Assistant integration to fetch water meter readings and billing information from the AQUAmatrix SMASVFX portal.

<img width="1351" height="716" alt="image" src="https://github.com/user-attachments/assets/0bf76f03-8901-4213-bf4a-1690d3cd5fce" />


## Features
- **Meter Readings:** Tracks the last reading value and date.
- **Consumption:** Tracks current and previous month consumption.
- **Billing:** Tracks the last billed value and total debt.
- **Energy Dashboard:** Compatible with the Home Assistant Energy dashboard.
- **Localization:** Supports English and Portuguese.

## Installation via HACS
1. Open HACS in Home Assistant.
2. Click on **Integrations**.
3. Click the three dots in the top right and select **Custom repositories**.
4. Paste the URL of this repository: `https://github.com/cheikemate/aquamatrix` and select **Integration** as the category.
5. Click **Add**.
6. Search for **AQUAmatrix SMASVFX** and click **Download**.
7. Restart Home Assistant.

## Configuration
1. Go to **Settings > Devices & Services**.
2. Click **Add Integration**.
3. Search for **AQUAmatrix SMASVFX**.
4. Enter your credentials:
   - **Tenant:** Your portal tenant (defaults to `SMSnet`).
   - **Username:** Your portal username.
   - **Password:** Your portal password.

## Energy Dashboard

Go to **Settings → Energy → Water → Add water source**.

| Field | Value |
|---|---|
| Water consumption | `Last reading` |
| Use an entity tracking the total costs | `Total billed` |

## Troubleshooting
If you experience issues connecting, please ensure your credentials are correct and that you can log in manually to the AQUAmatrix portal.

## License
This project is licensed under the GNU General Public License v3.0 (GPLv3).
