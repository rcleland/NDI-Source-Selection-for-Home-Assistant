# Changelog

All notable changes to this project are documented here.

## [1.4.6] - 2026-08-07

### Fixed
- Aspect ratio and frame rate sensors refresh 5 seconds after a source change (signal info lags set-channel)

## [1.4.5] - 2026-08-07

### Changed
- Code consolidation: `mwapi.py` (HTTP/auth), shared `entity.py` base, merged `api_normalize` + source encoding
- Removed duplicate modules (`auth`, `http_session`, `source_encoding`, `service_helpers`)
- Trimmed HACS/docs duplication (`info.md`, `dashboard-buttons.md`)

## [1.4.4] - 2026-08-07

### Fixed
- Config flow 500 on latest Home Assistant: port schema now uses serializable selectors only (removed `vol.Any` / `vol.Coerce` that broke frontend schema loading)
- Options flow uses `add_suggested_values_to_schema()` for scan interval

## [1.4.3] - 2026-08-07

### Added
- HACS publishing guide ([docs/HACS.md](docs/HACS.md)) with versioning and default-store steps
- GitHub Release workflow (validates on tag push, creates release from CHANGELOG)

### Changed
- Manifest/documentation URLs point to `NDI-Source-Selection-for-Home-Assistant` repository

## [1.4.2] - 2026-08-07

### Added
- Streaming source dashboard pack: Apple TV, Google TV, Roku, Fire TV, Cable
- Branded SVG icons in `docs/icons/streaming/`
- Ready-made Lovelace cards (native MDI, Mushroom, button-card branded)
- Script templates in `docs/scripts/streaming_sources.yaml`
- Source icon catalog in `docs/source-catalog.yaml`

## [1.4.1] - 2026-08-07

### Added
- `switch_source` service — switch presets/NDI by plain name for dashboard buttons and automations
- `entity_id` targeting on all services (use your Source select entity instead of config entry ID)
- [Dashboard button examples](docs/dashboard-buttons.md) (Button card, Mushroom, scripts, automations)

## [1.4.0] - 2026-08-07

### Added
- Brand assets (`icon.png`, logos, dark variants) for HACS and Home Assistant UI
- HACS packaging: `info.md`, validation workflow, MIT license
- Entity/service MDI icons via `icons.json`

### Fixed
- Config flow accepts empty port fields on latest Home Assistant
- Hostname or IP both supported for device communication

## [1.3.6] - 2026-08-07

### Added
- Shared `host_util.py` for hostname/IP URL building
- Reconfigure updates unique ID when connection details change

### Changed
- Config flow uses `add_suggested_values_to_schema()` instead of inline defaults

## [1.3.5] - 2026-08-07

### Fixed
- Optional port validation no longer blocks setup when left blank
