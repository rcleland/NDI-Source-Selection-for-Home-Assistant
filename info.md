# Magewell Pro Convert Decoder

Home Assistant integration for [Magewell Pro Convert decoders](https://www.magewell.com/products/pro-convert-decoder) — NDI + URL presets, source switching, stream metadata.

![Integration icon](docs/brand/icon.png)

## Install (HACS)

1. **HACS → Integrations → ⋮ → Custom repositories**
2. Add `https://github.com/rcleland/NDI-Source-Selection-for-Home-Assistant` (Integration)
3. Install and restart Home Assistant

## Setup

**Settings → Devices & services → Add integration → Magewell Pro Convert Decoder**

Enter hostname or IP, optional port (blank = 80/443), SSL, and login if required.

## Features

- **Source** select — NDI sources and URL presets
- **Services** — `switch_source`, `set_ndi_stream`, `set_http_stream`
- **Sensors** — active source, aspect ratio, frame rate
- **Reachable** binary sensor

Full documentation: [README.md](README.md)

Dashboard examples: [docs/lovelace/streaming-source-bar-mdi.yaml](docs/lovelace/streaming-source-bar-mdi.yaml)

HACS releases: [docs/HACS.md](docs/HACS.md)

Not affiliated with Magewell.
