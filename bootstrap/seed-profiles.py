"""Compose native Hermes identities without credentials, model calls or gateways.

Run as root on the installed Debian host with --instance-source. Existing modified
memories are refused rather than replaced. Instance inputs must be reviewed files.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import subprocess
import tempfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_text(root, relative):
    candidate = root / relative
    path = candidate.resolve(strict=True)
    if not path.is_relative_to(root) or candidate.is_symlink() or not path.is_file():
        raise ValueError("Seed must be a regular file inside its source directory")
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance-source", type=Path, required=True)
    parser.add_argument("--public-source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--only", help="Compose one declared profile, preserving the others")
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit("Run as root; profile files are assigned to the service account")
    public, private = args.public_source.resolve(), args.instance_source.resolve()
    runtime = json.loads(source_text(public, "config/runtime.lock.json"))
    instance = json.loads(source_text(private, "instance.json"))
    team = json.loads(source_text(private, instance["team_seed"])) if instance.get("team_seed") else json.loads(source_text(public, "config/team-seed.json"))
    account = pwd.getpwnam(runtime["service_account"])
    home = Path(runtime["data_home"])
    if home != Path(account.pw_dir) / ".hermes" or home.is_symlink():
        raise SystemExit("Unexpected service data home")
    if not any(p["id"] == team["entrypoint"] for p in team["profiles"]):
        raise SystemExit("Entrypoint must have a declared profile")
    metadata = Path("/var/lib/alfred")
    manifest_path = metadata / "identity-manifest.json"
    previous = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"files": {}}
    plan, descriptions = {}, {}
    for profile in team["profiles"]:
        name = profile["id"]
        if args.only and name != args.only:
            continue
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", name) or name in descriptions:
            raise SystemExit("Invalid or duplicate profile id")
        descriptions[name] = profile["description"]
        soul = source_text(public, profile["soul"])
        user, memory = "", profile["memory"]
        if name == team["entrypoint"]:
            soul = source_text(private, instance["relationship_soul"])
            user = source_text(private, instance["user_preferences"])
            memory = source_text(private, instance["relationship_memory"])
        elif name in instance.get("profile_memory_seeds", {}):
            memory = source_text(private, instance["profile_memory_seeds"][name])
        if len(user) > 1375 or len(memory) > 2200:
            raise SystemExit(f"Seed exceeds the native memory budget: {name}")
        if name != team["entrypoint"]:
            soul += "\n\nDomaine : " + profile["domain"]
            soul += "\nLes connaissances détaillées vont dans ../../shared/expertise ; les faits professionnels dans ../../shared/professional/clients."
            soul += "\nLes contextes professionnels et personnels restent séparés ; leur activation dépend du mandat et des accès effectifs."
            soul += "\nLa mémoire relationnelle de l'utilisateur appartient exclusivement au profil d'interface."
        config = {"memory": {"memory_enabled": True, "user_profile_enabled": name == team["entrypoint"],
                             "memory_char_limit": 2200, "user_char_limit": 1375}}
        selected = ["terminal", "file", "memory", "skills", "clarify"] if name == team["entrypoint"] else ["terminal", "file", "memory", "skills", "kanban", "web", "todo"]
        config["agent"] = {"disabled_toolsets": ["browser", "code_execution", "computer_use", "cronjob", "delegation"]}
        config["platform_toolsets"] = {platform: selected for platform in ["cli", "acp", "whatsapp", "teams"]}
        contents = {"SOUL.md": soul, "memories/USER.md": user, "memories/MEMORY.md": memory,
                    "config.yaml": json.dumps(config, indent=2)}
        for relative, content in contents.items():
            plan[f"profiles/{name}/{relative}"] = (content + "\n" if content else "").encode("utf-8")
    if not descriptions:
        raise SystemExit("No declared profile selected")
    # Preflight the entire set before any profile is created or changed.
    existing_profiles = set()
    for name in descriptions:
        profile_path = home / "profiles" / name
        if profile_path.exists():
            existing_profiles.add(name)
            if profile_path.is_symlink() or not profile_path.is_dir():
                raise SystemExit(f"Unsafe profile path: {name}")
    for relative, content in plan.items():
        target = home / relative
        if not target.resolve().is_relative_to(home.resolve()) or any(p.is_symlink() for p in [target, *target.parents]):
            raise SystemExit("Symlink or escaped profile target refused")
        if target.exists():
            if not target.is_file():
                raise SystemExit("Profile seed target must be a regular file")
            current = digest(target.read_bytes())
            expected = previous["files"].get(relative, {}).get("sha256")
            if current not in {digest(content), expected}:
                raise SystemExit(f"Existing content requires a reviewed merge: {relative}")
        elif relative.split("/")[1] in existing_profiles and relative not in previous["files"]:
            raise SystemExit(f"Unmanaged existing profile refused: {relative}")
    if args.dry_run:
        print(json.dumps({"dry_run": True, "profiles": list(descriptions), "files": len(plan), "model_calls": 0}))
        return
    busy = subprocess.run(["pgrep", "-u", str(account.pw_uid)], capture_output=True)
    if busy.returncode != 1:
        raise SystemExit("Stop all service-account processes before identity composition")
    os.umask(0o077)
    metadata.mkdir(mode=0o700, exist_ok=True)
    os.chown(metadata, 0, account.pw_gid)
    os.chmod(metadata, 0o750)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = metadata / "identity-backups" / stamp
    backup.mkdir(mode=0o700, parents=True)
    def cli(*arguments):
        subprocess.run(["runuser", "-u", account.pw_name, "--", "/usr/local/bin/hermes", *arguments],
                       check=True, stdout=subprocess.DEVNULL)
    for name, description in descriptions.items():
        if name not in existing_profiles:
            cli("profile", "create", name, "--no-alias", "--no-skills", "--description", description)
    applied = {}
    for relative, content in plan.items():
        target = home / relative
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chown(target.parent, account.pw_uid, account.pw_gid)
        if target.exists() and target.read_bytes() != content:
            saved = backup / relative
            saved.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            saved.write_bytes(target.read_bytes())
        if not target.exists() or target.read_bytes() != content:
            with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as output:
                output.write(content)
                temporary = Path(output.name)
            os.chown(temporary, account.pw_uid, account.pw_gid)
            os.chmod(temporary, 0o600)
            os.replace(temporary, target)
        os.chown(target, account.pw_uid, account.pw_gid)
        os.chmod(target, 0o600)
        applied[relative] = {"sha256": digest(content), "bytes": len(content)}
    for category in ["professional/clients", "personal", "expertise", "missions", "migration"]:
        directory = home / "shared" / category
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chown(directory.parent, account.pw_uid, account.pw_gid)
        os.chown(directory, account.pw_uid, account.pw_gid)
    for name in descriptions:
        directory = home / "shared" / "expertise" / name
        directory.mkdir(mode=0o700, exist_ok=True)
        os.chown(directory, account.pw_uid, account.pw_gid)
    cli("profile", "use", team["entrypoint"])
    if args.only:
        applied = {**previous["files"], **applied}
    profile_names = sorted(set(previous.get("profiles", [])) | set(descriptions))
    report = {"schema_version": 1, "applied_at_utc": stamp, "profiles": profile_names,
              "files": applied, "model_calls": 0, "mission_execution_tested": False,
              "filesystem_isolation_between_profiles": False}
    manifest_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"applied": True, "profiles": len(descriptions), "files": len(applied), "model_calls": 0}))


if __name__ == "__main__":
    main()
