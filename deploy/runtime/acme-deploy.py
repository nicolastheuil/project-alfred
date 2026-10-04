"""Copy a renewed Certbot lineage into configured root-only TLS paths, then reload nginx."""
import json
import os
from pathlib import Path
import subprocess


def main():
    assert os.geteuid() == 0, 'root required'
    manifest = Path('/etc/alfred/https.json')
    assert not manifest.is_symlink() and manifest.stat().st_uid == 0 and not manifest.stat().st_mode & 0o077
    cfg = json.loads(manifest.read_text())
    lineage = Path(os.environ['RENEWED_LINEAGE'])
    root = Path('/etc/letsencrypt')
    source = {}
    for name in ['fullchain.pem', 'privkey.pem']:
        p = (lineage / name).resolve(strict=True)
        assert p.is_relative_to(root) and p.is_file() and p.stat().st_uid == 0
        assert not p.stat().st_mode & 0o022
        if name == 'privkey.pem':
            assert not p.stat().st_mode & 0o077
        source[name] = p
    for hostname in cfg['tls_hosts']:
        subprocess.run(['openssl', 'x509', '-in', str(source['fullchain.pem']), '-noout', '-checkhost', hostname], check=True, stdout=subprocess.DEVNULL)
    certpub = subprocess.check_output(['openssl', 'x509', '-in', str(source['fullchain.pem']), '-pubkey', '-noout'])
    keypub = subprocess.check_output(['openssl', 'pkey', '-in', str(source['privkey.pem']), '-pubout'], stderr=subprocess.DEVNULL)
    assert certpub == keypub, 'certificate/key mismatch'
    for target in cfg['tls_targets']:
        directory = Path(target)
        assert directory.is_relative_to('/etc/alfred/tls') and not directory.is_symlink()
        for name, origin in source.items():
            dest = directory / name
            fd = os.open(dest.with_suffix('.new'), os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'wb') as f:
                f.write(origin.read_bytes())
            os.replace(dest.with_suffix('.new'), dest)
    subprocess.run(['nginx', '-t'], check=True, capture_output=True)
    subprocess.run(['systemctl', 'reload', 'nginx.service'], check=True)


if __name__ == '__main__':
    main()
