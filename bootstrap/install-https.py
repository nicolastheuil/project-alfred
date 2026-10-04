"""Publish the supervised Desktop backend with native auth behind nginx TLS.

Secrets and certificates are operator inputs outside the checkout. No model calls.
"""
import argparse
import hashlib
import base64
import json
import os
from pathlib import Path
import re
import secrets
import subprocess


def secure_file(path):
    path = Path(path)
    st = path.lstat()
    if path.is_symlink() or not path.is_file() or st.st_uid != 0 or st.st_mode & 0o077:
        raise ValueError("Expected a root-owned private regular file")
    return path


def private_write(path, value):
    path = Path(path)
    if path.exists():
        secure_file(path)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(value)


def password_hash(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
    return "scrypt$16384$8$1$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(digest).decode()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hostname", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--certificate", required=True)
    parser.add_argument("--private-key", required=True)
    parser.add_argument("--listen-port", type=int, default=8443)
    parser.add_argument("--public-port", type=int, default=443)
    parser.add_argument("--teams-hostname")
    parser.add_argument("--teams-certificate")
    parser.add_argument("--teams-private-key")
    parser.add_argument("--manual-dns", action="store_true")
    parser.add_argument("--oauth-client-id")
    parser.add_argument("--auth-provider", choices=["nous", "basic"], default="basic")
    args = parser.parse_args()
    assert os.geteuid() == 0, "root required"
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?", args.hostname) or "." not in args.hostname:
        raise ValueError("Invalid hostname")
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", args.username) or not all(1 <= port <= 65535 for port in (args.listen_port, args.public_port)):
        raise ValueError("Invalid account or port")
    if args.auth_provider == "nous" and not args.oauth_client_id:
        raise ValueError("Register your own Nous dashboard and supply --oauth-client-id; use --auth-provider basic for a local-account endpoint")
    if args.auth_provider == "basic" and args.oauth_client_id:
        raise ValueError("Basic auth does not use an OAuth client ID")
    if args.oauth_client_id and not re.fullmatch(r"agent:[A-Za-z0-9_-]{8,128}", args.oauth_client_id):
        raise ValueError("Invalid Nous dashboard client ID")
    certificate, key = secure_file(args.certificate), secure_file(args.private_key)
    if certificate.name != "fullchain.pem" or key.name != "privkey.pem" or certificate.parent != key.parent or not certificate.parent.is_relative_to("/etc/alfred/tls"):
        raise ValueError("Use fullchain.pem and privkey.pem together under /etc/alfred/tls")
    for path in (certificate, key):
        if not re.fullmatch(r"/[A-Za-z0-9_./-]+", str(path)):
            raise ValueError("Unsupported certificate path")
    subprocess.run(["openssl", "x509", "-in", str(certificate), "-noout", "-checkhost", args.hostname], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["openssl", "x509", "-in", str(certificate), "-noout", "-checkend", "86400"], check=True, stdout=subprocess.DEVNULL)
    certpub = subprocess.check_output(["openssl", "x509", "-in", str(certificate), "-pubkey", "-noout"])
    keypub = subprocess.check_output(["openssl", "pkey", "-in", str(key), "-pubout"], stderr=subprocess.DEVNULL)
    if certpub != keypub:
        raise ValueError("Certificate/key mismatch")
    assert Path("/etc/systemd/system/alfred-desktop.service").exists(), "Install backend first"
    creds = Path("/var/lib/alfred/credentials")
    creds.mkdir(mode=0o700, parents=True, exist_ok=True)
    login_path = creds / "desktop-login.json"
    if login_path.exists():
        login = json.loads(secure_file(login_path).read_text())
        if login["username"] != args.username:
            raise ValueError("Existing login belongs to a different user")
    else:
        login = {"username": args.username, "password": secrets.token_urlsafe(32), "signing_secret": secrets.token_urlsafe(48)}
        private_write(login_path, json.dumps(login))
    authority = args.hostname + (":" + str(args.public_port) if args.public_port != 443 else "")
    env = "\n".join([
        "HERMES_DASHBOARD_PUBLIC_URL=https://" + authority,
        "HERMES_DASHBOARD_BASIC_AUTH_USERNAME=" + login["username"],
        "HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH=" + password_hash(login["password"]),
        "HERMES_DASHBOARD_BASIC_AUTH_SECRET=" + login["signing_secret"],
        "HERMES_DASHBOARD_BASIC_AUTH_TTL_SECONDS=43200", ""])
    expected_provider = {'name': 'basic', 'display_name': 'Username & Password', 'supports_password': True}
    if args.oauth_client_id:
        env = "\n".join(["HERMES_DASHBOARD_PUBLIC_URL=https://" + authority,
            "HERMES_DASHBOARD_OAUTH_CLIENT_ID=" + args.oauth_client_id, ""])
        expected_provider = {'name': 'nous', 'display_name': 'Nous Research', 'supports_password': False}
    private_write("/etc/alfred/desktop-https.env", env)
    dropin = Path("/etc/systemd/system/alfred-desktop.service.d")
    dropin.mkdir(exist_ok=True)
    (dropin / "https.conf").write_text("[Service]\nEnvironmentFile=\nEnvironmentFile=/etc/alfred/desktop-https.env\nUnsetEnvironment=HERMES_DASHBOARD_SESSION_TOKEN HERMES_PARENT_PID\n")
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "restart", "alfred-desktop.service"], check=True)
    # Require the native gate to be up before publishing nginx.
    import time
    import urllib.request
    for attempt in range(40):
        try:
            with urllib.request.urlopen("http://127.0.0.1:9119/api/auth/providers", timeout=2) as r:
                providers = json.load(r)
            if providers.get("providers") == [expected_provider]:
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        raise RuntimeError("Native auth provider failed to start; HTTPS not published")
    source = Path(__file__).resolve().parents[1]
    template = (source / "deploy/nginx/desktop.conf.template").read_text()
    for placeholder, value in {"HOSTNAME": args.hostname, "AUTHORITY": authority, "TLS_PORT": str(args.listen_port), "CERTIFICATE": str(certificate), "PRIVATE_KEY": str(key)}.items():
        template = template.replace("@@" + placeholder + "@@", value)
    if args.teams_hostname:
        if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{0,251}[a-z0-9]", args.teams_hostname) or args.teams_hostname == args.hostname:
            raise ValueError("Invalid Teams hostname")
        teams_cert, teams_key = secure_file(args.teams_certificate), secure_file(args.teams_private_key)
        if teams_cert.name != "fullchain.pem" or teams_key.name != "privkey.pem" or teams_cert.parent != teams_key.parent or not teams_cert.parent.is_relative_to("/etc/alfred/tls"):
            raise ValueError("Use a Teams certificate pair under /etc/alfred/tls")
        for path in (teams_cert, teams_key):
            if not re.fullmatch(r"/[A-Za-z0-9_./-]+", str(path)):
                raise ValueError("Unsupported Teams certificate path")
        subprocess.run(["openssl", "x509", "-in", str(teams_cert), "-noout", "-checkhost", args.teams_hostname], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["openssl", "x509", "-in", str(teams_cert), "-noout", "-checkend", "86400"], check=True, stdout=subprocess.DEVNULL)
        teams_template = (source / "deploy/nginx/teams.conf.template").read_text()
        for placeholder, value in {"HOSTNAME": args.teams_hostname, "TLS_PORT": str(args.listen_port), "CERTIFICATE": str(teams_cert), "PRIVATE_KEY": str(teams_key)}.items():
            teams_template = teams_template.replace("@@" + placeholder + "@@", value)
        template += "\n" + teams_template
    conf = Path("/etc/nginx/conf.d/alfred-desktop.conf")
    conf.write_text(template)
    default = Path("/etc/nginx/sites-enabled/default")
    if default.is_symlink():
        default.unlink()
    nginx_dropin = Path("/etc/systemd/system/nginx.service.d")
    nginx_dropin.mkdir(exist_ok=True)
    (nginx_dropin / "alfred-restart.conf").write_text("[Unit]\nStartLimitIntervalSec=900\nStartLimitBurst=5\n[Service]\nRestart=on-failure\nRestartSec=10\n")
    subprocess.run(["nginx", "-t"], check=True)
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "enable", "--now", "nginx.service"], check=True)
    subprocess.run(["systemctl", "reload", "nginx.service"], check=True)
    rule = Path("/etc/sudoers.d/alfred-https")
    rule.write_text("alfred ALL=(root) NOPASSWD: /usr/local/sbin/alfred-service-control restart nginx.service\n")
    rule.chmod(0o440)
    subprocess.run(["visudo", "-cf", str(rule)], check=True, stdout=subprocess.DEVNULL)
    inventory = Path("/etc/alfred/service-inventory.d")
    # The local status endpoint intentionally hides runtime details while gated.
    (inventory / "desktop.json").write_text(json.dumps({"services": [{"unit": "alfred-desktop.service", "grace_seconds": 90,
        "probes": [{"kind": "http_json", "url": "http://127.0.0.1:9119/api/auth/providers", "field": "providers", "expected": [expected_provider]}]}]}, indent=2) + "\n")
    (inventory / "https.json").write_text(json.dumps({"services": [{"unit": "nginx.service", "grace_seconds": 90, "probes": [{"kind": "tls", "host": "127.0.0.1", "port": args.listen_port, "server_name": args.hostname, "min_validity_seconds": 1209600}]}]}, indent=2) + "\n")
    import shutil
    for name in ('acme-manual.py', 'acme-deploy.py', 'desktop-password.py'):
        shutil.copyfile(source / 'deploy/runtime' / name, '/usr/local/lib/alfred/' + name)
    tls_hosts = [args.hostname] + ([args.teams_hostname] if args.teams_hostname else [])
    tls_targets = [str(certificate.parent)] + ([str(Path(args.teams_certificate).parent)] if args.teams_hostname else [])
    private_write('/etc/alfred/https.json', json.dumps({'hostname': args.hostname, 'public_port': args.public_port,
        'listen_port': args.listen_port, 'tls_hosts': tls_hosts, 'tls_targets': tls_targets,
        'renewal_mode': 'operator_dns' if args.manual_dns else 'external', 'auth_provider': expected_provider['name']}))
    if args.manual_dns:
        subprocess.run(['systemctl', 'disable', '--now', 'certbot.timer'], check=True, capture_output=True)
    https_inventory = json.loads((inventory / 'https.json').read_text())
    https_inventory['services'][0]['probes'] = [{'kind': 'tls', 'host': '127.0.0.1', 'port': args.listen_port,
        'server_name': hostname, 'min_validity_seconds': 1209600} for hostname in tls_hosts]
    (inventory / 'https.json').write_text(json.dumps(https_inventory, indent=2) + "\n")
    print(json.dumps({"https_configured": True, "hostname": args.hostname, "listen_port": args.listen_port, "public_url": "https://" + authority,
        "credentials_path": str(login_path), "renewal_configured": False}))


if __name__ == "__main__":
    main()
