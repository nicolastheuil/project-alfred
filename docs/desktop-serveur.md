# Administrer le backend Desktop

Ce document concerne l’installation serveur. La procédure utilisateur est dans [Connecter Hermes Desktop à la gateway](communiquer-avec-alfred.md).

## Backend actuellement disponible

Après installation du moteur, composition du profil Alfred et supervision, exécuter depuis le checkout public :

```bash
sudo python3 bootstrap/install-desktop.py
```

`alfred-desktop.service` lance le profil Alfred sur **127.0.0.1:9119**, avec `--isolated` pour fixer son contexte. Ce choix de contexte n’est pas une isolation de sécurité entre profils. Le bootstrap crée un token technique de boucle locale dans `/etc/alfred/desktop.env`, root `0600`, qui reste hors Git.

Le service dispose de `Restart=always`, de limites de démarrage et d’une sonde HTTP de version dans `/etc/alfred/service-inventory.d/desktop.json`. La sonde vérifie le backend ; elle ne prouve pas une réponse de modèle. Les logs stdout/stderr natifs sont supprimés pour éviter d’enregistrer une URL d’authentification WebSocket. Les états systemd et les sondes restent disponibles pour le diagnostic. Le plafond est de 384 Mo ; le service partage aussi la limite de la slice runtime.

## Publier la gateway en HTTPS

Installer `nginx` et `certbot` depuis les dépôts Debian, puis fournir un certificat valide et sa clé dans des fichiers root `0600` sous `/etc/alfred/tls/desktop/`, hors Git. Le certificat doit correspondre au domaine et à sa clé. Depuis le checkout public, après le bootstrap Desktop :

```bash
sudo python3 bootstrap/install-https.py \
  --hostname alfred.example.org --username USER \
  --auth-provider basic \
  --listen-port 8443 --public-port 28443 \
  --certificate /etc/alfred/tls/desktop/fullchain.pem \
  --private-key /etc/alfred/tls/desktop/privkey.pem \
  --manual-dns
```

Adapter les domaines et ports à l’instance. La redirection est **port public → port TLS interne** : le backend Hermes 9119 reste en boucle locale. HTTPS distingue les domaines sur un même port. Pour partager le reverse proxy avec Teams, ajouter `--teams-hostname`, `--teams-certificate` et `--teams-private-key` ; le listener Teams prévu est 127.0.0.1:8645, route POST `/api/messages`.

Le bootstrap active par défaut le compte local `--auth-provider basic`, remplace l’environnement du backend et supprime son ancienne exemption par token Desktop. Le mot de passe est généré aléatoirement, haché par scrypt côté service, transmis seulement en HTTPS et protégé par une limite de tentatives Nginx. OAuth est une option `--auth-provider nous --oauth-client-id agent:YOUR_DASHBOARD_ID`, propre à l’instance. Il crée les credentials dans `/var/lib/alfred/credentials/desktop-login.json`, root `0600`. Ils doivent être remis à l’utilisateur via son coffre privé ; le mot de passe ne doit pas être affiché dans une sortie d’agent. Lorsque le fournisseur par mot de passe est choisi, le hash scrypt et la clé de signature de session sont injectés depuis `/etc/alfred/desktop-https.env`. Réexécuter ce bootstrap réutilise le compte existant ; une VM neuve exige de restaurer les credentials du coffre ou d’en provisionner de nouveaux.

Pour un accès Internet, [Hermes recommande OAuth Nous Portal](https://hermes-agent.nousresearch.com/docs/user-guide/features/web-dashboard#authentication-gated-mode). Le socle doit conserver le choix du fournisseur dans l’instance : enregistrer son propre dashboard Nous et callback, puis configurer le Client ID. L’enregistrement et les droits d’accès doivent être vérifiés avant activation ; la mise en place HTTPS seule ne configure pas OAuth. Le mode d’inférence et les comptes OpenRouter restent indépendants de la connexion Dashboard.

Nginx transmet HTTP et WebSocket au backend local. Il impose TLS 1.2/1.3, limite les tentatives de connexion par mot de passe et journalise les chemins sans query strings. `Restart=on-failure` et les sondes TLS sont ajoutés à la supervision. L’inventaire inclut chaque domaine et signale un certificat dont la validité restante devient inférieure à 14 jours.

## Certificats et validation DNS manuelle

`--manual-dns` déclare un renouvellement accompagné par un opérateur. Le timer Certbot non supervisé est désactivé dans ce mode : il ne peut pas publier les TXT à la place de l’utilisateur. Aucun renouvellement automatique n’est annoncé. Les certificats, clés, challenges et états restent hors Git. La supervision TLS fournit l’escalade avant échéance.

Le helper `/usr/local/lib/alfred/acme-manual.py` collecte tous les challenges d’un certificat multi-domaines avant validation. Il ne confirme pas une demande ancienne ou terminée. Procédure administrative de renouvellement :

1. Exécuter `sudo python3 /usr/local/lib/alfred/acme-manual.py begin`, puis `sudo certbot renew --cert-name NOM_CERTIFICAT --force-renewal` dans un terminal maintenu ouvert. La lignée doit avoir été créée avec le hook `--manual-auth-hook '/usr/bin/python3 /usr/local/lib/alfred/acme-manual.py'`.
2. Lire les TXT dans `/var/lib/alfred/acme-manual/challenges.json` via l’accès administratif autorisé, les faire publier et vérifier leur propagation. Ils restent propres à chaque nouvelle demande ; ne pas réutiliser les anciennes valeurs.
3. Exécuter `sudo python3 /usr/local/lib/alfred/acme-manual.py confirm`. Après réussite, utiliser le hook de déploiement `acme-deploy.py`, avec `RENEWED_LINEAGE` pointant vers la lignée, pour vérifier les domaines et la clé, copier les certificats et recharger Nginx. Exécuter `sudo python3 /usr/local/lib/alfred/acme-manual.py finish` ; retirer ensuite les TXT devenus inutiles.

Un fournisseur DNS automatisé peut remplacer ce workflow dans une instance qui lui accorde les droits nécessaires. Son installation doit valider une émission et un renouvellement d’essai avant de réactiver un timer automatique.
