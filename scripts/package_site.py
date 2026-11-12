"""Package the shop for upload to a PHP web host.

Builds:
  dist/lenscart_site.zip  everything in site/ that the site needs, under a top-level lenscart/ folder
  dist/lenscart_db.sql    schema + seed in one file, for a phpMyAdmin import on the host

Left out: site/CREDENTIALS.local.txt (demo passwords), site/README.md, test pages (ai/test.html),
Python/Git leftovers. Test-mode images in img/test/ ARE included (model.php uses them).

Run:  .venv\\Scripts\\python scripts\\package_site.py
"""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
DIST = ROOT / "dist"
TOP = "lenscart"

EXCLUDE_FILES = {"CREDENTIALS.local.txt", "README.md", "ai/test.html"}
EXCLUDE_PARTS = {".git", "__pycache__", ".ipynb_checkpoints"}
EXCLUDE_SUFFIX = {".pyc", ".bak", ".tmp", ".log"}
# a file is required if the site cannot work without it: fail loudly when one is missing
REQUIRED = ["index.php", "inc/db.php", "inc/config.php", "ai/lensai.js", "ai/lensnet.onnx", "ai/lensnet_meta.json",
            "ai/vendor/ort.min.js", "ai/vendor/ort-wasm-simd-threaded.wasm", "ai/vendor/ort-wasm-simd-threaded.mjs",
            "vendor/chart.umd.min.js", "data/model_report.json", "sql/schema.sql", "sql/seed.sql"]
REQUIRED_DIRS = {"img/products": 1500, "img/test": 1, "img/model": 1}


def wanted(rel: str) -> bool:
    p = Path(rel)
    return (rel not in EXCLUDE_FILES and not (set(p.parts) & EXCLUDE_PARTS) and p.suffix.lower() not in EXCLUDE_SUFFIX)


def main():
    missing = [r for r in REQUIRED if not (SITE / r).is_file()]
    for d, n in REQUIRED_DIRS.items():
        if len(list((SITE / d).glob("*"))) < n:
            missing.append(f"{d}/ (expected at least {n} files)")
    if missing:
        raise SystemExit("Missing, not packaging:\n  " + "\n  ".join(missing))

    DIST.mkdir(exist_ok=True)
    files = sorted(f for f in SITE.rglob("*") if f.is_file() and wanted(f.relative_to(SITE).as_posix()))
    zpath = DIST / "lenscart_site.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for f in files:
            z.write(f, f"{TOP}/{f.relative_to(SITE).as_posix()}")

    sql = DIST / "lenscart_db.sql"
    sql.write_text("-- LensCart database: schema + seed in one file. Import into an EMPTY database.\n"
                   + (SITE / "sql" / "schema.sql").read_text(encoding="utf-8") + "\n"
                   + (SITE / "sql" / "seed.sql").read_text(encoding="utf-8"), encoding="utf-8")

    # sanity: nothing secret slipped in, and the zip opens
    with zipfile.ZipFile(zpath) as z:
        names = z.namelist()
        assert z.testzip() is None
    assert not any(n.endswith(("CREDENTIALS.local.txt", "README.md", "test.html")) for n in names)
    assert all(n.startswith(TOP + "/") for n in names)

    raw = sum(f.stat().st_size for f in files)
    mb = lambda b: f"{b / 1024 / 1024:.1f} MB"
    print(f"{zpath.relative_to(ROOT)}: {len(names)} files, {mb(zpath.stat().st_size)} zipped ({mb(raw)} unzipped)")
    print(f"{sql.relative_to(ROOT)}: {mb(sql.stat().st_size)}")
    print("10 largest files:")
    for f in sorted(files, key=lambda f: f.stat().st_size, reverse=True)[:10]:
        print(f"  {mb(f.stat().st_size):>8}  {TOP}/{f.relative_to(SITE).as_posix()}")


if __name__ == "__main__":
    main()
