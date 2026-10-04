# Récupérer l’accès Desktop

La récupération concerne le compte local du dashboard. Son mot de passe est distinct de celui du compte Linux utilisé en SSH. Le choix actif et la référence de coffre sont dans le dépôt privé de l’instance.

## Mot de passe oublié

Consulter d’abord l’entrée de coffre créée lors du déploiement. Dans Desktop : **Remote gateway → Sign in**, puis saisir l’identifiant du dashboard et ce mot de passe. Ne pas utiliser un token de session ni le mot de passe SSH.

Si une réinitialisation est nécessaire, utiliser un accès SSH administrateur avec la clé autorisée. La perte du login Desktop ne bloque pas cette voie indépendante. Le helper est root-only ; aucun droit de reset n’est accordé aux agents :

```bash
# Vérifier la cohérence du coffre sans afficher ni changer le mot de passe.
sudo python3 /usr/local/lib/alfred/desktop-password.py

# Réinitialiser le compte, mettre à jour le coffre et invalider les sessions.
sudo python3 /usr/local/lib/alfred/desktop-password.py --rotate
```

La voie avec coffre utilise le compte de service 1Password déjà autorisé. Les fichiers `/var/lib/alfred/credentials/op-service-account.json` et `desktop-vault-reference.json` doivent être restaurés hors Git, root `0600`. Ils portent respectivement le token de service et la référence de l’entrée de login. Le helper transmet les données sensibles par stdin au CLI, jamais dans les arguments ou stdout. Il réutilise l’entrée existante et contrôle l’identité du compte.

Le nouveau mot de passe est aléatoire. Le hash scrypt et la clé de signature sont remplacés ; les anciens cookies, refresh tokens et connexions Desktop doivent se réauthentifier. Le backend est relancé. Lire ensuite le nouveau mot de passe dans le coffre et refaire **Sign in**, **Save connection**, **Test**. Les modèles, profils, conversations et paramètres de gateway ne sont pas réinitialisés.

Un échec de mise à jour du coffre arrête l’opération avant modification de la VM. Si la relance échoue, le helper tente de restaurer les fichiers et l’entrée du coffre antérieurs. Un échec du rollback doit être traité par l’administrateur via SSH ; les sorties indiquent uniquement la classe d’erreur, sans secrets. Les contrôles de panne et de restauration utilisent des fichiers temporaires ; ils ne tournent pas le mot de passe réel d’une instance en service.

## Coffre indisponible

Une récupération d’urgence root est possible avec `--rotate --local-only`. Elle enregistre les nouveaux credentials dans le fichier root privé `desktop-login.json` et invalide les sessions. L’administrateur doit remettre le mot de passe à l’utilisateur par un canal privé autorisé et réconcilier le coffre avant de considérer la récupération terminée. Le helper n’affiche pas le secret ; ne pas exporter ce fichier vers Git, une conversation, un log ou un dossier synchronisé en clair.

## Clé SSH perdue également

Passer par la console de la VM depuis son hyperviseur, avec un accès administrateur indépendant, restaurer une clé SSH autorisée puis appliquer la procédure ci-dessus. Aucun formulaire public de récupération, envoi d’e-mail ou contournement de connexion n’est provisionné par ce socle.
