#!/usr/bin/env python3
"""Fetch commit-pinned text snapshots. Never execute upstream content."""
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {".md", ".mdx", ".txt", ".yaml", ".yml", ".json"}
SKIP = {".git", ".github", "node_modules", "dist", "build", ".venv", "__pycache__"}
MAX_FILE = 1024 * 1024
MAX_FILES = 500
MAX_TOTAL = 18 * 1024 * 1024

def main():
    specs = json.loads((ROOT / "sources.json").read_text())["sources"]
    staging = ROOT / ".sync-staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir()
    lock = {"schema": 1, "sources": {}}
    try:
        for spec in specs:
            name, repo, ref, sub = (spec[k] for k in ("name", "repo", "ref", "path"))
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
                raise ValueError("invalid source name")
            if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
                raise ValueError("invalid repository")
            with tempfile.TemporaryDirectory() as tmp:
                checkout = Path(tmp) / "repo"
                subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "clone", "--depth", "1",
                                "--single-branch", "--branch", ref, "--no-checkout",
                                "https://github.com/" + repo + ".git", str(checkout)], check=True)
                subprocess.run(["git", "-C", str(checkout), "-c", "core.hooksPath=/dev/null",
                                "checkout", "-f", "HEAD"], check=True)
                sha = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
                source = (checkout / sub).resolve()
                if not source.is_relative_to(checkout.resolve()) or not source.is_dir():
                    raise ValueError("missing or unsafe source directory")
                files = [p for p in sorted(source.rglob("*"))
                         if p.is_file() and not p.is_symlink()
                         and p.suffix.lower() in ALLOWED
                         and not any(part in SKIP for part in p.relative_to(source).parts)]
                if not files or len(files) > MAX_FILES or sum(p.stat().st_size for p in files) > MAX_TOTAL:
                    raise ValueError("source file count/size requires manual curation: " + name)
                digest = hashlib.sha256()
                for p in files:
                    rel = p.relative_to(source)
                    data = p.read_bytes()
                    if len(data) > MAX_FILE:
                        raise ValueError("oversized upstream file: " + str(rel))
                    data.decode("utf-8")
                    target = staging / name / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
                    digest.update(str(rel).encode() + b"\\0" + data + b"\\0")
                lock["sources"][name] = {"repo": repo, "commit": sha, "path": sub,
                                         "files": len(files), "sha256": digest.hexdigest()}
                print(name, sha, len(files))
        final = ROOT / "upstream"
        if final.exists():
            shutil.rmtree(final)
        staging.rename(final)
        (ROOT / "sources.lock.json").write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")
    finally:
        if staging.exists():
            shutil.rmtree(staging)

if __name__ == "__main__":
    main()
