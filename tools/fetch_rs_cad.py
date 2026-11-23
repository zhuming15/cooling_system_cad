"""Download and unpack an RS / TraceParts 3D-viewer model into a scratch directory.

The link has to be found in a browser first (RS product pages refuse plain
fetch tools):
  1. Open https://sg.rs-online.com/web/services/product/cad-download/3DViewer?articleId=<RS no.>
  2. In the network log, open the `api/v/path` response; it holds a presigned
     S3 URL to a zip (valid for about 15 minutes).
Then:
    uv run python tools/fetch_rs_cad.py "<S3 URL>" <scratch dir>

The zip is unpacked into a new, empty folder <scratch dir>/<zip name>/ and the
Three.js mesh files (`*_000.bin`) are listed, ready for tools/cad_compare.py.
Nothing from the zip is executed. Keep the scratch directory outside the repo.
Some RS parts have no 3D model (the viewer then has no `api/v/path` call).
"""

from __future__ import annotations

import sys
import urllib.request
import zipfile
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]


def fetch(url: str, scratch: Path) -> list[Path]:
    if urlparse(url).scheme != "https":
        raise SystemExit("expected an https presigned URL")
    scratch = scratch.resolve()
    if scratch == ROOT or ROOT in scratch.parents:
        raise SystemExit("keep vendor files outside the repo (AGENTS.md)")
    name = Path(urlparse(url).path).stem or "rs_model"
    dest = scratch / name
    dest.mkdir(parents=True, exist_ok=False)  # a new, empty folder per download
    zpath = dest / f"{name}.zip"
    req = urllib.request.Request(url, headers={"User-Agent": "cad-fetch/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r, open(zpath, "wb") as f:
        f.write(r.read())
    with zipfile.ZipFile(zpath) as z:
        for member in z.namelist():  # refuse paths that would leave dest
            target = (dest / member).resolve()
            if dest not in target.parents and target != dest:
                raise SystemExit(f"unsafe path in zip: {member}")
        z.extractall(dest)
    meshes = sorted(dest.rglob("*_000.bin"))
    print(f"unpacked into {dest}")
    for m in meshes:
        print(f"  mesh: {m}")
    if not meshes:
        print("  no *_000.bin mesh found; list the folder to see what the zip holds")
    return meshes


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    fetch(sys.argv[1], Path(sys.argv[2]))
