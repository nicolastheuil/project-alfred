# Construction de la v1

## Ce qui existe dans ce dépôt

Le contrat de plateforme, les modèles de SOUL, les schémas de personnalisation documentés, le guide illustré et les contrôles de cohérence et de publication. Le contrôle CI vérifie ces artefacts ; il ne certifie pas encore une installation de production.

## Ce qui reste à construire et éprouver

- Bootstrap reproductible sur une VM Debian vierge, versions du moteur et dépendances verrouillées.
- Composition du socle et de l'instance, migration et retour à une version précédente.
- Profils persistants, orchestration Kanban et limite globale réellement appliquée.
- Isolation des workers, courtage des secrets et contrôle des opérations externes.
- Dossiers clients partagés, accès documentaire et gestion des preuves.
- Accès IDE et canaux de messagerie, avec routes et livraisons testées.
- Supervision, reprises, sauvegardes chiffrées et reconstruction de l'état.
- Détection de changements, rédaction documentaire et synchronisation fiable des deux dépôts.

## Quand la v1 pourra-t-elle être appelée prête ?

Une installation neuve doit réussir depuis les dépôts et les accès externes prévus. Une instance personnalisée doit pouvoir être reconstruite sans son ancienne VM. Des missions représentatives doivent aller de la demande à un résultat vérifié. Les refus d'accès, la livraison des résultats, les reprises après interruption et les plafonds de ressources doivent être éprouvés.

Le guide illustré décrit cette cible. Chaque fonctionnalité sera marquée comme validée avec une preuve de fonctionnement avant d'être annoncée comme disponible.
