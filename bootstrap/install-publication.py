"""Install fixed-destination publication using operator-provided root credentials."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
from urllib.request import urlopen

def main():
    if os.geteuid() != 0:
        raise SystemExit('Run as root')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--instance-source', type=Path, required=True)
    parser.add_argument('--credential-file', type=Path, required=True)
    parser.add_argument('--platform-credential-file', type=Path)
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1]
    publication = json.loads((args.instance_source / 'publication.json').read_text())
    os.umask(0o077)
    library = Path('/usr/local/lib/alfred')
    library.mkdir(parents=True, exist_ok=True)
    (library / 'no-hooks').mkdir(mode=0o700, exist_ok=True)
    for name in ['repository-publish.py', 'github-askpass.py']:
        shutil.copyfile(source / 'deploy/runtime' / name, library / name)
        os.chmod(library / name, 0o700)
    wrapper = Path('/usr/local/sbin/alfred-publish-broker')
    wrapper.write_text('#!/bin/sh\nexec /usr/bin/python3 /usr/local/lib/alfred/repository-publish.py "$@"\n')
    wrapper.chmod(0o755)
    # sudo's secure_path normally puts sbin before bin. Both entry points must
    # reach the client, rather than bypass elevation to the root-only script.
    for client in [Path('/usr/local/bin/alfred-publish'), Path('/usr/local/sbin/alfred-publish')]:
        client.write_text('#!/bin/sh\ncase "${1:-help}" in\nhelp|--help|-h) printf "%s\\n" "alfred-publish {status|sync|publish|retry}; JSON request on stdin (scope, classification, base_revision, files, message)."; exit 0;;\nesac\nexec sudo -n /usr/local/sbin/alfred-publish-broker "$@"\n')
        client.chmod(0o755)
    sudoers = Path('/etc/sudoers.d/alfred-publication')
    sudoers.write_text('alfred ALL=(root) NOPASSWD: ' + ', '.join('/usr/local/sbin/alfred-publish-broker ' + a for a in ['status', 'sync', 'publish', 'retry']) + '\n')
    sudoers.chmod(0o440)
    subprocess.run(['visudo', '-cf', str(sudoers)], check=True)
    repositories = {}
    for scope in ['platform', 'instance']:
        target = publication[scope]['write_repository']
        if target is None:
            continue
        credential = (args.platform_credential_file or args.credential_file) if scope == 'platform' else args.credential_file
        credential = credential.resolve(strict=True)
        if credential.stat().st_uid != 0 or credential.stat().st_mode & 0o077:
            raise SystemExit('Root-only credential file required')
        repositories[scope] = {'url': target, 'credential_file': str(credential),
                               'workspace': '/var/lib/alfred-agent/.hermes/shared/repositories/' + scope}
    config = {'schema_version': 1, 'service_account': 'alfred', 'repositories': repositories,
              'public_private_markers': publication.get('public_private_markers', [])}
    # The private destination must actually be private, not merely labelled so.
    from urllib.request import Request
    private = repositories['instance']
    token = json.loads(Path(private['credential_file']).read_text())['token']
    api = 'https://api.github.com/repos/' + private['url'].split('github.com/', 1)[1].removesuffix('.git')
    with urlopen(Request(api, headers={'Authorization': 'Bearer ' + token, 'User-Agent': 'Alfred-publication-bootstrap'}), timeout=20) as response:
        if json.load(response).get('private') is not True:
            raise SystemExit('Instance repository must be private')
    target = Path('/etc/alfred/publication-runtime.json')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(config, indent=2) + '\n')
    target.chmod(0o600)
    lock = json.loads((source / 'config/publication-dependencies.lock.json').read_text())['gitleaks']
    with urlopen(lock['url'], timeout=30) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != lock['sha256']:
        raise SystemExit('Gitleaks archive checksum mismatch')
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
        binary = archive.extractfile('gitleaks').read()
    tool = Path('/usr/local/bin/gitleaks')
    tool.write_bytes(binary)
    tool.chmod(0o755)
    subprocess.run([str(tool), 'version'], check=True)
    for scope in repositories:
        subprocess.run([str(wrapper), 'sync'], input=json.dumps({'scope': scope}).encode(), check=True)
    instance = json.loads((args.instance_source / 'instance.json').read_text())
    team = json.loads((args.instance_source / instance['team_seed']).read_text())
    home = Path('/var/lib/alfred-agent/.hermes')
    account = __import__('pwd').getpwnam('alfred')
    for profile in team['profiles']:
        skill = home / 'profiles' / profile['id'] / 'skills/platform-maintenance'
        skill.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / 'skills/platform-maintenance/SKILL.md', skill / 'SKILL.md')
        os.chown(skill, account.pw_uid, account.pw_gid)
        os.chown(skill / 'SKILL.md', account.pw_uid, account.pw_gid)
        os.chmod(skill / 'SKILL.md', 0o600)
    context = home / 'shared/platform/CONTEXT.md'
    context.parent.mkdir(parents=True, exist_ok=True)
    context.write_text('# Contexte actif de maintenance\n\n' +
        'Profils déclarés : ' + ', '.join(p['id'] for p in team['profiles']) + '.\n\n' +
        'Alfred comprend et consulte les sources ; Orchestrator coordonne via Kanban ; Platform Engineer réalise les changements du harness ; le documentaliste documente et publie.\n\n' +
        'Changement durable : Orchestrator → workers → QA/RSSI selon le besoin → documentaliste toujours → GitHub. Tâche ordinaire : Orchestrator → workers → QA/RSSI selon le besoin → fin.\n\n' +
        '\n'.join(f"- {scope} : {item['url']} ; sources {item['workspace']}" for scope, item in repositories.items()) +
        '\n\nLe moteur immuable /opt/alfred/current ne remplace pas ces sources. Utiliser alfred-publish status/sync/publish/retry ; les valeurs des credentials ne sont pas des éléments de contexte. Le mandat permanent inclut les publications classées et autorisées, sans nouvelle approbation systématique. Un doute public/privé se clarifie via Alfred.\n\n' +
        'Une étape est livrée sur preuve. Le broker est disponible ; la présence des profils ne certifie pas toute mission. Les données métier et conversations ne sont pas publiées par ce circuit.\n')
    os.chown(context.parent, account.pw_uid, account.pw_gid)
    os.chown(context, account.pw_uid, account.pw_gid)
    context.chmod(0o600)
    print(json.dumps({'publication_broker_installed': True, 'scopes': list(repositories), 'credentials_returned_in_status': False}))

if __name__ == '__main__':
    main()
