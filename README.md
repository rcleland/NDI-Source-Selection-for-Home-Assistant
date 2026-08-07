# Magewell Pro Convert Decoder for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Validate](https://github.com/rcleland/ha-magewell-pro-convert-decoder/actions/workflows/validate.yml/badge.svg)](https://github.com/rcleland/ha-magewell-pro-convert-decoder/actions/workflows/validate.yml)

Home Assistant custom integration for [Magewell Pro Convert decoders](https://www.magewell.com/products/pro-convert-decoder). Switch NDI inputs, monitor stream metadata, and automate source changes over the local mwapi HTTP API.

<p align="center">
  <img src="docs/brand/icon.png" alt="Integration icon" width="128" height="128" />
</p>

## Features

- **Source select** — NDI sources and saved URL presets in one dropdown
- **Reachability sensor** — know when mwapi is responding
- **Stream sensors** — active source name, aspect ratio, frame rate
- **Services** — switch by plain name, set NDI, or push RTSP/HTTP presets from buttons and automations
- **Hostname or IP** — use either; change later via **Configure**

## Installation

### HACS

1. **HACS → Integrations → ⋮ → Custom repositories**
2. Add `https://github.com/rcleland/ha-magewell-pro-convert-decoder` (Integration)
3. Install **Magewell Pro Convert Decoder** and restart Home Assistant

### Manual

Copy `custom_components/magewell_pro_convert_decoder/` to `config/custom_components/` and restart.

## Quick start

1. **Settings → Devices & services → Add integration**
2. Search **Magewell Pro Convert Decoder**
3. Enter hostname or IP (port optional), SSL settings, and login if the device requires it

## Documentation

See [info.md](info.md) for entity and service details, [docs/dashboard-buttons.md](docs/dashboard-buttons.md) for Lovelace button examples, or the [Magewell mwapi reference](https://www.magewell.com/api-docs/pro-convert-decoder-api/).

## Disclaimer

Community integration — not affiliated with Magewell. Product names are used for identification only.

## License

MIT — see [LICENSE](LICENSE).
