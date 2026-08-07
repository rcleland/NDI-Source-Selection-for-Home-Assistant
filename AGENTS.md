# Agent instructions — Magewell Pro Convert Decoder (Home Assistant)

Handoff guide for rebuilding, extending, or debugging this project without prior chat context.

## Project summary

**What it is:** A Home Assistant custom integration for **Magewell Pro Convert decoders** (NDI → HDMI/SDI/AIO). It talks to the local **mwapi** HTTP API (`GET /mwapi?method=…`), exposes entities, and provides services for source switching (NDI, presets, RTSP/HTTP URLs).

**Domain:** `magewell_pro_convert_decoder`  
**GitHub:** https://github.com/rcleland/NDI-Source-Selection-for-Home-Assistant  
**HACS:** Custom repository (default-store submission pending)  
**Min HA version:** 2024.1.0 (`hacs.json`)

**Not affiliated with Magewell.** Community integration.

---

## Repository layout

```
custom_components/magewell_pro_convert_decoder/   ← the integration (only code HACS installs)
  __init__.py          Setup, service registration
  config_flow.py       Add / reconfigure / options (poll interval)
  coordinator.py       Polling + set-channel + NDI/HTTP preset actions
  mwapi.py             HTTP session, auth, JSON requests, setup validation
  api_normalize.py     Parse mwapi JSON + source option strings + ntkndi URLs
  host_util.py         Hostname/IP normalize, origin URL, unique_id
  entity.py            Shared entity base (available, device_info)
  select.py            Source dropdown entity
  sensor.py            Active source, aspect ratio, frame rate
  binary_sensor.py     Reachable
  const.py             Domain, config keys, timing constants
  manifest.json        Integration metadata + version
  strings.json         UI translations (config, services, entities)
  services.yaml        Service definitions for Developer Tools / UI
  icons.json           MDI icons for entities and services
  brand/               HACS / HA brand PNGs + SVG sources

hacs.json              HACS metadata (repo root)
info.md                HACS store page (short; points to README)
README.md              Primary user documentation
CHANGELOG.md           Version history (newest first)
docs/
  HACS.md              Release workflow + default-store checklist
  dashboard-buttons.md Index to Lovelace examples
  lovelace/            Copy-paste dashboard YAML
  icons/streaming/     SVG icons for dashboard buttons
  scripts/             Example scripts.yaml snippets
scripts/
  prepare_release.py   Used by Auto Release workflow
  generate_brand_assets.py  Regenerate brand PNGs from SVG

.github/workflows/
  validate.yml         Hassfest + HACS on push/PR
  auto-release.yml     Patch bump + GitHub Release after Validate passes
  backfill-release.yml Manual release for an existing tag
  release.yml          Validates + publishes on manual tag push
```

**Do not** put integration code outside `custom_components/magewell_pro_convert_decoder/`.

---

## Architecture (read this first)

```
Config flow ──► config entry (host, port, SSL, credentials)
                      │
                      ▼
              MagewellDecoderCoordinator
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
     mwapi.py    api_normalize   host_util
   (HTTP/auth)   (JSON parsing)   (URLs)
        │
        ▼
   Entities: select, sensors, binary_sensor
        │
        ▼
   Services: switch_source, set_ndi_stream, set_http_stream
```

| Module | Responsibility |
|--------|----------------|
| `mwapi.py` | `async_create_magewell_session`, `async_mwapi_json`, `async_validate_connection`, MD5 login, exceptions for config flow |
| `coordinator.py` | Poll mwapi on interval; `_on_source_changed()` refreshes immediately + again after 5s for signal metadata |
| `api_normalize.py` | Firmware may use kebab-case or camelCase keys; also `encode/decode_source_option`, `build_ntkndi_url` |
| `config_flow.py` | **Selectors only** in schemas — no `vol.Coerce` / `vol.Any` (breaks HA UI with 500) |
| `entity.py` | All entities inherit `MagewellEntity` for `available` + `device_info` |

---

## Magewell mwapi essentials

- Base URL: `{http|https}://{host}:{port}/mwapi?method={name}&…`
- **Login:** `method=login&id=…&pass={md5_hex_password}` — session cookie required for protected calls (status `37` = auth required, `36` = bad credentials)
- **Cookie jar:** Use `CookieJar(unsafe=True)` for IP hosts (`mwapi.py`)
- **Key methods:** `ping`, `get-channel`, `set-channel`, `get-ndi-sources`, `list-channels`, `add-channel`, `modify-channel`, `get-signal-info`, `login`
- **set-channel:** `ndi-name=true|false`, `name={source name}`
- **NDI fallback:** If direct NDI set-channel fails, create ntkndi preset via `add-channel` with URL like `ntkndi://ndi?name=…&url=host:port&mw-buffer-duration=60`

Official docs: https://www.magewell.com/api-docs/pro-convert-decoder-api/

---

## Entities

| Entity | Platform | Notes |
|--------|----------|-------|
| Source | `select` | Options prefixed `[NDI] ` or `[Preset] `; scenes-friendly |
| Reachable | `binary_sensor` | `CONNECTIVITY`; attrs include per-API status codes |
| Active source name | `sensor` | From `get-channel` |
| Video aspect ratio | `sensor` | From `get-signal-info` |
| Video frame rate | `sensor` | From `get-signal-info` (field-rate as fps) |

**Polling:** Default 60s (`DEFAULT_SCAN_INTERVAL` in options flow). After source change, coordinator calls `_on_source_changed()`: refresh now + **5s delayed refresh** (`SOURCE_SIGNAL_REFRESH_DELAY`) because signal info lags `set-channel`.

---

## Services

