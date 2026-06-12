# cairometal

**A [pycairo](https://pycairo.readthedocs.io/)-compatible 2D vector-graphics backend that renders on the Apple GPU via Metal.**

> **Independent project — not affiliated with the [cairo](https://cairographics.org) graphics library or the official `pycairo` binding.** It reimplements a compatible surface/context drawing API on top of Apple Metal.

---

## What it is

`cairometal` implements cairo's drawing model — paths, fills, strokes, clips, groups, patterns/gradients, text, image surfaces, PNG output — with the rasterization running on the **GPU through Metal** instead of cairo's CPU backend. The public Python API mirrors pycairo, so a lot of existing pycairo code works by changing only the import.

It began as the GPU rendering engine inside an offline iOS Python IDE and is published here as a standalone, `pip`-installable package for macOS.

---

## Requirements

| | |
|---|---|
| **OS** | macOS (Apple Silicon). Metal is an Apple framework — there are no Linux/Windows builds. |
| **Python** | 3.10 – 3.14 |
| **GPU** | Any Metal-capable Apple GPU (M-series). |

## Install

```bash
pip install cairometal
```

Wheels are prebuilt per CPython version for macOS `arm64` — there is **no compilation at install time**, you get a binary. (If no matching wheel exists for your interpreter, pip falls back to building the sdist, which needs Xcode's Metal toolchain — see *Building from source*.)

---

## Quick start

```python
import cairometal as cairo

surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 256, 256)
ctx = cairo.Context(surface)

# solid background
ctx.set_source_rgb(0.13, 0.42, 0.96)
ctx.paint()

# a filled rounded shape
ctx.set_source_rgb(1, 1, 1)
ctx.rectangle(48, 48, 160, 160)
ctx.fill()

# text
ctx.set_source_rgb(0.1, 0.1, 0.1)
ctx.move_to(64, 150)
ctx.set_font_size(40)
ctx.show_text("Metal")

surface.write_to_png("out.png")   # rasterized on the GPU
```

### API compatibility

The names mirror pycairo: `ImageSurface`, `Context`, `FORMAT_ARGB32`/`FORMAT_RGB24`/`FORMAT_A8`, `set_source_rgb[a]`, `move_to`/`line_to`/`curve_to`/`close_path`, `rectangle`, `arc`, `fill`/`stroke`/`paint`/`clip`, `save`/`restore`, `translate`/`scale`/`rotate`/`transform`, `set_line_width`/`set_line_cap`/`set_line_join`, `show_text`/`set_font_size`, `push_group`/`pop_group`, gradients, and `write_to_png`. For most drawing code, `import cairometal as cairo` is the only change.

### When it helps (and when it doesn't)

GPU rasterization pays off for **GPU-bound 2D work** — large canvases, heavy compositing/layering, many primitives. For light or typical cairo workloads (small plots, a few shapes, one-off SVG/PDF), the CPU `pycairo` is perfectly fast and simpler — there's no benefit to the GPU round-trip. Use `cairometal` where the rasterization is your bottleneck.

---

## How the package is built (internals)

The importable package is small but wraps a real native engine:

```
cairometal/
  __init__.py          # sets $CM_METALLIB to the bundled lib, then re-exports the ext
  cairo_metal.<abi>.so # the compiled Obj-C / Metal extension
  default.metallib     # compiled Metal shaders (shipped beside the .so)
```

- **The extension** is compiled from `python/cairo_metal_ext.c` (the CPython glue) plus the engine's `src/*.c` (geometry, matrices, raster, regions, patterns, fonts) and `src/*.m` (the Metal/Obj-C surface, device, fill, stroke, paint, clip, group, compose, text, PNG units). It links 11 Apple frameworks: `Metal`, `MetalKit`, `QuartzCore`, `CoreVideo`, `IOSurface`, `Foundation`, `CoreFoundation`, `CoreText`, `CoreGraphics`, `ImageIO`, `UniformTypeIdentifiers`. Built with Obj-C ARC.
- **The shaders** (`shaders/*.metal`) are compiled with `xcrun -sdk macosx metal` + `metallib` into `default.metallib`, shipped as package data.
- **Metallib discovery:** at import, `__init__.py` sets `$CM_METALLIB` to the `default.metallib` sitting beside the extension, so the engine loads it with no configuration. (You can override `$CM_METALLIB` to point at your own.)
- **Submodule, not a renamed symbol:** the extension is built as `cairometal.cairo_metal`, whose init symbol is `PyInit_cairo_metal` (named after the last path component) — exactly what `cairo_metal_ext.c` already exports. So the packaging needs **no change to the C/Obj-C source**.

## Building from source

```bash
# macOS with full Xcode (the Metal compiler `xcrun -sdk macosx metal` must resolve)
git clone -b pip https://github.com/yu314-coder/cairometal
cd cairometal
pip install .            # or: python -m build  (produces a wheel + sdist)
```

`setup.py` compiles the extension and the metallib; if the Metal toolchain isn't available it falls back to the committed `prebuilt/default.metallib`.

## Wheels & releasing

- Wheels are tagged like `cairometal-0.1.0-cp314-cp314-macosx_11_0_arm64.whl` — per-CPython-version (the extension is **not** `abi3`), macOS `arm64`, deployment target 11.0.
- The full **cp310–cp314** matrix is built in CI by [cibuildwheel](https://cibuildwheel.pypa.io/) on a macOS Apple-Silicon runner and published to PyPI via **Trusted Publishing** (OIDC — no API token stored). See [`.github/workflows/wheels.yml`](.github/workflows/wheels.yml); release by pushing a `v*` tag.

---

## Notes & limitations

- **macOS / Apple Silicon only.** `arm64` wheels; the `x86_64` (Intel-Mac) path compiles but is currently untested.
- **`import cairometal`** is the package name. (The in-app/iOS embedding of the same engine imports a top-level `cairo_metal` instead — same code, different packaging.)
- This is an independent reimplementation of a cairo-compatible API, **not** the cairo library or `pycairo`.

## License

MIT — see [LICENSE](LICENSE).
