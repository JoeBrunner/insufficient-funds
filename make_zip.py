#!/usr/bin/env python3
"""Deterministic Claude app package. Only the four runtime files ship."""
from pathlib import Path
import zipfile

NAME = "insufficient-funds"
ROOT = Path(__file__).resolve().parent
SKILL = ROOT / "skills" / NAME
OUT = ROOT / (NAME + ".zip")
FIXED_TIME = (2026, 10, 15, 0, 0, 0)
FILES = ("SKILL.md", "categories.md", "scripts/funds.py", "scripts/make_xlsx.py")


def build(out=OUT):
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as archive:
        for name in sorted(FILES):
            info = zipfile.ZipInfo(NAME + "/" + name, FIXED_TIME)
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (SKILL / name).read_bytes())
    return Path(out)


if __name__ == "__main__":
    print(build())
