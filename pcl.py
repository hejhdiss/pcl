#!/usr/bin/env python3
"""pcl.py – Minimal proof‑of‑concept compiler/runner for PCL (Python‑C Linked) files.

USAGE
-----
$ python pcl.py run   hello.pcl      # extract, build, then run __pcl_main__.py
$ python pcl.py build hello.pcl      # extract & build only (no execution)
$ python pcl.py clean hello.pcl      # delete generated build/ dist/

"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
CC = os.environ.get("PCLC_CC", "gcc")
CFLAGS = ["-shared", "-fPIC", "-O3", "-Wall", "-Werror"]

BLOCK_RE = re.compile(r"%(?P<kind>c|py)(?P<meta>[^\n]*)\n(.*?)%end(?P=kind)", re.S)
META_KV_RE = re.compile(r"(\w+)=([\w,]+)")

TEMP = tempfile.gettempdir()

# ---------------------------------------------------------------------------
# Core compiler stages
# ---------------------------------------------------------------------------

def parse_pcl(source: str):
    """Return list of blocks with metadata and body."""
    blocks = []
    for m in BLOCK_RE.finditer(source):
        kind = m.group("kind")
        raw_meta = m.group("meta")
        body = m.group(3)
        meta = {}
        for k, v in META_KV_RE.findall(raw_meta):
            meta[k] = v
        # normalise comma lists
        for key in ("export", "import"):
            if key in meta:
                meta[key] = [x.strip() for x in meta[key].split(",") if x.strip()]
        blocks.append({"kind": kind, "meta": meta, "body": body})
    return blocks


def write_sources(pcl_path: Path, blocks):
    root = pcl_path.with_suffix("")  # without .pcl
    build_dir = root / "build"
    dist_dir = root / "dist"
    build_dir.mkdir(parents=True, exist_ok=True)
    dist_dir.mkdir(parents=True, exist_ok=True)

    manifest = {"c": [], "py": []}

    for idx, blk in enumerate(blocks):
        if blk["kind"] == "c":
            name = blk["meta"].get("name", f"cmod_{idx}")
            c_file = build_dir / f"{name}.c"
            c_file.write_text(blk["body"])
            blk["path"] = c_file
            # Store path as string for JSON
            manifest["c"].append({
                "meta": blk["meta"],
                "path": str(c_file)
            })
        else:
            blk["path"] = None
            manifest["py"].append({
                "meta": blk["meta"],
                "body": blk["body"]
            })

    (build_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return build_dir, dist_dir, manifest



def compile_c_modules(build_dir: Path, manifest):
    """Build every extracted C block into a shared object (.so)."""
    so_paths = {}
    for blk in manifest["c"]:
        name    = blk["meta"].get("name")
        c_path  = blk["path"]
        so_path = build_dir / f"{name}.so"

        # NOTE: do **not** hide symbols unless the user explicitly asks for it.
        extra_visibility_flags = []
        if blk["meta"].get("hide", "no").lower() == "yes":
            extra_visibility_flags.append("-fvisibility=hidden")

        cmd = [
            CC,
            *CFLAGS,          # -shared -fPIC -O3 -Wall -Werror
            *extra_visibility_flags,
            "-o", str(so_path),
            str(c_path),
        ]

        print("[CC]", " ".join(cmd))
        subprocess.check_call(cmd)
        so_paths[name] = so_path

    return so_paths



import ctypes

# ... your existing imports and code ...

def gen_ctypes_wrapper(build_dir: Path, blk, so_path: Path):
    name = blk["meta"].get("name")
    exports = blk["meta"].get("export", [])

    # Helper code for error handling and memory ownership
    helper_code = """
from ctypes import *
import sys

# Error code to Python exception helper
class PCLCError(Exception):
    pass

def check_error_code(code):
    if code != 0:
        raise PCLCError(f"Error code: {code}")

# Memory ownership helpers
def ptr_to_bytes(ptr, length):
    return string_at(ptr, length)

def bytes_to_ptr(data):
    buf = create_string_buffer(data)
    return cast(buf, c_void_p), buf  # return buf to keep alive

