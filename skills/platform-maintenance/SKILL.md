---
name: platform-maintenance
description: Coordonner un changement du harness, connaître le socle et l'instance, documenter puis publier dans les dépôts autorisés.
---

# Un changement livré comprend sa documentation

Lire `/var/lib/alfred-agent/.hermes/shared/platform/CONTEXT.md` pour les rôles, chemins, destinations et limites réellement actifs. Les données d'une instance ne vont jamais dans une rédaction publique. Le moteur immuable Hermes et les sources Project Alfred sont deux ensembles différents : l'absence de remote du moteur ne dit rien des dépôts du projet.

Alfred comprend la demande et utilise `kanban_create` pour la confier à `orchestrator`. Il n'exécute pas lui-même le travail expert. Orchestrator affecte les workers nécessaires, sollicite QA/RSSI selon le besoin, et ajoute systématiquement `documentaliste` pour tout changement durable de code, configuration, rôle, SOUL ou skill. Une tâche ordinaire se termine après ses revues et sa restitution, sans publication de ses données métier.

Le documentaliste prépare les sources et les explications dans les espaces `shared/repositories/platform` ou `shared/repositories/instance`. Public = mécanisme réutilisable ; privé = personnalité, contexte professionnel, réglages, connexions ou skill propre à l'utilisateur ; mixte = deux ensembles cohérents. Un doute d'exposition demande une décision via Alfred. Un périmètre clair et autorisé n'exige pas une nouvelle autorisation de push.

Le documentaliste réalise la publication avec `alfred-publish`. Les credentials sont résolus par le broker privilégié ; ne pas chercher, afficher ou recopier de token. Alfred peut utiliser `status` et consulter les sources pour qualifier une demande. Une absence d'accès se rapporte comme un blocage précis.

```sh
printf '%s' '{"scope":"platform"}' | alfred-publish status
printf '%s' '{"scope":"instance"}' | alfred-publish status
```

Pour publier, transmettre un objet JSON sur stdin à `alfred-publish publish` : `scope`, `classification` identique au scope, `base_revision` obtenue par status, liste explicite `files`, et `message` de commit. Le broker refuse fichiers opérationnels, secrets, symlinks et destination non configurée ; il contrôle la syntaxe et exécute Gitleaks. Seul `remote_confirmed: true` avec un commit prouve la publication. Les agents doivent en plus vérifier le sens, la documentation et la confidentialité de leurs modifications ; les contrôles déterministes ne savent pas classifier tout texte personnel.

Un changement mixte publie d'abord le socle, puis inscrit son SHA dans `platform.lock.json` de l'instance avant de publier le privé. Un échec de push garde le commit en attente ; `retry` avec le SHA courant ne force jamais l'historique. En cas de divergence, demander une résolution contrôlée. `sync` actualise les sources sans écraser des modifications de workspace ; `overwrite` reste réservé à une décision explicite de récupération.

Ne pas clore la mission de changement tant que la documentation et les publications requises restent en attente. Donner à Alfred les commits réellement confirmés et les éventuels blocages. Une simulation demandée par l'utilisateur ne modifie aucun fichier et n'effectue aucune publication.
