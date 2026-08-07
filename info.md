# Magewell Pro Convert Decoder

Monitor and control [Magewell Pro Convert](https://www.magewell.com/products/pro-convert-decoder) **decoders** from Home Assistant.

![Integration icon](docs/brand/icon.png)

## Highlights

- **Source select** — switch NDI sources and URL presets from the HA UI
- **Reachability** — binary sensor for mwapi availability
- **Stream metadata** — active source, aspect ratio, and frame rate sensors
- **Dashboard buttons** — Apple TV, Google TV, Roku, Fire TV presets with MDI or branded SVG icons; ready-made Lovelace YAML in [docs/lovelace/](docs/lovelace/)
- **Hostname or IP** — use either address; switch anytime via **Configure**

## Supported devices

Magewell Pro Convert decoder models with the `/mwapi` HTTP API, including:

- Pro Convert for NDI to HDMI / HDMI 4K
- Pro Convert for NDI to SDI
- Pro Convert for NDI to AIO

Not affiliated with or endorsed by Magewell. Product names are used for identification only.

## Installation

### HACS (recommended)

1. Open **HACS → Integrations → ⋮ → Custom repositories**
2. Add `https://github.com/rcleland/NDI-Source-Selection-for-Home-Assistant` (category: **Integration**)
3. Search for **Magewell Pro Convert Decoder** and install
4. Restart Home Assistant

### Manual

Copy `custom_components/magewell_pro_convert_decoder/` into your `config/custom_components/` directory and restart.

## Configuration

1. **Settings → Devices & services → Add integration**
2. Search for **Magewell Pro Convert Decoder**
3. Enter hostname or IP, optional port (blank = 80/443), SSL options, and login if required

| Setting | Default | Notes |
| --- | --- | --- |
| Hostname or IP | — | e.g. `magewell-decoder.local` or `192.168.1.50` |
| Port | 80 / 443 | Leave blank for standard HTTP/HTTPS |
| Use HTTPS | Off | Enable if the device serves mwapi over TLS |
| Username / password | — | Required when the device returns mwapi status `37` |

## Entities

| Entity | Type | Description |
| --- | --- | --- |
| Source | `select` | NDI sources and saved presets |
| Reachable | `binary_sensor` | Device responds to mwapi ping |
| Active source name | `sensor` | Current decode channel |
| Aspect ratio | `sensor` | Output aspect ratio when available |
| Frame rate | `sensor` | Field rate when available |

## Services

- `magewell_pro_convert_decoder.switch_source` — switch to a preset or NDI source by plain name (e.g. `Apple TV`); ideal for dashboard buttons
- `magewell_pro_convert_decoder.set_ndi_stream` — select NDI by exact name (creates ntkndi preset if needed)
- `magewell_pro_convert_decoder.set_http_stream` — add/update URL preset (RTSP, HTTP, HLS, …) and switch to it

All services accept `entity_id` (your Source select) or `config_entry_id`.

**Dashboard examples:** [docs/dashboard-buttons.md](docs/dashboard-buttons.md) · **Streaming source bar:** [docs/lovelace/streaming-source-bar-mdi.yaml](docs/lovelace/streaming-source-bar-mdi.yaml)

**HACS versioning & default store:** [docs/HACS.md](docs/HACS.md)

See [Magewell mwapi docs](https://www.magewell.com/api-docs/pro-convert-decoder-api/) for device API details.

## Related projects

- [brianegge/homeassistant-magewell](https://github.com/brianegge/homeassistant-magewell) — community integration focused on encoder/decoder monitoring with CPU/temperature sensors

## License

MIT — see [LICENSE](LICENSE).
