# Déployer les modules experts

Ces étapes supposent Hermes installé, le compte de service et les profils déjà composés. Elles ne configurent pas de credentials ni de routage de modèles. Effectuer une maintenance hors mission ; relancer la gateway après modification des configurations.

```sh
sudo /opt/alfred/current/venv/bin/python bootstrap/install-expert-modules.py
sudo /opt/alfred/current/venv/bin/python bootstrap/install-rtk.py
sudo systemctl restart alfred-gateway.service
```

Le premier script installe les skills sélectionnés, LintLang isolé et Context7 distant pour les profils présents concernés. Il conserve les modèles et les MCP privés existants, corrige la sélection d'outils native et sauvegarde les configurations antérieures sous `/var/lib/alfred/module-config-backups`, hors Git. Il ne remplace pas les SOUL ou mémoires. Les profils futurs doivent repasser cette étape pour recevoir les méthodes de leur rôle.

RTK 0.51.0 est compilé depuis son commit verrouillé avec Rust 1.91.0 : le binaire Linux GNU publié demande glibc 2.39, absente de Debian 12. Les archives source et compilateur sont vérifiées par SHA256, les dépendances suivent Cargo.lock avec `--locked`. Le build s'effectue sous un compte dédié sans sudo, un job, CPU à 100 %, mémoire plafonnée à 1 000 Mo et swap à 700 Mo. LTO désactivé et codegen 16 limitent le pic de compilation. Cette étape ponctuelle peut durer plusieurs dizaines de minutes ; elle n'ajoute pas de daemon de production. Les paquets de compilation viennent des dépôts Debian : ils sont une condition de reconstruction, pas une promesse de binaires bit à bit identiques.

L'option `--use-completed-build` promeut un build déjà terminé pour la révision déclarée. Le manifeste `/var/lib/alfred/rtk-manifest.json` relève version, commit et empreinte du binaire réellement installé. Le code exécuté et les launchers appartiennent à root.

## Utilisation et preuves

`alfred-lint scan <sources> --format json --fail-on fail` est accessible sans sudo. QA et le documentaliste ont un skill dédié ; la CI installe la même version et contrôle les sources d'instructions. Le contrôle n'accorde aucun droit de publication.

`alfred-rtk git status`, `git log`, `git diff` et `git show` sont des usages explicites ; aucune réécriture automatique du terminal, aucun hook ni `rtk init` n'est installé. Un intercepteur local transparent conserve stdout, stderr, arguments et code de sortie de chaque commande Git exécutée par RTK. Le chemin des preuves est indiqué avec le résumé. Ces données sont privées, sous `state/rtk/raw` du profil, mode 0700/0600, hors Git ; rétention de sept jours et des cinquante derniers appels, purgée lors d'un appel ultérieur. Les sorties peuvent contenir des informations sensibles : appliquer la politique de la mission avant partage.

La télémétrie et le suivi de gains propres à RTK sont désactivés. Les autres commandes utilisent le terminal normal. Le binaire n'est pas un contrôle d'autorisation : les permissions de la mission s'appliquent toujours. Les diagnostics système, citations documentaires et résultats structurés ne passent pas dans une compression générale.

## Vérification après installation

```sh
sudo -u alfred env HERMES_HOME=/var/lib/alfred-agent/.hermes/profiles/dev \
 /opt/alfred/current/venv/bin/python tools/check_native_modules.py --context7-live
sudo -u alfred env HERMES_HOME=/var/lib/alfred-agent/.hermes/profiles/alfred \
 /opt/alfred/current/venv/bin/python tools/check_native_modules.py
sudo -u alfred env HERMES_HOME=/var/lib/alfred-agent/.hermes/profiles/dev \
 /opt/alfred/current/venv/bin/python tools/check_rtk.py
python tools/check_instructions.py --executable alfred-lint
sudo -u alfred alfred-service-status
```

Le contrôle natif n'appelle aucun modèle ni ne contacte un utilisateur. Le mode Context7 transmet des questions publiques, vérifie une référence versionnée, un endpoint inaccessible et l'accès au repli officiel. Les missions autonomes restent à tester séparément. Les manifestes locaux ne contiennent pas de credentials.
