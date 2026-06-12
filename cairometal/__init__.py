"""cairometal — a pycairo-compatible 2D vector-graphics backend that renders on
the Apple GPU via Metal.

Independent project. NOT affiliated with the cairo graphics library
(cairographics.org) or the official `pycairo` binding — it reimplements a
compatible surface/context API on top of Metal.

macOS only (Metal is an Apple framework). Usage mirrors pycairo:

    import cairometal as cairo
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 256, 256)
    ctx = cairo.Context(surface)
    ctx.set_source_rgb(0.2, 0.6, 1.0)
    ctx.paint()
    surface.write_to_png("out.png")
"""
import os as _os

# Point the native extension at the metallib we ship beside it, before it loads.
# (The extension's discovery order is: $CM_METALLIB -> main-bundle -> source.)
_os.environ.setdefault(
    "CM_METALLIB",
    _os.path.join(_os.path.dirname(__file__), "default.metallib"),
)

from .cairo_metal import *        # noqa: E402,F401,F403

try:                              # surface __all__/__doc__ if the ext defines them
    from .cairo_metal import __all__, __doc__  # noqa: E402,F401
except ImportError:
    pass

del _os
