#!/usr/bin/env python3
"""
Dump repository code into a single TXT:
- First: a project tree
- Then: each file's relative path followed by its contents
- Honors .gitignore (prefers `git ls-files -co --exclude-standard -z`)
- Skips suspected binary files (NUL-byte heuristic)
"""

import os
import sys
import shutil
import subprocess
import pathlib
from typing import List
from collections import defaultdict

OUTPUT_NAME = "project_code.txt"


def in_git_repo(root: pathlib.Path) -> bool:
    return (root / ".git").exists()


def get_files_via_git(root: pathlib.Path) -> List[pathlib.Path]:
    # tracked + untracked, excluding ignored; NUL-delimited for safety
    cmd = ["git", "ls-files", "-z", "-co", "--exclude-standard"]
    out = subprocess.check_output(cmd, cwd=root)
    items = [p for p in out.decode("utf-8", "replace").split("\0") if p]
    return [root / p for p in items]


def get_files_via_lib(root: pathlib.Path) -> List[pathlib.Path]:
    """
    Fallback if not a Git repo or Git unavailable:
    - Try gitignore_parser
    - Then try pathspec
    - Else walk and omit common VCS/venv dirs
    """
    gi = root / ".gitignore"

    # Try gitignore_parser (spec-compliant)
    if gi.exists():
        try:
            from gitignore_parser import parse_gitignore  # type: ignore
            matches = parse_gitignore(str(gi))
            paths = []
            for dirpath, dirnames, filenames in os.walk(root):
                # prune VCS dirs
                if os.path.basename(dirpath) == ".git":
                    dirnames[:] = []
                    continue
                for name in filenames:
                    fp = pathlib.Path(dirpath) / name
                    if matches(str(fp)):
                        continue
                    paths.append(fp)
            return [p for p in paths if p.is_file()]
        except Exception:
            pass

        # Try pathspec (gitwildmatch)
        try:
            from pathspec import PathSpec  # type: ignore
            patterns = gi.read_text(encoding="utf-8", errors="ignore").splitlines()
            spec = PathSpec.from_lines("gitwildmatch", patterns)
            paths = []
            for dirpath, dirnames, filenames in os.walk(root):
                if os.path.basename(dirpath) == ".git":
                    dirnames[:] = []
                    continue
                for name in filenames:
                    rel = os.path.relpath(os.path.join(dirpath, name), start=root)
                    if spec.match_file(rel):
                        continue
                    paths.append(root / rel)
            return [p for p in paths if p.is_file()]
        except Exception:
            pass

    # Last-resort: include most things, omit common noisy dirs
    skip_dirs = {".git", ".hg", ".svn", "node_modules", ".venv", "venv", "__pycache__"}
    paths = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for name in filenames:
            paths.append(pathlib.Path(dirpath) / name)
    return [p for p in paths if p.is_file()]


def is_binary_file(path: pathlib.Path, blocksize: int = 1024) -> bool:
    """Heuristic: binary if a NUL byte appears in the first block."""
    try:
        with open(path, "rb") as f:
            chunk = f.read(blocksize)
            return b"\x00" in chunk
    except Exception:
        # If unreadable, treat as binary to be safe
        return True


def build_tree(paths: List[pathlib.Path], root: pathlib.Path) -> str:
    rels = sorted([p.relative_to(root).as_posix() for p in paths])
    dirs = defaultdict(set)         # parent_dir -> set(child_dirs)
    files_in_dir = defaultdict(list)  # dir -> [files]

    for rel in rels:
        parts = rel.split("/")
        for i in range(len(parts) - 1):
            parent = "/".join(parts[: i + 1])
            child = parts[i + 1]
            if i + 1 < len(parts) - 1:
                dirs[parent].add(child)
        dkey = "/".join(parts[:-1])
        files_in_dir[dkey].append(parts[-1])

    # ensure top-level dirs populated
    dirs[""] |= set([p.split("/")[0] for p in rels if "/" in p])
    files_in_dir[""] += [p for p in rels if "/" not in p]

    lines = [root.name + "/"]

    def render(dir_key: str, prefix: str = ""):
        entries = sorted([("DIR", n) for n in sorted(dirs.get(dir_key, []))] +
                         [("FILE", n) for n in sorted(files_in_dir.get(dir_key, []))])
        for idx, (kind, name) in enumerate(entries):
            last = idx == len(entries) - 1
            connector = "└── " if last else "├── "
            lines.append(prefix + connector + name)
            if kind == "DIR":
                next_key = name if dir_key == "" else f"{dir_key}/{name}"
                extension = "    " if last else "│   "
                render(next_key, prefix + extension)

    render("")
    return "\n".join(lines)


def main():
    root = pathlib.Path.cwd()
    out_path = root / OUTPUT_NAME

    # Gather files while honoring .gitignore
    if shutil.which("git") and in_git_repo(root):
        try:
            files = get_files_via_git(root)
        except Exception:
            files = get_files_via_lib(root)
    else:
        files = get_files_via_lib(root)

    # Exclude the output file itself (in case it would be captured)
    files = [p for p in files if p.resolve() != out_path.resolve()]
    files = [p for p in files if p.is_file()]

    # Write the dump
    with open(out_path, "w", encoding="utf-8") as out:
        # Project tree
        out.write("PROJECT TREE\n")
        out.write("================\n")
        out.write(build_tree(files, root))
        out.write("\n\n")

        # Files and contents
        out.write("FILES AND CONTENTS\n")
        out.write("==================\n\n")
        for path in sorted(files, key=lambda p: p.as_posix()):
            rel = path.relative_to(root).as_posix()
            out.write(f"--- FILE: {rel} ---\n")
            if is_binary_file(path):
                out.write("[binary file skipped]\n\n")
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = path.read_text(encoding="utf-8", errors="replace")
            out.write(text)
            if not text.endswith("\n"):
                out.write("\n")
            out.write("\n")

    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
