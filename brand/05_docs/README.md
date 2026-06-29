# Modira Rebuilt Vector Brand Pack

This pack rebuilds the Modira identity from the provided raster brand sheet as editable SVG assets.

## What is included

- `00_source_svg/` — rebuilt vector SVG source files for symbol, wordmark, lockups, app icon, favicon, and brand board.
- `01_png_exports/` — production PNG exports from the rebuilt SVGs.
- `02_icons_favicons/` — app icon sizes, transparent symbol sizes, `favicon.ico`, and `site.webmanifest`.
- `99_reference/` — original provided raster reference image.

## Important note

The original image was a raster brand sheet, not a true vector source file. These files are rebuilt as clean, editable SVG approximations based on that reference. The wordmark uses a standard font stack (`Inter, Arial, sans-serif`) and should be reviewed/outlined in Figma or Illustrator before final trademark/production use.

## Recommended production usage

Use these files first:

- Primary website/header logo: `00_source_svg/modira_logo_horizontal_full_color.svg`
- Dark background logo: `00_source_svg/modira_logo_horizontal_white_reversed.svg`
- App icon: `00_source_svg/modira_app_icon.svg`
- Favicon: `02_icons_favicons/favicon.ico`
- Color tokens: `04_brand_tokens/modira-brand-tokens.css`

## Accessibility

When the logo is linked to the homepage, use alt text such as `Modira home`. When the nearby text already says Modira, the symbol can be treated as decorative.
