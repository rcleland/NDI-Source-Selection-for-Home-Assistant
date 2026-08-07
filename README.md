# Magewell Pro Convert Decoder for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Validate](https://github.com/rcleland/NDI-Source-Selection-for-Home-Assistant/actions/workflows/validate.yml/badge.svg)](https://github.com/rcleland/NDI-Source-Selection-for-Home-Assistant/actions/workflows/validate.yml)

Home Assistant custom integration for [Magewell Pro Convert decoders](https://www.magewell.com/products/pro-convert-decoder). Switch NDI inputs and URL presets, monitor stream metadata, and build one-tap dashboard buttons — all over the local mwapi HTTP API.

<p align="center">
  <img src="docs/brand/icon.png" alt="Integration icon" width="128" height="128" />
</p>

## What you can do

| Goal | How |
| --- | --- |
| Pick a source from the HA UI | Use the **Source** dropdown entity |
| One-tap buttons for Apple TV, Google TV, Roku, … | Pre-built card YAML + branded SVG icons |
| One-tap button for an RTSP/HTTP URL | Dashboard button → `set_http_stream` service |
| Switch on a schedule or trigger | Automation → same services |
| See if the decoder is online | **Reachable** binary sensor |
| See what's playing now | **Active source name**, aspect ratio, frame rate sensors |

---

## Installation

### HACS (recommended)

**Today:** add as a custom repository (one-time setup):

1. **HACS → Integrations → ⋮ → Custom repositories**
2. Add `https://github.com/rcleland/NDI-Source-Selection-for-Home-Assistant` (category: **Integration**)
3. Search for **Magewell Pro Convert Decoder**, install, and **restart Home Assistant**

**Default HACS store (no custom repo):** requires a [submission to HACS default](docs/HACS.md#getting-into-the-default-hacs-store) — see [docs/HACS.md](docs/HACS.md).

### Manual

Copy `custom_components/magewell_pro_convert_decoder/` into `config/custom_components/` and restart.

### Versions and upgrades

HACS tracks versions via **GitHub Releases**. After installing, use HACS → **Magewell Pro Convert Decoder** → select a release (e.g. `v1.4.2`) or **Update** when a new release is published.

See [docs/HACS.md](docs/HACS.md) for the release checklist and publishing guide.

---

## Setup

1. **Settings → Devices & services → Add integration**
2. Search **Magewell Pro Convert Decoder**
3. Enter your device details:

| Setting | Default | Notes |
| --- | --- | --- |
| Hostname or IP | — | e.g. `magewell-decoder.local` or `192.168.1.50` |
| Port | 80 / 443 | Leave blank for standard HTTP/HTTPS |
| Use HTTPS | Off | Enable if mwapi is served over TLS |
| Username / password | — | Required when the device returns mwapi status `37` |

You can change hostname, port, or SSL later via **Configure** on the integration card.

---

## Entities

After setup, each decoder gets these entities:

| Entity | Type | What it does |
| --- | --- | --- |
| **Source** | `select` | Dropdown of NDI sources and saved URL presets |
| **Reachable** | `binary_sensor` | `on` when mwapi responds |
| **Active source name** | `sensor` | Name of the current decode channel |
| **Aspect ratio** | `sensor` | Output aspect ratio (when available) |
| **Frame rate** | `sensor` | Field rate (when available) |

**Find your Source entity:** **Settings → Developer tools → States** — look for `select.<device>_source` (exact name depends on your device label).

---

## Switching sources — pick the right method

Use this table to choose how to switch:

| What you want | Method | Example |
| --- | --- | --- |
| Switch from the HA UI | Source dropdown | Select `[Preset] Apple TV` or `[NDI] OBS` |
| Dashboard button for a **saved preset or NDI name** | `switch_source` | `source: Apple TV` |
| Dashboard button for an **RTSP / HTTP / HLS URL** | `set_http_stream` | `url: rtsp://192.168.1.20:554/stream` |
| NDI stream not yet in discovery | `set_ndi_stream` | Creates an ntkndi preset if needed |
| Exact dropdown option string | `select.select_option` | `option: "[Preset] Apple TV"` |

All integration services accept either:

- **`entity_id`** — your Source select entity (easiest for buttons), or
- **`config_entry_id`** — the integration instance ID

---

## Dashboard buttons

Replace `select.magewell_decoder_source` with your actual **Source** entity from Developer tools.

Preset names must match your Magewell decoder (e.g. if your Roku preset is named `Living Room Roku`, use that instead of `Roku`).

### Streaming source button bar (Apple TV, Google TV, Roku, …)

Copy one of these ready-made layouts into your dashboard (**Edit dashboard → Raw configuration editor**):

| Style | File | Requirements |
| --- | --- | --- |
| Native buttons | [docs/lovelace/streaming-source-bar-mdi.yaml](docs/lovelace/streaming-source-bar-mdi.yaml) | None — uses MDI icons |
| Mushroom chips | [docs/lovelace/streaming-source-bar-mushroom.yaml](docs/lovelace/streaming-source-bar-mushroom.yaml) | [Mushroom Cards](https://github.com/piitaya/lovelace-mushroom) (HACS) |
| Branded logos | [docs/lovelace/streaming-source-bar-branded.yaml](docs/lovelace/streaming-source-bar-branded.yaml) | [button-card](https://github.com/custom-cards/button-card) (HACS) + copy [docs/icons/streaming/](docs/icons/streaming/) to `config/www/magewell-icons/streaming/` |

**MDI icon mapping** (works in any button card):

| Source | Icon | Service `source` value |
| --- | --- | --- |
| Apple TV | `mdi:apple` | `Apple TV` |
| Google TV | `mdi:google-chromecast` | `Google TV` |
| Roku | `mdi:television-box` | `Roku` |
| Fire TV | `mdi:amazon` | `Fire TV` |
| Cable / HDMI | `mdi:television-classic` | `Cable` |

**Reusable scripts** with icons: merge [docs/scripts/streaming_sources.yaml](docs/scripts/streaming_sources.yaml) into `scripts.yaml`, then assign scripts to buttons.

Quick native example:

```yaml
type: horizontal-stack
cards:
  - type: button
    name: Google TV
    icon: mdi:google-chromecast
    tap_action:
      action: call-service
      service: magewell_pro_convert_decoder.switch_source
      service_data:
        entity_id: select.magewell_decoder_source
        source: Google TV
  - type: button
    name: Roku
    icon: mdi:television-box
    tap_action:
      action: call-service
      service: magewell_pro_convert_decoder.switch_source
      service_data:
        entity_id: select.magewell_decoder_source
        source: Roku
```

### Switch to a saved preset (single button)

Best for presets or NDI sources already on the device. No `[Preset]` prefix needed.

```yaml
type: button
name: Apple TV
icon: mdi:apple
tap_action:
  action: call-service
  service: magewell_pro_convert_decoder.switch_source
  service_data:
    entity_id: select.magewell_decoder_source
    source: Apple TV
```

Force NDI when the name could match a preset:

```yaml
tap_action:
  action: call-service
  service: magewell_pro_convert_decoder.switch_source
  service_data:
    entity_id: select.magewell_decoder_source
    source: "DESKTOP-ABC (OBS)"
    source_type: ndi
```

### Switch to an RTSP or HTTP URL

Creates or updates a URL preset on the decoder, then selects it.

```yaml
type: button
name: Security cam
icon: mdi:cctv
tap_action:
  action: call-service
  service: magewell_pro_convert_decoder.set_http_stream
  service_data:
    entity_id: select.magewell_decoder_source
    channel_name: Security cam
    url: rtsp://192.168.1.20:554/stream
```

Use the full URL, including credentials or query parameters if your stream requires them.

### Use the built-in dropdown from a button

If the source already appears in the Source entity options:

```yaml
type: button
name: Apple TV
tap_action:
  action: call-service
  service: select.select_option
  target:
    entity_id: select.magewell_decoder_source
  data:
    option: "[Preset] Apple TV"
```

NDI options use the `[NDI] …` prefix shown in the dropdown.

### Reusable script (use from any card)

Add to `scripts.yaml`:

```yaml
magewell_apple_tv:
  alias: Magewell → Apple TV
  sequence:
    - service: magewell_pro_convert_decoder.switch_source
      data:
        entity_id: select.magewell_decoder_source
        source: Apple TV
```

Then set a button's tap action to **Perform action → Script: Magewell → Apple TV**.

More card layouts and automations: [docs/dashboard-buttons.md](docs/dashboard-buttons.md)

---

## Automations

### Scheduled source switch

```yaml
automation:
  - alias: Morning — Apple TV on Magewell
    trigger:
      - platform: time
        at: "07:00:00"
    action:
      - service: magewell_pro_convert_decoder.switch_source
        data:
          entity_id: select.magewell_decoder_source
          source: Apple TV
```

### Triggered RTSP switch (e.g. motion)

```yaml
automation:
  - alias: Motion — front door cam on Magewell
    trigger:
      - platform: state
        entity_id: binary_sensor.front_door_motion
        to: "on"
    action:
      - service: magewell_pro_convert_decoder.set_http_stream
        data:
          entity_id: select.magewell_decoder_source
          channel_name: Front door
          url: rtsp://192.168.1.20:554/stream
```

---

## Services reference

### `magewell_pro_convert_decoder.switch_source`

Switch to a preset or NDI source by plain name. **Use this for most dashboard buttons.**

| Field | Required | Description |
| --- | --- | --- |
| `entity_id` or `config_entry_id` | One of two | Target decoder |
| `source` | Yes | Preset or NDI name, e.g. `Apple TV` |
| `source_type` | No | `auto` (default), `ndi`, or `preset` |

### `magewell_pro_convert_decoder.set_http_stream`

Add or update a URL preset and switch to it. **Use this for RTSP, HTTP, HLS, and similar URLs.**

| Field | Required | Description |
| --- | --- | --- |
| `entity_id` or `config_entry_id` | One of two | Target decoder |
| `channel_name` | Yes | Label shown in the source list |
| `url` | Yes | Full stream URL |
| `update_if_exists` | No | Update preset if name already exists (default: `true`) |

### `magewell_pro_convert_decoder.set_ndi_stream`

Select an NDI source by exact name. If direct selection fails, creates an ntkndi preset.

| Field | Required | Description |
| --- | --- | --- |
| `entity_id` or `config_entry_id` | One of two | Target decoder |
| `ndi_name` | Yes | Exact NDI stream name |
| `ndi_ip_port` | No | `host:port` if not in discovery (e.g. `192.168.1.10:5961`) |
| `preset_label` | No | Preset name if one must be created (default: `HA NDI`) |
| `buffer_duration` | No | Buffer in ms for ntkndi preset (default: `60`) |

Service definitions also appear under **Developer tools → Services** after restart.

---

## Supported devices

Magewell Pro Convert **decoder** models with the `/mwapi` HTTP API, including:

- Pro Convert for NDI to HDMI / HDMI 4K
- Pro Convert for NDI to SDI
- Pro Convert for NDI to AIO

Device API reference: [Magewell mwapi docs](https://www.magewell.com/api-docs/pro-convert-decoder-api/)

---

## Related projects

- [brianegge/homeassistant-magewell](https://github.com/brianegge/homeassistant-magewell) — community integration with encoder/decoder monitoring (CPU, temperature, NDI select)

---

## Disclaimer

Community integration — not affiliated with Magewell. Product names are used for identification only.

## License

MIT — see [LICENSE](LICENSE).