"""

    wrapper_lines = [
        "from ctypes import *",
        "from pathlib import Path",
        f"lib = CDLL(str(Path(__file__).parent / '{so_path.name}'))",
        helper_code,
        ""
    ]

    # We'll attempt simple detection of global variables and structs/enums by naming conventions or exports.
    # For this POC, assume user explicitly exports globals and callback function types via 'export' metadata.

    # Exported functions, variables, structs/enums
    for sym in exports:
        # Simple heuristic: if name ends with "_cb", treat as callback function pointer type
        if sym.endswith("_cb"):
            # Assume callback signature: int callback(int)
            wrapper_lines.append(f"# Callback type for {sym}")
            wrapper_lines.append(f"{sym} = CFUNCTYPE(c_int, c_int)")
            continue

        # For global variables, user names them as "g_<name>" or marks them explicitly in meta.
        # Try to detect global variables with 'global_vars' key (optional).
        # We'll wrap them with .in_dll(lib, 'symbol')

        # For this minimal POC, assume anything starting with 'g_' is a global variable of type int.
        if sym.startswith("g_"):
            wrapper_lines.append(f"{sym} = c_int.in_dll(lib, '{sym}')")
            continue

        # For structs or enums: user should manually add a separate .py file for structs if complex.
        # For demonstration, if sym ends with "_struct" or "_enum", define placeholder ctypes.Structure or enum.IntEnum
        if sym.endswith("_struct"):
            wrapper_lines.append(f"class {sym}(Structure):")
            wrapper_lines.append(f"    _fields_ = []  # TODO: fill with actual struct fields")
            wrapper_lines.append(f"{sym}_ptr = POINTER({sym})")
            continue

        if sym.endswith("_enum"):
            wrapper_lines.append(f"# Enum {sym} placeholder")
            wrapper_lines.append(f"class {sym}(c_int):")
            wrapper_lines.append(f"    pass  # TODO: add enum values")
            continue

        # Otherwise, treat as function pointer or variable symbol
        wrapper_lines.append(f"{sym} = lib.{sym}")
        wrapper_lines.append(f"{sym}.restype = c_int  # default restype, override as needed")

        # Attach an errcheck only if the user opted-in (meta flag) or the symbol
        # name suggests it returns an error/status code.
        wants_errcheck = (
            blk["meta"].get("errcheck", "no").lower() == "yes"
            or sym.startswith(("rc_", "status_", "err_"))
        )
        if wants_errcheck:
            wrapper_lines.append(
                f"{sym}.errcheck = "
                "lambda result, func, args: check_error_code(result) or result"
            )

    wrapper_file = build_dir / f"{name}_wrapper.py"
    wrapper_file.write_text("\n".join(wrapper_lines))
    return wrapper_file




def stitch_python(build_dir: Path, manifest, so_paths):
    parts = ["import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).parent))"]
    for blk in manifest["py"]:
        reqs = blk["meta"].get("requires", "").split(",") if blk["meta"].get("requires") else []
        for req in reqs:
            req = req.strip()
            if not req:
                continue
            parts.append(f"from {req}_wrapper import *  # auto-imported")
        parts.append(blk["body"])
    main_py = build_dir / "__pcl_main__.py"
    main_py.write_text("\n\n".join(parts))
    return main_py


def package_onefile(dist_dir: Path, main_py: Path, build_dir: Path):
    # Ensure __main__.py exists in build_dir
    main_stub = build_dir / "__main__.py"
    main_stub.write_text("import __pcl_main__\n")

    zipapp_path = dist_dir / f"{build_dir.parent.name}_onefile.pyz"
    zip_path = dist_dir / f"{build_dir.parent.name}_onefile.zip"

    shutil.make_archive(str(zip_path).replace(".zip", ""), "zip", root_dir=build_dir)

    zip_path.rename(zipapp_path)
    print("[PKG] Created", zipapp_path)



# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cli():
    ap = argparse.ArgumentParser(description="Minimal PCL compiler")
    ap.add_argument("command", choices=["run", "build", "clean"], help="{[extract, build, then run __pcl_main__.py],[extract & build only (no execution)],[delete generated build/ dist/]}")
    ap.add_argument("file", help=".pcl source file")
    ap.add_argument("--onefile", action="store_true", help="create .pyz archive")
    args = ap.parse_args()

    pcl_path = Path(args.file).resolve()
    if args.command == "clean":
        shutil.rmtree(pcl_path.with_suffix("") / "build", ignore_errors=True)
        shutil.rmtree(pcl_path.with_suffix("") / "dist", ignore_errors=True)
        print("[CLEAN] removed build/ and dist/")
        return

    source = pcl_path.read_text()
    blocks = parse_pcl(source)
    build_dir, dist_dir, manifest = write_sources(pcl_path, blocks)
    so_paths = compile_c_modules(build_dir, manifest)

    # generate wrappers
    for blk in manifest["c"]:
        name = blk["meta"].get("name")
        gen_ctypes_wrapper(build_dir, blk, so_paths[name])

    main_py = stitch_python(build_dir, manifest, so_paths)

    if args.onefile:
        package_onefile(dist_dir, main_py, build_dir)

    if args.command == "run":
        print("[RUN] python", main_py)
        subprocess.check_call([sys.executable, str(main_py)])


if __name__ == "__main__":
    cli()