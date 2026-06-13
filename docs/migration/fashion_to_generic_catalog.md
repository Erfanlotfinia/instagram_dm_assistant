# Fashion to generic catalog migration

Fashion-specific modules are now compatibility wrappers and category presets under the generic catalog intelligence system.

Migration plan:
- `color_aliases` and `size_aliases` remain readable for old APIs and can be mirrored into `attribute_aliases` for `color` and `size`.
- `Fashion Dictionary` becomes `Attribute Dictionary` in user-facing UI.
- Unavailable color/size demand becomes unavailable attribute demand; legacy columns remain for compatibility.
- The old variant resolver request (`raw_color`, `raw_size`) stays supported while new requests send `raw_requested_attributes`.
