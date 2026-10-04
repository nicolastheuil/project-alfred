---
name: configuration-lint
description: Use before publishing changes to SOUL, skills or agent instructions: run LintLang and review coverage.
---

# Relire les instructions de configuration

Disponible pour QA et le documentaliste lorsqu'une SOUL, un skill ou des instructions changent.

Exécuter `alfred-lint scan <fichiers> --format json --fail-on fail` sur les instructions effectivement modifiées. Relire les constats : LintLang vérifie des structures et heuristiques, pas la justesse de l'architecture ni toutes les contradictions du langage naturel. Une entrée SKIPPED ou non inspectée exige un contrôle explicite ; ne pas la présenter comme validée.

Corriger les constats justifiés puis refaire le contrôle concerné. Les avis medium nécessitent une revue et les high/critical bloquent la publication jusqu'à résolution. Conserver une preuve expurgée dans la mission. Ne pas utiliser --fix automatiquement et ne pas fabriquer de baseline pour masquer un échec.

Ce contrôle complète la validation des dépôts et la recherche de secrets. Il ne choisit pas entre dépôt public et personnalisation privée ; en cas de doute sur cette classification, demander confirmation à l'utilisateur par Alfred.
