# Dashboard buttons and automations

Use these patterns to build one-tap source switching on a Home Assistant dashboard — similar to [brianegge/homeassistant-magewell](https://github.com/brianegge/homeassistant-magewell) automations, but with preset/RTSP support.

Replace `select.magewell_decoder_source` with your **Source** entity (Settings → Developer tools → States).

Preset names (`Apple TV`, `Google TV`, `Roku`, etc.) must match what you saved on the Magewell decoder.

## Streaming sources (Apple TV, Google TV, Roku, …)

Ready-made card layouts with icons:

| Card style | File | Icons |
| --- | --- | --- |
| Native buttons (no HACS) | [streaming-source-bar-mdi.yaml](lovelace/streaming-source-bar-mdi.yaml) | MDI (`mdi:apple`, `mdi:google-chromecast`, …) |
| Mushroom chips | [streaming-source-bar-mushroom.yaml](lovelace/streaming-source-bar-mushroom.yaml) | MDI |
| Branded logos | [streaming-source-bar-branded.yaml](lovelace/streaming-source-bar-branded.yaml) | SVG icons from [icons/streaming/](icons/streaming/) |

**Branded icons:** copy `docs/icons/streaming/` to `config/www/magewell-icons/streaming/`, then use the branded card YAML.

**Scripts:** merge [scripts/streaming_sources.yaml](scripts/streaming_sources.yaml) into `scripts.yaml` for reusable actions with icons.

**Icon reference:** [source-catalog.yaml](source-catalog.yaml) lists preset names and icon options per source.

### Native button bar (copy-paste)

```yaml
type: horizontal-stack
cards:
  - type: button
    name: Apple TV
    icon: mdi:apple
    tap_action:
      action: call-service
      service: magewell_pro_convert_decoder.switch_source
      service_data:
        entity_id: select.magewell_decoder_source
        source: Apple TV
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

See the full five-source bar (Fire TV, Cable) in [lovelace/streaming-source-bar-mdi.yaml](lovelace/streaming-source-bar-mdi.yaml).

## Option 1: `switch_source` service (recommended for buttons)

Plain preset or NDI names — no `[Preset]` / `[NDI]` prefix required.

### Button card (Lovelace)

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

### Mushroom template chip

```yaml
type: custom:mushroom-chips-card
chips:
  - type: template
    icon: mdi:apple
    content: Apple TV
    tap_action:
      action: call-service
      service: magewell_pro_convert_decoder.switch_source
      service_data:
        entity_id: select.magewell_decoder_source
        source: Apple TV
  - type: template
    icon: mdi:television
    content: Living Room NDI
    tap_action:
      action: call-service
      service: magewell_pro_convert_decoder.switch_source
      service_data:
        entity_id: select.magewell_decoder_source
        source: "DESKTOP-ABC (OBS)"
        source_type: ndi
```

### Script (reusable from any card or automation)

```yaml
script:
  magewell_apple_tv:
    alias: Magewell → Apple TV
    sequence:
      - service: magewell_pro_convert_decoder.switch_source
        data:
          entity_id: select.magewell_decoder_source
          source: Apple TV
```

Then use **Tap action → Perform action → Script: Magewell → Apple TV**.

## Option 2: RTSP / HTTP URL presets

Creates or updates a saved URL preset on the decoder, then selects it.

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

Use the full URL including credentials or query parameters if your stream requires them.

## Option 3: Built-in select entity

If the source already appears in the dropdown, you can call the standard select service:

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

NDI options use the `[NDI] …` prefix from the entity options list.

## Automations (scheduled or triggered switching)

```yaml
automation:
  - alias: Morning — show Apple TV on Magewell
    trigger:
      - platform: time
        at: "07:00:00"
    action:
      - service: magewell_pro_convert_decoder.switch_source
        data:
          entity_id: select.magewell_decoder_source
          source: Apple TV

  - alias: Motion — switch to RTSP cam
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

## Services reference

| Service | Use when |
| --- | --- |
| `switch_source` | Preset or NDI name already on the device |
| `set_http_stream` | RTSP, HTTP, HLS, or other URL (creates preset if needed) |
| `set_ndi_stream` | NDI name not in discovery yet; may create ntkndi preset |
| `select.select_option` | You want the exact dropdown option string |

All services accept either `entity_id` (Source select) or `config_entry_id`.
