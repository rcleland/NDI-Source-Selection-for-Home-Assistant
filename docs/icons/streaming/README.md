# Streaming source icons

SVG icons for dashboard source buttons (Apple TV, Google TV, Roku, Fire TV, Cable).

## Install in Home Assistant

1. Copy this folder to your HA config, e.g. `config/www/magewell-icons/streaming/`
2. In Lovelace cards, reference icons as `/local/magewell-icons/streaming/roku.svg`

Or use the MDI fallbacks in [source-catalog.yaml](../../source-catalog.yaml) if you prefer not to copy files.

**Note:** Preset names (`Apple TV`, `Google TV`, `Roku`, etc.) must match what you saved on the Magewell decoder or what appears in the **Source** dropdown.
