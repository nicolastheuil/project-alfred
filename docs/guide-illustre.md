# Le bureau d'études d'Alfred

Ce guide décrit **la cible v1**, pas des fonctions déjà toutes déployées. Imagine un bureau d'études : une réception, un chef de projet, des spécialistes et un tableau de suivi. Le tableau garde les engagements ; les spécialistes ne restent pas tous devant leur bureau lorsqu'il n'y a rien à faire.

## Une porte d'entrée, plusieurs mains

**Alfred** connaît son utilisateur et reformule son besoin. Il garde la relation et livre le résultat. **Orchestrator** organise la mission : étapes, compétences, dépendances et critères d'acceptation. Les **experts** connaissent leurs domaines. **QA** examine les preuves de qualité ; **RSSI** examine les risques lorsqu'ils le nécessitent. Le **documentaliste** explique les changements de la plateforme.

Une SOUL définit l'identité, le rôle et la façon de travailler d'un agent. Sa mémoire conserve des faits et méthodes utiles. Ce sont deux choses différentes : une instruction de rôle ne constitue pas une preuve sur un client.

```mermaid
flowchart TB
    C[IDE ou messagerie] --> A[Alfred : accueil]
    A --> G[Orchestrator : coordination]
    G --> Q[(Kanban : travail durable)]
    Q --> E[Expertise adaptée à la demande]
    E --> R[Revue adaptée au résultat et au risque]
    R --> G
    G --> A
    A --> C
    X[Documentaliste] -. changements de plateforme .-> DOC[Documentation]
```

Un profil peut exister sans avoir un processus actif. Le scheduler ouvre les postes de travail nécessaires, dans une limite globale. Une configuration initiale de deux travaux simultanés et d'un travail par profil sert de point de départ pour une petite VM ; les mesures déterminent les plafonds adaptés.

## Un exemple concret

Demande fictive : « Compare deux approches pour atteindre mon objectif et prépare une recommandation. »

Alfred comprend le résultat attendu, le contexte professionnel ou personnel et les contraintes utiles. Orchestrator distingue les informations à réunir, les expertises nécessaires et la vérification. Les experts concernés consultent le dossier de contexte autorisé. La revue vérifie les arguments et les sources. Alfred présente le résultat et les incertitudes qui restent pertinentes pour son utilisateur.

Le même flux sert à un dossier professionnel, à la marque personnelle, au suivi d'un programme sportif ou à une question de nutrition. Ces exemples sont non exhaustifs : les spécialités sont configurables et ne constituent pas une liste fermée des capacités d'Alfred. Les critères, les sources, les outils et le niveau de revue changent selon le domaine ; les contextes et permissions restent distincts. Une nouvelle spécialité conserve sa SOUL et sa mémoire métier sans alourdir celle d'Alfred. Cela décrit la cible du socle ; le périmètre personnel de l'instance initiale reste à activer.

```mermaid
sequenceDiagram
    actor U as Utilisateur
    participant A as Alfred
    participant G as Orchestrator
    participant K as Kanban
    participant E as Expertise adaptée
    participant Q as QA
    U->>A: Résultat souhaité et contraintes
    A->>G: Mission qualifiée et mandat
    G->>K: Étapes, dépendances, critères
    K->>E: Étape prête et périmètre autorisé
    E->>K: Livrable, sources et limites
    K->>Q: Résultat à vérifier
    Q->>K: Verdict et preuves
    K->>G: Étapes terminées
    G->>A: Synthèse vérifiée
    A->>U: Résultat exploitable
```

Le retour d'un expert ne suffit pas à déclarer la mission terminée. Il faut satisfaire ses critères et conserver les preuves utiles. Une étape qui attend une autre libère sa place au lieu de garder un agent actif sans travail.

## Où vit la connaissance ?

L'analogie est celle de trois classeurs : « mon utilisateur », « mon métier » et « le dossier concerné ». Le dossier peut être celui d'un client professionnel ou d'un contexte personnel autorisé. Copier tout dans le premier rendrait l'assistant moins clair et multiplierait les contradictions.

