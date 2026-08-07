# Changelog

All notable changes to this project are documented here.

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
