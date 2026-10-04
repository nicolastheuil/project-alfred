"""Check the initial public repository contract using only the standard library."""
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_ROOT_FILES = {"README.md", "AGENTS.md", "LICENSE", "THIRD_PARTY_NOTICES.md", ".gitignore", ".gitattributes"}
ALLOWED_DIRECTORIES = {"docs", "config", "examples", "profiles", "tools", "bootstrap", "deploy", ".github"}
FORBIDDEN_NAMES = {"auth.json", "credentials.json", "USER.md", "MEMORY.md"}
FORBIDDEN_SUFFIXES = {".key", ".pem", ".p12", ".pfx", ".ppk", ".db", ".sqlite", ".aes", ".age"}


def checked_files():
    result = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True)
    if result.returncode == 0 and result.stdout:
        return [ROOT / p.decode("utf-8") for p in result.stdout.split(b"\0") if p]
    return [p for p in ROOT.rglob("*") if p.is_file() and not any(x in {".git", "__pycache__"} for x in p.relative_to(ROOT).parts)]


def check():
    errors = []
    files = checked_files()
    for path in files:
        relative = path.relative_to(ROOT)
        if len(relative.parts) == 1:
            if relative.name not in ALLOWED_ROOT_FILES:
                errors.append(f"Unexpected root file: {relative}")
        elif relative.parts[0] not in ALLOWED_DIRECTORIES:
            errors.append(f"Directory outside public scope: {relative}")
        if path.name.startswith(".env") or path.name in FORBIDDEN_NAMES or path.suffix in FORBIDDEN_SUFFIXES:
            errors.append(f"Private or runtime file: {relative}")
        if path.is_symlink() or not path.is_file():
            errors.append(f"Expected regular file: {relative}")
            continue
        if path.stat().st_size > 1_000_000:
            errors.append(f"Unexpected large source file: {relative}")
        if path.suffix == ".json":
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except (ValueError, UnicodeError) as error:
                errors.append(f"Invalid JSON {relative}: {error}")
    contract = json.loads((ROOT / "config/platform-contract.json").read_text(encoding="utf-8"))
    for role, relative in contract["roles"].items():
        path = (ROOT / relative).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            errors.append(f"Invalid role source: {role}")
    if contract["entrypoint"] not in contract["roles"] or contract["coordinator"] not in contract["roles"]:
        errors.append("Entrypoint and coordinator must be declared roles")
    limits = contract["initial_limits"]
    if not 0 < limits["tasks_per_profile"] <= limits["global_tasks"]:
        errors.append("Invalid task limits")
    runtime = json.loads((ROOT / "config/runtime.lock.json").read_text(encoding="utf-8"))
    if not re.fullmatch(r"[0-9a-f]{40}", runtime["hermes"]["revision"]):
        errors.append("Hermes must be pinned to a full commit SHA")
    for digest in [runtime["hermes"]["uv_lock_sha256"], runtime["uv"]["sha256"], runtime["python"]["sha256"]]:
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            errors.append("Runtime artifact requires a SHA256 hash")
    if (runtime["uv"]["architecture"] != "arm64" or runtime["python"]["major_minor"] != "3.11"
            or runtime["python"]["executable"] != f"/opt/alfred/tools/cpython-{runtime['python']['version']}-{runtime['python']['build']}/bin/python3"
            or runtime["service_account"] != "alfred" or runtime["data_home"] != "/var/lib/alfred-agent/.hermes"
            or runtime["extras"] != ["acp", "mcp"] or runtime["build_requirements"] != "deploy/runtime/build-requirements.lock"):
        errors.append("Runtime lock does not match the initial Debian ARM64 installer contract")
    for relative in ["docs/guide-illustre.md", "docs/personnalisation.md", "docs/construction.md", "examples/instance.example.json", "THIRD_PARTY_NOTICES.md", "config/runtime.lock.json"]:
        if not (ROOT / relative).is_file():
            errors.append(f"Missing documentation or example: {relative}")
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"Public contract valid: {len(files)} files, {len(contract['roles'])} role templates")


if __name__ == "__main__":
    check()