```mermaid
flowchart LR
    A[Alfred] --> U[(Relation utilisateur<br/>Préférences et besoins)]
    E[Experts] --> T[(Mémoires d'expertise<br/>Méthodes par domaine)]
    E --> C[(Dossier de contexte autorisé<br/>Professionnel ou personnel<br/>Faits sourcés et datés)]
    G[Orchestrator] --> K[(Missions<br/>Étapes et preuves)]
    P[PDF et documents] --> I[Index documentaire]
    I --> E
```

Un fait du dossier porte une source, une date et un état : observation, hypothèse, vérifié ou périmé. Un expert peut ainsi distinguer une observation récente d'une hypothèse ancienne. Les experts concernés partagent ces faits dans le contexte autorisé ; la mémoire relationnelle d'Alfred et les données des autres contextes ne sont pas recopiées dans leurs mémoires.

L'index documentaire aide à retrouver un passage utile. Il ne transforme pas un PDF en connaissance certaine du modèle et ne remplace pas une vérification. La référence, la version et le contexte du passage restent nécessaires.

## Comment une décision se construit-elle ?

Le harness prépare le contexte et encadre les outils. Le modèle propose un plan ou une action. L'exécution fournit un résultat. La vérification décide s'il faut continuer, corriger ou consulter l'utilisateur.

```mermaid
flowchart TD
    D[Demande et résultat attendu] --> C[Contexte utile<br/>Rôle, dossier, sources, mandat]
    C --> H[Hypothèses et informations manquantes]
    H --> P[Plan d'actions proposé]
    P --> M{Action dans le mandat<br/>et permissions effectives ?}
    M -->|Oui| O[Outil ou travail expert]
    M -->|Non| U[Clarification ou extension du mandat]
    U --> C
    O --> R[Résultat et preuves]
    R --> V{Critères satisfaits ?}
    V -->|Non| H
    V -->|Oui| S[Synthèse et restitution]
```

On documente les hypothèses retenues, les décisions, les sources, les appels d'outils et les vérifications. Ces traces expliquent le travail observable ; elles ne prétendent pas être une transcription exacte du fonctionnement interne du modèle.

Une SOUL qui demande de respecter les permissions ne crée pas ces permissions. L'accès aux fichiers, au coffre et aux opérations externes doit être imposé par le logiciel. Une identité de profil ne constitue pas, à elle seule, une isolation de sécurité.

## Et si la VM s'arrête au milieu ?

Le tableau conserve les étapes et leurs résultats. Au redémarrage, on examine les opérations réellement effectuées avant de relancer. Un fichier déjà créé ou un changement externe déjà appliqué ne doit pas être reproduit aveuglément.

```mermaid
stateDiagram-v2
    [*] --> Preparee
    Preparee --> Prete: dépendances satisfaites
    Prete --> EnCours: slot disponible
    EnCours --> AVerifier: résultat enregistré
    AVerifier --> Terminee: critères satisfaits
    AVerifier --> Prete: correction nécessaire
    EnCours --> Reprise: interruption détectée
    Reprise --> AVerifier: effet déjà accompli et confirmé
    Reprise --> Prete: relance sûre
    Reprise --> Attente: état externe incertain
    Attente --> Reprise: information obtenue
    Terminee --> [*]
```

La machine à états ci-dessus est un schéma logique de la cible. Ses libellés ne sont pas une liste contractuelle des statuts internes du moteur.

## Comment la documentation reste-t-elle à jour ?

Le logiciel repère un changement de configuration, rôle ou skill, conserve son diff et prépare les validations. Le documentaliste explique ce qui change. Les contrôles comparent le texte aux paramètres vérifiables. Les commits et les erreurs de publication sont suivis explicitement.

Le contexte du documentaliste public contient uniquement les éléments publics. La personnalisation et la documentation d'une instance privée suivent un circuit distinct. Une tâche métier ordinaire n'est pas un changement du produit.

## Plusieurs portes, le même Alfred

Hermes Desktop vise un backend Remote gateway supervisé, accessible en HTTPS authentifié. L’accès Desktop actuellement vérifié passe par un tunnel SSH manuel ; Connect via SSH est une alternative privée à éprouver. WhatsApp et Teams passent par la gateway de messagerie ; les IDE peuvent joindre la CLI ou un backend ACP compatible via SSH. [Le guide de communication](communiquer-avec-alfred.md) explique les réglages, les sessions et l’état réellement testé.
