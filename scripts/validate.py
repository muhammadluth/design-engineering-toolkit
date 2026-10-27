#!/usr/bin/env python3
"""Validate plugin archive layout, manifests and sizes (not a security audit)."""
import json
from pathlib import Path
from zipfile import ZipFile
ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / "plugin.json").read_text())
assert manifest["$schema"] == "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
assert len(manifest["extensions"]["com.openai"]["interface"]["shortDescription"]) <= 30
path = ROOT / "dist" / "design-engineering-toolkit.zip"
with ZipFile(path) as z:
    entries = z.namelist()
    assert len(entries) == len(set(entries))
    assert all(n.startswith("design-engineering-toolkit/") and ".." not in Path(n).parts for n in entries)
    skills = [n for n in entries if n.endswith("/SKILL.md")]
    assert len(skills) == 5, skills
    assert all(z.getinfo(n).file_size <= 1024 * 1024 for n in entries)
    for n in skills:
        text = z.read(n).decode("utf-8")
        assert text.startswith("---\n") and "\nname: " in text and "\ndescription: " in text
print("PASS: five skill files and valid basic archive layout")
