# Préparer une VM Debian 12

**Phase disponible : prérequis système.** Le moteur agentique, les profils exécutables et les canaux restent à déployer ; cette commande ne suffit pas encore à obtenir un Alfred opérationnel.

Sur Debian 12, après récupération d'une version précise du dépôt :

```sh
sudo bash bootstrap/prepare-host.sh
```

Le script installe les prérequis depuis les dépôts Debian et configure la zram via le paquet `zram-tools`. La taille logique initiale est de 100 % de la RAM physique, avec zstd et une priorité de swap de 100. Ce volume est une capacité de pages compressées, pas une réserve supplémentaire de mémoire physique. Le réglage initial de swappiness est 100.

La configuration est persistante et le service est activé au démarrage. Si une réexécution demande de modifier une zram qui contient déjà des pages échangées, le script s'arrête pour permettre une intervention en maintenance. Lorsque la configuration est identique, il conserve le service actif.

Le manifeste local `/var/lib/alfred/host-manifest.json` conserve les versions de paquets, l'architecture, les empreintes des sources appliquées et les vérifications du service. Il marque explicitement que le runtime et l'essai après redémarrage ne sont pas encore validés.

Les paquets système suivent les dépôts Debian configurés sur l'hôte. Leurs versions effectives sont relevées ; cette première phase ne prétend pas fournir une image binaire identique de la distribution. Les versions du moteur et des dépendances applicatives seront verrouillées séparément.

La phase a été exécutée le 4 octobre 2026 sur Debian 12 ARM64 : service actif et activé au démarrage, compression zstd, priorité 100 et swappiness 100 vérifiés. Une seconde exécution identique a conservé le service sans le redémarrer. L'essai après redémarrage de la VM reste à effectuer.

Pour vérifier la phase :

```sh
systemctl status zramswap.service
swapon --show
sudo cat /var/lib/alfred/host-manifest.json
```
