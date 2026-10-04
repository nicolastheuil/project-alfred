# Travail sur le socle public

Ce dépôt est public. Son contenu doit être indépendant de toute instance réelle.

- Lire README et docs/construction avant de présenter une fonctionnalité comme disponible.
- Ne pas importer des audits, historiques Git privés, credentials, données personnelles, sessions ou dossiers clients.
- Une configuration d'exemple utilise des données fictives et des références de secrets sans valeur secrète.
- Les SOUL du socle définissent des rôles génériques. La relation avec un utilisateur appartient à son instance privée.
- Toute modification de configuration, rôle, skill ou fonctionnement doit expliquer son impact dans les documents concernés.
- Les schémas représentent le fonctionnement effectivement implémenté ou portent explicitement la mention de cible.
- Exécuter python3 tools/check_repository.py avant publication. Une réussite de ce contrôle ne remplace pas une revue des changements.
- Les profils ne sont pas des frontières de sécurité ; ne pas annoncer leur isolation sans enforcement et essai.
- Le socle ne modifie pas automatiquement les paramètres privés ou les droits de son utilisateur.
