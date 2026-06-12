"""Build cairometal as a macOS wheel.

Layout produced:
    cairometal/__init__.py          (sets $CM_METALLIB, re-exports the ext)
    cairometal/cairo_metal.<abi>.so (the compiled Obj-C / Metal extension)
    cairometal/default.metallib     (compiled shaders, shipped as package data)

The extension is the *submodule* `cairometal.cairo_metal`, whose init symbol is
`PyInit_cairo_metal` (named after the last path component) — i.e. exactly the
symbol `python/cairo_metal_ext.c` already exports. So this packaging needs NO
change to the C/Obj-C source.

Requires a macOS host with full Xcode (`xcrun -sdk macosx metal` must resolve).
If the Metal toolchain is unavailable, the committed `build/default.metallib`
is shipped as a fallback.
"""
import glob
import os
import shutil
import subprocess

from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext

HERE = os.path.dirname(os.path.abspath(__file__))

FRAMEWORKS = [
    "Metal", "MetalKit", "QuartzCore", "CoreVideo", "IOSurface", "Foundation",
    "CoreFoundation", "CoreText", "CoreGraphics", "ImageIO", "UniformTypeIdentifiers",
]
_fw_link = [arg for fw in FRAMEWORKS for arg in ("-framework", fw)]

# Python C glue + the engine's C units (src/*.c) + the Obj-C/Metal units
# (src/*.m). This mirrors the Makefile's C_SRCS + OBJC_SRCS. The compiler picks
# C vs Obj-C by file extension; -fobjc-arc is a harmless unused-arg warning on
# the .c files (silenced via -Wno-unused-command-line-argument).
SOURCES = (["python/cairo_metal_ext.c"]
           + sorted(glob.glob("src/*.c"))
           + sorted(glob.glob("src/*.m")))

ext = Extension(
    "cairometal.cairo_metal",
    sources=SOURCES,
    include_dirs=["include", "src"],   # cairo_metal.h lives in include/, cm_internal.h in src/
    extra_compile_args=["-fobjc-arc", "-fobjc-weak", "-O2",
                        "-Wno-deprecated-declarations", "-Wno-unused-command-line-argument"],
    extra_link_args=_fw_link,
)


class build_ext_metallib(build_ext):
    """After building the extension, compile shaders/*.metal into the package."""

    def run(self):
        super().run()
        out_dir = os.path.join(self.build_lib, "cairometal")
        os.makedirs(out_dir, exist_ok=True)
        target = os.path.join(out_dir, "default.metallib")
        if self._compile_metallib(target):
            return
        # Fallback: ship the committed prebuilt metallib (for CI without the
        # Metal toolchain). NOTE: deliberately NOT named build/ — that collides
        # with setuptools' scratch dir and can shadow pypa-build at invocation.
        cand = "prebuilt/default.metallib"
        if os.path.exists(os.path.join(HERE, cand)):
            shutil.copyfile(os.path.join(HERE, cand), target)
            self.announce(f"[cairometal] used prebuilt {cand}", level=2)
            return
        raise SystemExit("cairometal: no Metal toolchain and no prebuilt/default.metallib")

    def _compile_metallib(self, target) -> bool:
        metals = sorted(glob.glob(os.path.join(HERE, "shaders", "*.metal")))
        if not metals:
            return False
        try:
            airs = []
            os.makedirs(self.build_temp, exist_ok=True)
            for m in metals:
                air = os.path.join(self.build_temp, os.path.basename(m) + ".air")
                subprocess.check_call(["xcrun", "-sdk", "macosx", "metal", "-c", m, "-o", air])
                airs.append(air)
            subprocess.check_call(["xcrun", "-sdk", "macosx", "metallib", *airs, "-o", target])
            self.announce(f"[cairometal] compiled {len(metals)} shader(s) -> default.metallib", level=2)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False


setup(
    packages=["cairometal"],
    package_dir={"cairometal": "cairometal"},
    package_data={"cairometal": ["default.metallib"]},
    ext_modules=[ext],
    cmdclass={"build_ext": build_ext_metallib},
    include_package_data=True,
)
