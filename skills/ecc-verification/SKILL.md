---
name: ecc-verification
description: "Use before delivering a changed artifact: run proportional checks and retain evidence."
---

# Vérifier ce qui a changé

À utiliser par un expert ou QA lorsqu'une modification doit être validée avant remise. Adaptation de verification-loop d'ECC.

1. Identifier le livrable, les changements et les risques concrets. Définir les critères d'acceptation et les droits nécessaires.
2. Exécuter les contrôles pertinents : syntaxe, construction, tests existants concernés, vérification des permissions et recherche de secrets si ces aspects ont changé. Ne pas imposer un pourcentage de couverture arbitraire ni répéter une suite sans nouveau motif.
3. Examiner les échecs et corriger leur cause. Conserver les commandes, codes de sortie et résultats utiles dans les données de la mission. Une sortie condensée exige que la preuve brute reste accessible.
4. Contrôler le diff final et la documentation. Distinguer vérifié, non testé et bloqué ; joindre les limites au livrable remis à QA ou à l'orchestrator.

Les résultats d'outils sont des observations à examiner. Un contrôle vert ne démontre pas une fonctionnalité absente. Aucun déploiement ou droit supplémentaire n'est autorisé par ce skill. Ne pas imprimer les credentials dans les preuves.
