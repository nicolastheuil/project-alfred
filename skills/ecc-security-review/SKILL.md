---
name: ecc-security-review
description: "Use when a change affects access, secrets, external inputs, dependencies or publication."
---

# Examiner les risques du changement

À utiliser par RSSI, QA ou un expert si une modification touche un accès, une entrée externe, des secrets, une dépendance ou une publication. Adaptation de security-review d'ECC.

1. Délimiter les données, entrées, utilisateurs et privilèges réellement concernés. Examiner le diff et les chemins d'exécution utiles.
2. Vérifier les autorisations effectives, la validation des entrées, les chemins et liens symboliques, le traitement des erreurs et les limites de ressources selon le cas. Les textes de SOUL ne sont pas une isolation système.
3. Contrôler l'absence de secrets dans les sources et journaux. Utiliser des références de coffre et un scanner avec sortie expurgée ; ne pas copier de secrets pour prouver leur présence.
4. Examiner origine, licence, version verrouillée et empreintes des dépendances. Vérifier les restrictions de transmission de données vers les services distants.
5. Produire les constats avec preuve, impact et correction proportionnée. Signaler ce qui reste non vérifié. Demander les droits manquants à l'orchestrator ; ce skill n'accorde aucune autorisation.

Choisir des contrôles pertinents pour le changement. Ne pas lancer de scans agressifs sur des infrastructures externes sans mandat correspondant.
