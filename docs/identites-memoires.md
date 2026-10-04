# Donner une identité à l'équipe

Une identité persistante est un dossier de profil Hermes, avec sa SOUL et ses fichiers de mémoire. Elle existe même quand aucun agent ne tourne. La composition des identités n'ouvre pas les canaux, ne donne aucun credential et ne déclenche aucune mission.

## Un flux commun, des domaines configurables

Alfred comprend et restitue ; **orchestrator** coordonne ; les experts réalisent ; les revues vérifient. Le socle générique propose six profils : alfred, orchestrator, expert, qa, rssi et documentaliste. `config/team-seed.json` décrit cette base. La spécialité et le contexte d'un expert peuvent être professionnels ou personnels ; le flux de mission reste le même.

L'instance peut fournir son propre `team_seed` et ses `profile_memory_seeds`. Son fichier d'équipe utilise le même format que le socle : identifiant, description, SOUL générique du socle, domaine et mémoire initiale. On peut ainsi avoir plusieurs expertises persistantes et en ajouter sans déplacer leur savoir métier dans Alfred. Une déclaration de profil ne crée pas les outils ou permissions de ce domaine.

## Ce que le composeur écrit

| Destination native | Contenu |
|---|---|
| `profiles/alfred/SOUL.md` | SOUL relationnelle de l'instance |
| `profiles/alfred/memories/USER.md` | Préférences sourcées de l'utilisateur |
| `profiles/alfred/memories/MEMORY.md` | Connaissances relationnelles durables |
| `profiles/<autre-role>/SOUL.md` | Rôle générique et spécialisation |
| `profiles/<autre-role>/memories/MEMORY.md` | Mémoire métier initiale du rôle |
| `profiles/<autre-role>/memories/USER.md` | Vide ; la mémoire utilisateur native est désactivée pour ce rôle |

Les mémoires sont courtes, compatibles avec les plafonds natifs initiaux de 2 200 caractères pour MEMORY et 1 375 pour USER. Les entrées sont séparées par `§`. Le savoir détaillé et les documents ne doivent pas être intégralement chargés dans le prompt. Les nouvelles sessions chargent leur propre instantané de mémoire ; une session déjà ouverte ne reçoit pas magiquement une mise à jour.

L'espace `shared` se trouve sous le home Hermes : `professional/clients`, `personal`, `expertise/<profil>`, `missions` et `migration`. Les faits clients sont partagés entre les expertises concernées, les contextes personnels disposent d'un espace distinct. La création du dossier personnel n'active aucune mission personnelle. Ces répertoires vides préparent le stockage ; ils ne constituent pas encore une base documentaire indexée ou un contrôle d'accès par contexte.

## Composer sur le socle installé

Préparer dans l'instance les trois fichiers relationnels et leurs chemins dans `instance.json`, puis, si nécessaire, un fichier d'équipe et les mémoires initiales spécifiques. Les sources doivent être des fichiers relus ; ne pas prendre les instructions d'un ancien export comme autorisations courantes.

```sh
sudo python3 bootstrap/seed-profiles.py \
  --instance-source /chemin/vers/instance-privee --dry-run
sudo python3 bootstrap/seed-profiles.py \
  --instance-source /chemin/vers/instance-privee
```

Le script utilise le compte système déclaré dans le verrou de runtime, appelle la création native Hermes sans clonage, alias ni skills automatiques, applique les SOUL et mémoires, puis sélectionne Alfred comme profil par défaut. Il exige que les processus de ce compte soient arrêtés. Il n'appelle aucun modèle et ne démarre aucun gateway.

Un fichier existant doit correspondre à la dernière empreinte appliquée ou au nouveau contenu. Une mémoire ayant évolué depuis son injection provoque un refus et exige une fusion relue. Les fichiers remplacés sont conservés dans `/var/lib/alfred/identity-backups` ; les empreintes appliquées sont dans `identity-manifest.json`. Une interruption peut laisser une composition partielle : ce composeur initial ne promet pas une transaction atomique entre tous les profils.

## Migrer une ancienne mémoire

Conserver les sources alpha avec leurs empreintes dans les données privées. Trier chaque entrée entre relation, expertise, faits du dossier, état de mission et ancienne configuration. Les observations de l'ancien système deviennent des éléments historiques à vérifier ; les anciennes autorisations restent archivées. Une biographie ou un inventaire client rédigé par l'agent sans source directe ne devient pas un fait confirmé.

Ce tri ne supprime pas l'historique et ne copie pas les conversations dans le socle public. Les mémoires qui évoluent pendant les missions relèvent de la sauvegarde d'état, séparée des fichiers de configuration et de leurs graines initiales.

## Limite de sécurité actuelle

Tous ces profils utilisent encore le même compte système. Leur séparation de mémoire est logique : elle ne constitue pas une isolation des fichiers entre agents. Le courtage des secrets, l'accès aux contextes et les limites d'exécution doivent être imposés et testés par le harness avant de confier des accès réels aux workers.
