# Administrer le backend Desktop

Ce document concerne l’installation serveur. La procédure utilisateur est dans [Connecter Hermes Desktop à la gateway](communiquer-avec-alfred.md).

## Backend actuellement disponible

Après installation du moteur, composition du profil Alfred et supervision, exécuter depuis le checkout public :

```bash
sudo python3 bootstrap/install-desktop.py
```

`alfred-desktop.service` lance le profil Alfred sur **127.0.0.1:9119**, avec `--isolated` pour fixer son contexte. Ce choix de contexte n’est pas une isolation de sécurité entre profils. Le bootstrap crée un token technique de boucle locale dans `/etc/alfred/desktop.env`, root `0600`, qui reste hors Git.

Le service dispose de `Restart=always`, de limites de démarrage et d’une sonde HTTP de version dans `/etc/alfred/service-inventory.d/desktop.json`. La sonde vérifie le backend ; elle ne prouve pas une réponse de modèle. Les logs stdout/stderr natifs sont supprimés pour éviter d’enregistrer une URL d’authentification WebSocket. Les états systemd et les sondes restent disponibles pour le diagnostic. Le plafond est de 384 Mo ; le service partage aussi la limite de la slice runtime.

## Publication HTTPS à finaliser

Le bootstrap précédent ne publie pas la gateway en HTTPS. Le déploiement retenu doit ajouter :

- Un domaine d’instance, un certificat valide et un renouvellement automatique contrôlé.
- L’authentification native de Hermes, avec le fournisseur choisi pour l’instance et ses secrets hors Git.
- Un reverse proxy TLS vers le backend local, avec passage des WebSockets et supervision.
- Les tests de refus anonyme, de connexion utilisateur, de transport HTTP/WebSocket et d’une conversation Desktop.

Le token technique Desktop de boucle locale n’est pas une configuration d’authentification publique. La publication doit activer la porte d’authentification native prévue par le [serveur Hermes verrouillé](https://github.com/NousResearch/hermes-agent/blob/f97608f178d1ffeca59860195ab7da295f7c8e5f/hermes_cli/web_server.py), sans exemption d’authentification réservée au Desktop local.

Desktop et Teams peuvent partager un reverse proxy, avec des domaines ou routes distincts. Le callback Teams et l’URL de la gateway Desktop restent deux destinations différentes, avec leurs authentifications respectives.
