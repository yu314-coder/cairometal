# CairoMetal

**A pycairo-compatible 2D vector-graphics library that renders on the Apple GPU via Metal.**

CairoMetal is a broad, building re-implementation of the cairo graphics API on top of Metal. The C library exposes **246 `cm_*` functions across 24 source modules**, and the Python extension is a **drop-in for most of pycairo** — `import cairo_metal as cairo` and the usual `ImageSurface` / `Context` / gradients / patterns / text code just works, rendering paths on the GPU with a **stencil-then-cover** pipeline into an **IOSurface-backed `MTLTexture`**.

Enums and matrix layout are **numerically identical to cairo's**, and output is **pixel-diffed against real cairo** (byte-identical on flat fills; anti-aliased-edge-only differences on curves).

```python
import cairo_metal as cairo        # the GPU shim — module is "cairo_metal", never shadows real cairo

surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 400, 300)
ctx = cairo.Context(surface)
ctx.move_to(50, 50); ctx.curve_to(150, 0, 250, 300, 350, 150)
ctx.set_source_rgba(0.2, 0.5, 0.9, 1.0)
ctx.set_line_width(8); ctx.stroke()
surface.write_to_png("out.png")
```

> **Origin / honest scope note.** CairoMetal began inside [OfflinAi / CodeBench](https://github.com/yu314-coder) (an on-device scientific-Python stack for iOS) and grew from a manim-only subset into a general GPU cairo. It is a faithful, GPU-backed cairo — but note it does **not** speed up *manim* specifically: in manim, cairo fill/stroke is ~5% of frame time and the bottleneck is single-threaded Python path interpolation, which no graphics backend can touch. CairoMetal is best thought of as "pixel-accurate cairo, on the GPU," not a manim accelerator.

## Prior art — how this differs

Unlike PyTorch-on-Metal (which exists officially), **cairo has no Metal backend** and there is no real precedent for one. Cairo's backends are image (software), Quartz, Win32, Xlib, and PDF/SVG/PostScript; its only GPU path was OpenGL (`cairo-gl` / glitz), which was **removed in 2022–2023**, and cairo is now in **maintenance-only mode**. The 2D engine that *does* have a Metal backend is **Skia** — a different library, not cairo.

CairoMetal fills that gap: a **pycairo-compatible cairo that renders on Metal**, and it **works on both iOS and macOS** — the same sources build for either (`build.sh` / `python/build.sh` on macOS, `python/build_ios.sh` for iOS). To our knowledge, a GPU/Metal cairo with a pycairo drop-in is novel.

## Features

A broad slice of the cairo API, with cairo-exact semantics and enum values:

- **Surfaces** — `ImageSurface` in `ARGB32`, `RGB24`, `A8`, `A1`, `RGB16_565`; `RecordingSurface`; `create_similar`; **PNG read/write** (`write_to_png` / `ImageSurface.create_from_png`); raw buffer map; zero-copy `IOSurfaceRef` accessor.
- **Context** — `save`/`restore`, `push_group`/`pop_group`(`_to_source`), status.
- **Paths** — `move_to`, `line_to`, `curve_to`, `rel_*`, `arc`, `arc_negative`, `rectangle`, `close_path`, `new_path`/`new_sub_path`, `text_path`, plus `copy_path`/`append_path`, `path_extents`.
- **Fill & stroke** — `fill`(`_preserve`), `stroke`(`_preserve`), `set_fill_rule` (winding **and** even-odd), line width/join/cap/miter, dashes.
- **Sources / patterns** — `set_source_rgb(a)`; `SolidPattern`, `SurfacePattern`, `LinearGradient`, `RadialGradient`, `MeshPattern`; color stops; extend & filter modes.
- **Compositing** — **all 28 operators** (Porter-Duff via fixed-function blend states 0–13; the separable + HSL blend modes 14–27 via programmable-blend cover fragments).
- **Clipping & masking** — `clip`(`_preserve`), `reset_clip`, `clip_extents`, `in_clip`; `mask`, `mask_surface`; `paint`, `paint_with_alpha`.
- **Text** — toy text API (`select_font_face`, `set_font_size`, `show_text`, `text_extents`), `FontOptions`, `ToyFontFace`, `ScaledFont`, glyph paths via FreeType (`cm_ft`).
- **Transforms** — `translate`/`scale`/`rotate`/`transform`/`set_matrix`/`get_matrix`, device↔user conversions, full `Matrix` algebra (multiply/invert/transform point & distance).
- **Regions** — `Region` with the cairo set operations.
- **Queries** — `fill_extents`, `stroke_extents`, `path_extents`, `in_fill`, `in_stroke`.

The Python extension (`python/cairo_metal_ext.c`, 2246 lines) exposes **171 symbols / 18 classes / 20 enums**, with `Context` carrying **91 methods**.

## Requirements

- **macOS** on Apple Silicon (a Metal-capable GPU). The same sources also build for **iOS arm64**.
- **Xcode / Command Line Tools** — `clang`, `swift`, and the Metal toolchain (`xcrun -sdk macosx -f metal` must resolve).
- **Python 3** with dev headers (`python3-config`) for the extension. NumPy is **not** required; Pillow is optional (tests use it to decode-verify PNGs).

## Quick start (macOS)

```bash
git clone https://github.com/yu314-coder/cairometal.git
cd cairometal
./build.sh                      # swift build + compile shaders + render the C demo
bash python/build.sh           # build the cairo_metal CPython extension
```

Then:

```bash
export CM_METALLIB="$PWD/build/default.metallib"
export PYTHONPATH="$PWD/python:$PYTHONPATH"
python3 -c "import cairo_metal as cairo; print('cairo_metal', cairo.version())"
```

## Usage

### Python (pycairo drop-in)

```python
import cairo_metal as cairo

surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 256, 256)
ctx = cairo.Context(surface)

# a linear-gradient filled rounded shape
g = cairo.LinearGradient(0, 0, 256, 256)
g.add_color_stop_rgba(0, 1, 0.3, 0.2, 1)
g.add_color_stop_rgba(1, 0.2, 0.4, 1, 1)
ctx.rectangle(32, 32, 192, 192)
ctx.set_source(g)
ctx.fill_preserve()

# stroke the same path
ctx.set_source_rgba(0, 0, 0, 1)
ctx.set_line_width(6)
ctx.set_line_join(cairo.LINE_JOIN_ROUND)
ctx.stroke()

# text
ctx.select_font_face("Helvetica")
ctx.set_font_size(28)
ctx.move_to(48, 140)
ctx.set_source_rgba(1, 1, 1, 1)
ctx.show_text("CairoMetal")

surface.write_to_png("demo.png")
```

Because the module is named `cairo_metal` (not `cairo`), it never shadows a real pycairo install; you opt in explicitly with `import cairo_metal as cairo`. Enums (`FORMAT_*`, `LINE_JOIN_*`, `LINE_CAP_*`, `OPERATOR_*`, `FILL_RULE_*`, `EXTEND_*`, `FILTER_*`) carry the same integer values as cairo.

### C API

The public C API is [`include/cairo_metal.h`](include/cairo_metal.h) (~1020 lines, 246 `CM_PUBLIC` functions). Every entry point mirrors a cairo call (`cm_image_surface_create`, `cm_context_create`, `cm_move_to`, `cm_curve_to`, `cm_set_source_rgba`, `cm_fill_preserve`, `cm_stroke_preserve`, `cm_surface_write_to_png`, …). `cm_matrix_t` is binary-compatible with `cairo_matrix_t`. `cm_surface_get_iosurface()` returns the `IOSurfaceRef` for zero-copy hand-off (e.g. to VideoToolbox).

## Architecture

```
        your code  /  manim camera  /  pycairo-style Python
                 │  C API  (include/cairo_metal.h)  ·  or the cairo_metal Python ext
                 ▼
   ┌────────────────────────────────────────────────────────────┐
   │ cairo_metal.m   public glue + context state machine + batch  │
   └───┬──────┬──────┬───────┬───────┬───────┬───────┬───────┬────┘
       ▼      ▼      ▼       ▼       ▼       ▼       ▼       ▼
   cm_path cm_fill cm_stroke cm_paint cm_clip cm_compose cm_text cm_pattern …
       └──────┴──────┴───────┴───────┴───────┴───────┴───────┘
                                 ▼
                    cm_device.m + cm_surface.m
        MTLDevice/queue · persistent pipeline & depth-stencil states ·
        triple-buffered ring + dispatch_semaphore · IOSurface-backed
        BGRA8 target + MSAA + stencil
                                 │  zero-copy IOSurfaceRef
                                 ▼
                       e.g. h264_videotoolbox
```

The struct layouts and inter-module function names live in [`src/cm_internal.h`](src/cm_internal.h). Pure-C modules (`cm_matrix.c`, `cm_region.c`, `cm_pattern.c`, `cm_raster.c`, …) hold the math; the Metal/IOSurface plumbing is Objective-C. See [DESIGN.md](DESIGN.md) for the full rationale.

### The stencil-then-cover pipeline

Arbitrary self-intersecting paths with holes are filled with the classic two-pass **stencil-then-cover** technique — no CPU triangulation of concave polygons:

1. **CPU flatten** — cubic Béziers flattened by adaptive de Casteljau, flatness tested in **device space** so on-screen deviation stays under tolerance at any zoom.
2. **Stencil pass** — each contour emits a triangle fan; **winding** uses two-sided increment/decrement-wrap, **even-odd** uses invert-on-low-bit; colour writes masked off.
3. **Cover pass** — the path's bounding quad is drawn; the depth-stencil state tests the stencil **and** resets the touched bits in the same op (no per-path clear). The fragment shader produces the paint (solid, gradient LUT, or a blend-mode cover for operators 14–27).

**Anti-aliasing** is 4× MSAA on colour + stencil; `cm_frame_end` resolves into the IOSurface target. **Strokes** are CPU-expanded into a fillable outline (segment quads + joins + caps, honoring width/join/cap/miter) and run through the same fill.

### Optimizations

Persistent pipeline & depth-stencil states (built once); one command buffer per frame; triple-buffered dynamic buffers gated by a `dispatch_semaphore`; IOSurface-backed target for zero-copy encode; zero per-draw heap allocation (bump-allocated ring); draws grouped by pipeline state.

## Build

### macOS

```bash
./build.sh                 # swift build + shaders -> default.metallib + render demo
./build.sh --clean         # wipe .build/ and build/ first
./build.sh --no-run        # build only
bash python/build.sh       # build just the cairo_metal CPython extension
```

Produces `build/libcairometal.a`, `build/default.metallib`, `build/demo` (+ `build/demo.png`), and `python/cairo_metal.cpython-*-darwin.so`. Individual steps go through the **Makefile**; the source/shader inventory is kept in lock-step with `Package.swift`.

### iOS (arm64)

```bash
bash python/build_ios.sh
```

Cross-compiles the same sources + `fill.metal` + the CPython ext for the `iphoneos` target. Copy the resulting `cairo_metal.cpython-*-iphoneos.so` + `default.metallib` into your app bundle.

### How it finds its Metal kernels at runtime

`cm_device.m` resolves the metallib in three tiers (first wins): `$CM_METALLIB` → the app/main-bundle `default.metallib` (add `shaders/fill.metal` to the app target) → compile `shaders/fill.metal` from source at runtime.

## Tests

```bash
export CM_METALLIB="$PWD/build/default.metallib"
PYTHONPATH="$PWD/python" python3 tests/test_geometry.py     # transforms, paths, matrix algebra
PYTHONPATH="$PWD/python" python3 tests/test_raster.py       # rasterized output checks
PYTHONPATH="$PWD/python" python3 tests/test_robust.py       # edge cases / robustness
PYTHONPATH="$PWD/python" python3 tests/test_reference.py    # pixel-diff vs REAL cairo (needs pycairo)
PYTHONPATH="$PWD/python" python3 python/test_full_shim.py   # full pycairo-shim smoke test
PYTHONPATH="$PWD/python" python3 python/test_gaps.py        # API-gap coverage
```

`tests/test_reference.py` renders each scene with both CairoMetal and **real cairo** (pycairo) and diffs the pixels: **byte-identical on flat fills**, anti-aliased-edge-only differences on curves (±1 LSB premultiplied rounding). The repo also includes GPU smoke scripts (`cairo_gpu_test.py`, `cairo_gpu_full_test.py`, `cairo_gpu_deep_test.py`) used to validate the path on a real Metal device.

## Repository layout

```
include/cairo_metal.h     public C API (246 functions)
src/cairo_metal.m         public glue + context state machine + batching
src/cm_device.m           MTLDevice/queue, persistent states, ring + semaphore
src/cm_surface*.m/.c      IOSurface target, formats, PNG, similar, MSAA resolve
src/cm_path.m             record / adaptive-flatten / tessellate
src/cm_fill.m             stencil-then-cover encode
src/cm_stroke.m           stroke expansion -> fillable polygon
src/cm_paint.m            solid + gradients, 1D LUT bake
src/cm_compose.m          programmable blend modes (operators 14–27)
src/cm_clip.m             clip / mask
src/cm_pattern.c          solid / surface / linear / radial / mesh patterns
src/cm_text.m cm_font.c cm_ft.c   toy text, font options, scaled fonts, FreeType glyphs
src/cm_mesh.c cm_region.c cm_matrix.c cm_raster.c cm_state.c cm_query.c  pure-C helpers
shaders/fill.metal        vertex + stencil/cover/blend fragments
python/cairo_metal_ext.c  CPython extension — pycairo drop-in (171 symbols)
python/build.sh build_ios.sh   macOS / iOS extension builds
build.sh Makefile Package.swift   one-shot / CLI / SwiftPM builds
examples/demo.m           pure-C GPU smoke test
tests/                    geometry / raster / robust / reference (vs real cairo)
```

See **[DESIGN.md](DESIGN.md)** for the design and **[STATUS.md](STATUS.md)** for the running verification state and known gaps.

## License

[MIT](LICENSE) © 2026 Yu Yao-Hsing
