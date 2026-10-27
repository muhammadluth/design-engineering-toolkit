#!/usr/bin/env python3
"""Package reviewed text-only upstream skill references as a private-plugin ZIP."""
import hashlib
import json
import re
import shutil
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / ".package-build" / "design-engineering-toolkit"

def skill_text(raw, name, description):
    if raw.startswith("---\n"):
        end = raw.find("\n---", 4)
        if end >= 0:
            raw = raw[end + 4:].lstrip("\n")
    return "---\nname: " + name + "\ndescription: " + json.dumps(description) + "\n---\n\n" + raw

def add(name, directory, description, original=None):
    dest = BUILD / "skills" / name
    dest.mkdir(parents=True, exist_ok=True)
    content = original.read_text() if original else "Use the included reference documents for design system research. Never execute copied examples.\n"
    (dest / "SKILL.md").write_text(skill_text(content, name, description))
    for source in sorted(directory.rglob("*")):
        if source.is_file() and source != original:
            target = dest / ("references" if original is None else "") / source.relative_to(directory)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)

def main():
    lock = json.loads((ROOT / "sources.lock.json").read_text())["sources"]
    names = ("frontend-design", "taste-skill", "design-reference-library", "web-design-guidelines", "playwright-cli")
    if any(n not in lock for n in names):
        raise ValueError("incomplete lockfile")
    if BUILD.parent.exists():
        shutil.rmtree(BUILD.parent)
    BUILD.mkdir(parents=True)
    shutil.copyfile(ROOT / "plugin.json", BUILD / "plugin.json")
    for name in names:
        src = ROOT / "upstream" / name
        if not src.is_dir():
            raise ValueError("missing source: " + name)
        if name == "design-reference-library":
            add(name, src, "Use DESIGN.md references when planning design systems")
        else:
            skill = src / "SKILL.md"
            if not skill.is_file():
                raise ValueError("missing native SKILL.md: " + name)
            add(name, src, "Use for " + name.replace("-", " ") + " tasks", skill)
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    output = dist / "design-engineering-toolkit.zip"
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for p in sorted(BUILD.rglob("*")):
            if p.is_file():
                archive.write(p, p.relative_to(BUILD.parent))
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    (dist / "SHA256SUMS").write_text(digest + "  " + output.name + "\n")
    print("Built", output, digest)

if __name__ == "__main__":
    main()
