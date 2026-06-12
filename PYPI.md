# cairometal

**A [pycairo](https://pycairo.readthedocs.io/)-compatible 2D vector-graphics library that rasterizes on the Apple GPU via Metal.**

> ⚠️ **Independent project — not affiliated with the [cairo](https://cairographics.org) graphics library or the official `pycairo` binding.** `cairometal` re-implements a cairo-compatible surface/context drawing API on top of Apple Metal; it does not wrap or link the cairo C library.

```bash
pip install cairometal
```

```python
import cairometal as cairo

s = cairo.ImageSurface(cairo.FORMAT_ARGB32, 256, 256)
ctx = cairo.Context(s)
ctx.set_source_rgb(0.13, 0.42, 0.96); ctx.paint()      # GPU
ctx.set_source_rgb(1, 1, 1); ctx.rectangle(48, 48, 160, 160); ctx.fill()
s.write_to_png("out.png")
```

---

## At a glance

| | |
|---|---|
| **What** | cairo's 2D drawing model (paths, fills, strokes, gradients, text, clips, groups, PNG) rasterized on the GPU through Metal |
| **Platform** | macOS, Apple Silicon (`arm64`) |
| **Python** | 3.10 – 3.14 (per-version wheels; the extension is *not* `abi3`) |
| **Install** | prebuilt wheels — no compiler needed at install time |
| **API** | mirrors pycairo — for most code, `import cairometal as cairo` is the only change |
| **License** | MIT |

It began as the GPU rendering engine inside an offline iOS Python IDE (where cairo is used for plotting and animation), and is published here as a standalone, `pip`-installable package for the desktop.

---

## Installation

```bash
pip install cairometal
```

- Wheels are published **per CPython version** for **macOS `arm64`** — you get a prebuilt binary, nothing is compiled at install time.
- If pip can't find a wheel for your interpreter it falls back to building the **sdist**, which requires a macOS host with **full Xcode** (the Metal shader compiler `xcrun -sdk macosx metal` must resolve). See [Building from source](#building-from-source).
- There are **no** Linux or Windows builds — Metal is an Apple-only framework.

---

## Capabilities

`cairometal` implements cairo's imaging model. The drawing primitives are executed on the GPU; surface I/O and geometry are handled on the CPU.

| Area | Supported |
|---|---|
| **Surfaces** | `ImageSurface` (ARGB32 / RGB24 / A8), recording surface, `create_similar` |
| **Context state** | `save`/`restore` stack, source color/pattern, line width/cap/join/dash, fill rule, operators |
| **Paths** | `move_to`, `line_to`, `curve_to`, `rel_*`, `arc`/`arc_negative`, `rectangle`, `close_path`, path copy/append |
| **Painting** | `fill`, `stroke`, `paint`, `paint_with_alpha`, `clip` (GPU stencil-then-cover) |
| **Patterns** | solid, `LinearGradient`, `RadialGradient`, surface patterns, **mesh gradients** |
| **Groups** | `push_group` / `pop_group[_to_source]` (off-screen layers composited on the GPU) |
| **Compositing** | Porter-Duff operators (over, in, out, atop, …) |
| **Text** | `select_font_face`, `set_font_size`, `show_text`, `text_path`, font/text extents (CoreText-backed) |
| **Transforms** | `translate`, `scale`, `rotate`, `transform`, full affine `Matrix` |
| **Output** | `write_to_png`, direct pixel access, IOSurface-backed buffers |

> Names mirror pycairo. Porting existing pycairo code is usually just the import line; if a specific symbol is missing, please open an issue.

### When the GPU helps (and when it doesn't)

GPU rasterization pays off for **GPU-bound 2D work** — large canvases, heavy compositing and layering, many primitives, repeated redraws. For light or typical cairo workloads (a small plot, a few shapes, one-off SVG/PDF), the CPU `pycairo` is just as fast and simpler — there's no benefit to the CPU↔GPU round-trip, and possibly a small cost. Reach for `cairometal` where **rasterization is your bottleneck**.

---

## Migrating from pycairo

```python
# before
import cairo
# after
import cairometal as cairo
```

The surface/context/pattern/matrix API and the `FORMAT_*` / `OPERATOR_*` / `FONT_*` constants are named as in pycairo. Differences to expect: macOS/arm64 only, text uses CoreText font lookup (so available faces match the system), and very new or rarely-used cairo entry points may not be implemented yet.

---

## How it works (internals)

The installed package is small but wraps a real native engine:

```
cairometal/
  __init__.py            # sets $CM_METALLIB to the bundled lib, then re-exports the ext
  cairo_metal.<abi>.so   # the compiled Obj-C / Metal extension (~24 cm_* units)
  default.metallib       # the precompiled Metal shaders, shipped beside the .so
```

- **The extension** is compiled from the CPython glue `cairo_metal_ext.c` plus the engine units: C sources (`cm_matrix`, `cm_raster`, `cm_region`, `cm_pattern`, `cm_mesh`, `cm_state`, `cm_query`, `cm_font`, `cm_ft`, `cm_surface_format/similar`) and Obj-C/Metal sources (`cm_surface`, `cm_device`, `cm_path`, `cm_fill`, `cm_stroke`, `cm_paint`, `cm_clip`, `cm_group`, `cm_compose`, `cm_text`, `cm_recording`, `cm_surface_png`). It is built with Obj-C ARC and links 11 Apple frameworks: `Metal`, `MetalKit`, `QuartzCore`, `CoreVideo`, `IOSurface`, `Foundation`, `CoreFoundation`, `CoreText`, `CoreGraphics`, `ImageIO`, `UniformTypeIdentifiers`.
- **Shaders** (`shaders/*.metal`) are compiled with `xcrun -sdk macosx metal` + `metallib` into `default.metallib`, shipped as package data.
- **Metallib discovery:** at import, `__init__.py` sets `$CM_METALLIB` to the `default.metallib` next to the extension, so the engine loads it with zero configuration. The engine's lookup order is `$CM_METALLIB` → the app/main-bundle default library → compile-from-source; you can override `$CM_METALLIB` to point at your own.
- **Why `import cairometal` works without a C edit:** the extension is built as the submodule **`cairometal.cairo_metal`**, whose init symbol is `PyInit_cairo_metal` (named after the last path component) — exactly what `cairo_metal_ext.c` already exports. So the same source serves both the desktop package and the iOS embedding (which imports a top-level `cairo_metal`) with no source change.
- **Rendering approach:** stencil-then-cover path filling, IOSurface-backed surfaces, GPU compositing for groups/clips.

---

## Building from source

```bash
# macOS + full Xcode (the Metal toolchain must be present)
git clone -b pip https://github.com/yu314-coder/cairometal
cd cairometal
pip install .                  # or: python -m build   (wheel + sdist)
```

`setup.py` compiles the extension and the metallib. If the Metal toolchain isn't available it falls back to the committed `prebuilt/default.metallib`. To build a single-arch / pinned-deployment-target wheel:

```bash
MACOSX_DEPLOYMENT_TARGET=11.0 ARCHFLAGS="-arch arm64" python -m build --wheel
```

---

## Wheels & releasing

- Wheels are tagged e.g. `cairometal-0.1.0-cp314-cp314-macosx_11_0_arm64.whl` — per-CPython version, macOS `arm64`, deployment target 11.0.
- The full **cp310–cp314** matrix is built in CI by [cibuildwheel](https://cibuildwheel.pypa.io/) on a macOS Apple-Silicon runner and published to PyPI via **Trusted Publishing** (OIDC — no API token stored). See [`.github/workflows/wheels.yml`](.github/workflows/wheels.yml); release by pushing a `v*` tag. (To add wheels to an *already-published* version, the publish step needs `skip-existing: true`.)

---

## Origin

`cairometal` is the desktop release of a GPU cairo engine originally written for an iOS Python environment, where it provides a Metal-backed cairo for plotting/animation libraries. The same engine ships inside that app imported as a top-level `cairo_metal`; this package repackages it for macOS as `import cairometal`.

## Limitations & notes

- **macOS / Apple Silicon only.** `arm64` wheels; the `x86_64` (Intel-Mac) path compiles but is currently untested.
- **Per-version wheels** (not `abi3`) — install the wheel matching your Python.
- Independent re-implementation of a cairo-compatible API — **not** the cairo library or `pycairo`.
- Missing an entry point you need? Open an issue at the repo.

## License

MIT © 2026 Yu Yao-Hsing — see [LICENSE](LICENSE).