All accept `entity_id` (Source select) **or** `config_entry_id`.

| Service | Purpose |
|---------|---------|
| `switch_source` | Plain name, e.g. `Apple TV` — best for dashboard buttons |
| `set_ndi_stream` | NDI by exact name; creates ntkndi preset if needed |
| `set_http_stream` | RTSP/HTTP/HLS URL preset + select |

Register in `__init__.py` (`async_setup`). Schemas use `cv.has_at_least_one_key("config_entry_id", "entity_id")`. Coordinator lookup is inline in `__init__.py` (`_coordinator_from_service`).

When adding a service: update `services.yaml`, `strings.json` (services section), and README services table.

---

## Config flow rules (critical)

Home Assistant serializes config flow schemas for the frontend. **Only use selector types** (`TextSelector`, `BooleanSelector`, `NumberSelector`) — never bare `vol.Coerce`, custom callables, or `vol.Any("", NumberSelector(…))` in schemas. Violations cause:

> Config flow could not be loaded: 500 Internal Server Error

**Port field:** `TextSelector()` optional; parse empty → 80/443 in Python (`_resolve_port`).  
**Defaults:** Use `add_suggested_values_to_schema()`, not `default=` in `vol.Schema`.  
**Host:** Accept hostname or IP; validate with `is_host_valid()` after `normalize_host()`.

---

## Coding conventions

1. **Minimize scope** — smallest correct diff; match existing style.
2. **No over-abstraction** — prefer extending `mwapi.py` / `coordinator.py` over new one-function modules.
3. **Keep modules thin:**
   - HTTP/auth → `mwapi.py`
   - JSON/source strings → `api_normalize.py`
   - URLs/unique_id → `host_util.py`
4. **Comments** only for non-obvious mwapi behavior.
5. **Do not commit** unless the user asks.
6. **Version bump** `manifest.json` + `CHANGELOG.md` when shipping user-facing changes (Auto Release also bumps patch on push to `main`).

---

## Release & Git workflow

- **Branch:** `main`
- **Remote:** `https://github.com/rcleland/NDI-Source-Selection-for-Home-Assistant.git`
- **Every push to `main`** (unless `[skip release]` in commit message) triggers Validate → Auto Release → patch version + GitHub Release for HACS.
- **Skip release:** commit message contains `[skip release]`
- **Manual minor/major:** set version in `manifest.json` before push (Auto Release uses manifest if ahead of latest tag).
- **CI:** Hassfest + HACS action must pass (`.github/workflows/validate.yml`)
- **GitHub Actions** needs **Read and write** workflow permissions for auto-release bot pushes.

See [docs/HACS.md](docs/HACS.md) for default HACS store submission checklist.

**Note:** Project folder may live on Synology Drive. If `.git` misbehaves, git metadata may exist under `_git_metadata/` with worktree `_github_staging/` — prefer normal `.git` in project root when possible.

---

## Validation before shipping

```bash
# Syntax check
python3 -m py_compile custom_components/magewell_pro_convert_decoder/*.py

# Full validation (requires Docker)
docker run --rm -v "$PWD:/github/workspace" ghcr.io/home-assistant/hassfest
# HACS action runs in GitHub Actions
```

Test on a real decoder when changing: config flow, source select, service calls, aspect ratio update after source switch (~5s).

---

## Dashboard / user docs

- **Primary guide:** [README.md](README.md)
- **Lovelace YAML:** [docs/lovelace/](docs/lovelace/)
- **HACS page:** [info.md](info.md) — keep short
- Do **not** duplicate full service docs in three places; `services.yaml` + `strings.json` are required for HA UI; README is for humans.

---

## Common tasks

### Add a new service
1. Method on `MagewellDecoderCoordinator`
2. Schema + handler in `__init__.py`
3. `services.yaml`, `strings.json`, `icons.json`
4. README example (optional: `docs/scripts/` snippet)

### Fix slow sensor updates
- Check `DEFAULT_SCAN_INTERVAL` (options) vs `SOURCE_SIGNAL_REFRESH_DELAY` (post-switch)
- Ensure source-change paths call `_on_source_changed()`, not only `async_request_refresh()`

### Add a new entity
1. Extend `MagewellEntity` + platform base
2. Register in platform's `async_setup_entry`
3. Add to `PLATFORMS` in `__init__.py`
4. `strings.json` entity section + translation key if using `_attr_translation_key`

### Regenerate brand PNGs
```bash
python3 scripts/generate_brand_assets.py
```

---

## Related projects

- [brianegge/homeassistant-magewell](https://github.com/brianegge/homeassistant-magewell) — encoder/decoder monitoring (CPU, temp); different scope

---

## Rebuild checklist (from scratch)

If recreating the integration:

1. Create `custom_components/magewell_pro_convert_decoder/` with domain above
2. Implement `mwapi.py` (session + ping + login + JSON GET)
3. Config flow with serializable selectors only
4. Coordinator polling ping, get-ndi-sources, list-channels, get-channel, get-signal-info
5. Select entity with `[NDI]` / `[Preset]` option encoding
6. Services for automation/button use cases
7. `brand/icon.png` (256×256) for HACS
8. Root `hacs.json`, `README.md`, `LICENSE`, `.github/workflows/validate.yml`
9. Push to GitHub; enable Actions write permissions; verify Auto Release creates `v*` tags

---

## What not to do

- Do not use IP-only validation that rejects hostnames
- Do not put `vol.Coerce` or callables in config flow schemas
- Do not split HTTP logic across many tiny files again (use `mwapi.py`)
- Do not force-push `main` without explicit user request
- Do not store plaintext passwords except in HA config entry (encrypted at rest by HA)
