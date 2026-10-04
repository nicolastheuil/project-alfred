---
name: context7-documentation
description: "Use when public library documentation is needed: check the installed version and official fallback."
---

# Consulter une documentation ciblée

Disponible pour dev, devops et platform-engineer. Utiliser les outils MCP de Context7 si une bibliothèque ou une API nécessite une vérification documentaire.

- Résoudre la bibliothèque avec resolve-library-id, en précisant la version réellement installée ; consulter query-docs avec l'identifiant adéquat. Limiter la recherche à trois appels utiles par question.
- Vérifier la version dans les références et extraits obtenus. Mentionner une version dans la question ne garantit pas une réponse correspondant à cette version. Si seuls des exemples de main/latest arrivent, consulter la documentation officielle de la version et signaler la différence.
- Les requêtes portent exclusivement sur des bibliothèques publiques. Ne jamais transmettre identifiants clients, pièces internes, configurations réelles ou secrets.
- En cas d'indisponibilité, quota ou documentation insuffisante, utiliser les sources officielles avec web ou terminal. Ne pas bloquer la mission sur ce seul fournisseur ; ne pas utiliser un proxy ou changer les restrictions de clés.
- Citer les références retenues et vérifier le code proposé. Un exemple documentaire ne prouve pas son fonctionnement dans le projet.

Le service distant peut évoluer ; son code serveur n'est pas verrouillé par le dépôt. Le mode initial est anonyme et sans service local résident.
