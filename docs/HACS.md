# HACS publishing and versioning

How to use **GitHub releases** for version tracking in HACS, and how to get listed in the **default HACS store** (no custom repository required).

Current repository: [rcleland/NDI-Source-Selection-for-Home-Assistant](https://github.com/rcleland/NDI-Source-Selection-for-Home-Assistant)

---

## How HACS versioning works

Every push to `main` triggers **[Auto Release](../.github/workflows/auto-release.yml)** (unless the commit message starts with `chore(release):` or contains `[skip release]`):

1. Hassfest + HACS validation must pass
2. Patch version increments from the latest `v*` tag (e.g. `v1.4.3` → `v1.4.4`)
3. `manifest.json` and `CHANGELOG.md` are updated
4. A GitHub tag and **Release** are published automatically

HACS reads version information from two places:

| Source | Purpose |
| --- | --- |
| `custom_components/.../manifest.json` → `"version"` | Version shown in HA **Settings → Devices & services** |
| **GitHub Releases** (tags like `v1.4.4`) | Version picker in HACS when installing or upgrading |

If you publish releases, HACS offers the **5 most recent releases** plus the default branch (`main`). Users can pin a version or pick **Latest** for the newest release.

**Skip auto-release** for work-in-progress pushes: include `[skip release]` in the commit message.

---

## Manual release (optional)

Automatic releases handle normal workflow. Use manual steps only if you need a **minor/major** bump or the workflow failed.

### Manual checklist

1. **Update the version** in `custom_components/magewell_pro_convert_decoder/manifest.json`
2. **Add a section** to `CHANGELOG.md` (keep newest at top)
3. **Commit and push** to `main`
4. **Create a GitHub Release** (not just a tag):
   - Tag: `v1.5.0` (must match manifest, with a `v` prefix)
   - Publish release

Pushing a `v*` tag triggers the [Release workflow](../.github/workflows/release.yml), which validates and publishes the release if the tag matches `manifest.json`.

### Preview next version locally

```bash
python3 scripts/prepare_release.py --dry-run
```

---

## Installing today (custom repository)

Until the integration is in the default store, users add it once as a custom repository:

1. **HACS → Integrations → ⋮ → Custom repositories**
2. URL: `https://github.com/rcleland/NDI-Source-Selection-for-Home-Assistant`
3. Category: **Integration**
4. Search **Magewell Pro Convert Decoder** → Install
5. To upgrade later: open the integration in HACS and pick a version from the release list

---

## Getting into the default HACS store

Default integrations appear in HACS search **without** adding a custom repository. Inclusion is **not automatic** — you submit a PR to the HACS project and wait in their review queue (often **months**).

Official guide: [Include default repositories](https://hacs.xyz/docs/publish/include/)

### Requirements checklist

| Requirement | Status / action |
| --- | --- |
| Public GitHub repository | ✅ |
| Valid `hacs.json` in repo root | ✅ |
| Valid integration `manifest.json` with `version` | ✅ |
| Brand assets (`brand/icon.png`) | ✅ |
| [Hassfest + HACS Action](https://github.com/rcleland/NDI-Source-Selection-for-Home-Assistant/actions) passing on `main` | Verify green ✅ |
| At least **one GitHub Release** published | ✅ Auto Release on every push to `main` |
| Repository **description** set on GitHub | ⬜ Settings → General → Description |
| **Issues** enabled | ⬜ Settings → General → Features |
| **Topics** on GitHub (e.g. `home-assistant`, `hacs`, `magewell`, `ndi`) | ⬜ Settings → General → Topics |
| README with install instructions | ✅ |
| You are the repo **owner** (not an org-only PR) | ✅ |

### Submit to HACS default

1. Complete the checklist above (especially the first GitHub Release).
2. Fork [hacs/default](https://github.com/hacs/default).
3. Create a branch from `master` (not `main`).
4. Add your repo to the correct file, **alphabetically** by GitHub `owner/repo`:

   **File:** `integration` (in the repo root — it's a JSON list file)

   ```json
   "rcleland/NDI-Source-Selection-for-Home-Assistant"
   ```

5. Open a PR using the [HACS default PR template](https://github.com/hacs/default/compare) and fill every field honestly.
6. Wait for automated checks and maintainer review.

After merge, your integration appears in the default store on the next HACS scan (every ~8 hours).

### Tips for approval

- Keep CI green on every push to `main`.
- Use semantic versioning (`1.4.2`, `1.5.0`, …) and maintain `CHANGELOG.md`.
- Respond promptly if reviewers request changes.
- Consider a clearer repo name before submitting (e.g. `ha-magewell-pro-convert-decoder`) — optional but easier for users to find. Renaming on GitHub redirects old URLs.

---

## Version numbering convention

Automatic releases always increment the **patch** version from the latest tag.

For **minor** or **major** bumps, edit `manifest.json` manually before pushing, or run:

```bash
# Example: set next release to 1.5.0 manually in manifest.json, update CHANGELOG, then push
```

Always keep `manifest.json` `"version"` in sync with the GitHub release tag (without the `v` prefix in manifest, with `v` on the tag).

Use [Semantic Versioning](https://semver.org/) when choosing manual version numbers:

- **Patch** (`1.4.2` → `1.4.3`): bug fixes — automatic
- **Minor** (`1.4.2` → `1.5.0`): new features, backward compatible — manual manifest bump before push
- **Major** (`1.4.2` → `2.0.0`): breaking changes — manual manifest bump before push

---

## Related links

- [HACS integration requirements](https://hacs.xyz/docs/publish/integration/)
- [HACS general publishing](https://hacs.xyz/docs/publish/start/)
- [Home Assistant integration manifest](https://developers.home-assistant.io/docs/creating_integration_manifest/)
