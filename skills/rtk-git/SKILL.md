---
name: rtk-git
description: "Use when Git inspection output is verbose: explicitly condense status, log, diff or show and retain raw evidence."
---

# Lire des sorties Git condensées

Pour dev, devops, QA, le documentaliste et platform-engineer. Utiliser `alfred-rtk git status`, `alfred-rtk git log`, `alfred-rtk git diff` ou `alfred-rtk git show` si la lecture est verbeuse. Les autres commandes utilisent le terminal normal. Aucun hook ni réécriture globale n'est installé.

Le wrapper indique le dossier privé de preuves : stdout, stderr, arguments et codes de chaque invocation Git effectuée par RTK. Consulter les fichiers bruts lorsque le résumé ne suffit pas, en cas d'erreur, ou pour constituer la preuve d'une revue. Le résumé ne remplace pas un diff complet avant publication. Vérifier le code de sortie de la commande.

Les preuves vivent dans state/rtk/raw du profil, hors Git, avec une rétention de sept jours et cinquante appels, purgée à l'appel suivant. Copier uniquement les preuves utiles dans la mission si une conservation plus longue est nécessaire. Ne pas partager une sortie pouvant contenir des secrets ou des données clients.

RTK n'accorde aucun droit supplémentaire. Ne pas condenser les diagnostics système ni les citations de documents par ce mécanisme Git. Les économies de caractères observées ne sont pas un budget garanti en tokens ou en argent.
