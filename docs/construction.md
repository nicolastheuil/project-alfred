# Construction de la v1

## Ce qui existe dans ce dépôt

Le contrat de plateforme, les modèles de SOUL, les schémas de personnalisation documentés, le guide illustré, la préparation système Debian, l'installation du moteur Hermes verrouillé, les crédits des composants, la supervision systemd les modules experts retenus et les contrôles de cohérence et de publication. Le contrôle CI vérifie ces artefacts et la syntaxe du bootstrap ; il ne certifie pas encore une installation de production.

## Ce qui reste à construire et éprouver

- Bootstrap complet d'une instance sur VM vierge : prérequis et moteur ont été exécutés ; composition des profils, accès et état restent à éprouver.
- Composition du socle et de l'instance, migration et retour à une version précédente.
- Profils persistants composés ; orchestration Kanban et limite globale à éprouver sur des missions représentatives.
- Isolation des workers, courtage des secrets et contrôle des opérations externes.
- Dossiers clients partagés, accès documentaire et gestion des preuves.
- Accès IDE et canaux de messagerie, avec routes et livraisons testées.
- Supervision des services et reprise sur panne testées ; escalade spécialisée, sauvegardes chiffrées et reconstruction de l'état à éprouver intégralement.
- Détection de changements, rédaction documentaire et synchronisation fiable des deux dépôts.

## Quand la v1 pourra-t-elle être appelée prête ?

Une installation neuve doit réussir depuis les dépôts et les accès externes prévus. Une instance personnalisée doit pouvoir être reconstruite sans son ancienne VM. Des missions représentatives doivent aller de la demande à un résultat vérifié. Les refus d'accès, la livraison des résultats, les reprises après interruption et les plafonds de ressources doivent être éprouvés.

Le guide illustré décrit cette cible. Chaque fonctionnalité sera marquée comme validée avec une preuve de fonctionnement avant d'être annoncée comme disponible.

## Modules étudiés et mis en service

L’[étude de huit outils](etude-outils-v1.md) décrit les décisions, les mesures et les limites. Les méthodes ECC, Context7 distant et LintLang sont intégrés sans daemon supplémentaire ; RTK dispose d’un bootstrap de compilation compatible Debian 12. La sélection d’outils native a été corrigée et sa découverte testée. Ces acceptations ne certifient pas le circuit complet de missions.
