# Brand assets

Original artwork for this community integration (not Magewell corporate branding).

| File | Use |
| --- | --- |
| `icon.png` | 256×256 integration icon (HACS + HA UI) |
| `icon@2x.png` | 512×512 retina icon |
| `dark_icon.png` | Dark-theme variant |
| `dark_icon@2x.png` | Dark-theme retina variant |
| `logo.png` | Landscape wordmark |
| `logo@2x.png` | Retina wordmark |
| `icon.svg` / `logo.svg` | Editable source art |

Regenerate PNGs after editing SVG:

```bash
python3 scripts/generate_brand_assets.py
```

Home Assistant 2026.3+ serves these from `custom_components/magewell_pro_convert_decoder/brand/`.
