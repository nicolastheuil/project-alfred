# Préparer une VM Debian 12

**Phases disponibles : prérequis système et moteur Hermes verrouillé.** Les profils configurés et les canaux restent à composer ; ces commandes ne suffisent pas encore à obtenir un Alfred opérationnel.

Sur Debian 12, après récupération d'une version précise du dépôt :

```sh
sudo bash bootstrap/prepare-host.sh
```

Le script installe les prérequis depuis les dépôts Debian et configure la zram via le paquet `zram-tools`. La taille logique initiale est de 100 % de la RAM physique, avec zstd et une priorité de swap de 100. Ce volume est une capacité de pages compressées, pas une réserve supplémentaire de mémoire physique. Le réglage initial de swappiness est 100.

La configuration est persistante et le service est activé au démarrage. Si une réexécution demande de modifier une zram qui contient déjà des pages échangées, le script s'arrête pour permettre une intervention en maintenance. Lorsque la configuration est identique, il conserve le service actif.

Le manifeste local `/var/lib/alfred/host-manifest.json` conserve les versions de paquets, l'architecture, les empreintes des sources appliquées et les vérifications du service. Il marque explicitement que le runtime et l'essai après redémarrage ne sont pas encore validés.

Les paquets système suivent les dépôts Debian configurés sur l'hôte. Leurs versions effectives sont relevées ; cette première phase ne prétend pas fournir une image binaire identique de la distribution. Les versions du moteur et des dépendances applicatives seront verrouillées séparément.

La phase a été exécutée le 4 octobre 2026 sur Debian 12 ARM64 : service actif et activé au démarrage, compression zstd, priorité 100 et swappiness 100 vérifiés. Une seconde exécution identique a conservé le service sans le redémarrer. Un redémarrage réel de la VM a confirmé ces réglages et la disponibilité du moteur installé.

Pour vérifier la phase :

```sh
systemctl status zramswap.service
swapon --show
sudo cat /var/lib/alfred/host-manifest.json
```

## Installer le moteur Hermes verrouillé

La phase suivante, pour Debian 12 ARM64, est :

```sh
sudo bash bootstrap/install-hermes.sh
sudo -u alfred hermes --version
sudo -u alfred hermes doctor
```

Le verrou [runtime.lock.json](../config/runtime.lock.json) fixe Hermes 0.21.5, tag `v2026.9.24`, commit `f97608f178d1ffeca59860195ab7da295f7c8e5f`, ainsi que uv et les empreintes des artefacts. Les dépendances du moteur suivent le `uv.lock` de ce commit. Le cœur et les extras ACP/MCP/Teams sont installés ; les outils de construction ont leurs propres versions et empreintes. Aucun repli vers une résolution libre n'est utilisé.

Le runtime utilise un CPython 3.11.17 dédié, build Astral `20261003`, qui embarque SQLite 3.53.1. Le diagnostic avait signalé SQLite 3.40.1 du Python système : cette version contient le [bug de reset WAL](https://sqlite.org/wal.html#walresetbug), pertinent pour les bases partagées par plusieurs processus. L'installateur exige une SQLite au moins égale à 3.51.3 et vérifie la version réellement chargée. Le Python système Debian reste utilisé par les scripts système et n'est pas remplacé.

Le compte système `alfred` n'a pas de shell de connexion ni sudo général. La supervision lui accorde seulement deux commandes de relance bornées. Le code et le venv sous `/opt/alfred/releases` appartiennent à root ; l'agent écrit son état sous `/var/lib/alfred-agent/.hermes`. Le manifeste `/var/lib/alfred/runtime-manifest.json` relève les versions et métadonnées de licence des paquets. Cette séparation protège l'installation du moteur ; elle ne constitue pas encore une isolation entre les futurs profils.

L'installation et les imports ACP/MCP ont été vérifiés sur Debian 12 ARM64. SQLite FTS5 est disponible ; les droits d'écriture sur le code et le venv ainsi que l'accès sudo ont été refusés au compte `alfred`. Aucun appel de modèle ou envoi de message n'est effectué par cette phase.

Un essai d'intégration a fait écrire simultanément deux processus dans une base SQLite temporaire en mode WAL : 400 entrées retrouvées par FTS, puis contrôle d'intégrité réussi. Ce test confirme le fonctionnement de la bibliothèque chargée ; la présence du correctif WAL repose sur sa version vérifiée. L'installateur refuse une maintenance pendant qu'un processus du compte `alfred` tourne, afin de ne pas remplacer ses dépendances en pleine mission.

Le diagnostic initial peut signaler les credentials et canaux encore absents. Ils font partie des phases de composition de l'instance et de connexion. Le bootstrap ne crée pas encore l'équipe configurée, un service de messagerie ou le circuit autonome de missions. Les [crédits](../THIRD_PARTY_NOTICES.md) expliquent le choix de chaque composant.

## Modules experts

Après composition des profils, suivre le [déploiement des modules retenus](deploiement-modules.md). Les [résultats de l’étude](etude-outils-v1.md) distinguent les fonctions réellement installées et les validations encore nécessaires.

## Raccorder Hermes Desktop

Après composition des profils et supervision, le [guide des accès](communiquer-avec-alfred.md) fournit le backend headless supervisé, le transport SSH et les procédures Desktop, messageries et IDE. La cible recommandée est Remote gateway en HTTPS authentifié ; le tunnel SSH manuel décrit dans le guide constitue l’accès provisoire déjà vérifié. La publication HTTPS et le raccordement SSH natif restent à éprouver.
