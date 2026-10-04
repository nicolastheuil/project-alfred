# ECC, Context7, Headroom et RTK : quelle place dans Alfred ?

Dans le bureau d'études, ECC fournit des fiches de méthode, Context7 une bibliothèque documentaire, RTK une lecture condensée des sorties de commandes et Headroom une compression du contexte envoyé au modèle. Ces fonctions répondent à des besoins différents : les installer tous ne suffit pas à créer une équipe autonome.

**État au 4 octobre 2026 : aucun de ces quatre modules n'est installé sur la nouvelle VM v1.** Le moteur Hermes, ses dépendances ACP/MCP et la zram sont installés. Les décisions ci-dessous définissent les prochaines intégrations ou essais ; elles ne décrivent pas des services déjà opérationnels.

## La décision pour chaque module

| Module et auteurs | Fonction | Choix pour la v1 | État réel |
|---|---|---|---|
| [ECC — affaan-m et contributeurs](https://github.com/affaan-m/ECC), anciennement Everything Claude Code | Skills, règles, procédures de développement, hooks et conventions de coopération | Reprendre une sélection de skills adaptés aux experts et à la revue. Examiner l'adaptateur Hermes officiel avant de reprendre un ancien pont spécifique. | Sélection à réaliser ; aucun skill importé. |
| [Context7 — Upstash et contributeurs](https://github.com/upstash/context7) | Recherche de documentation et d'exemples de bibliothèques, avec possibilité de cibler une version | Prévu comme outil documentaire à la demande pour les experts qui développent. Préférer le transport distant si compatible pour limiter les services locaux. | Connexion MCP, authentification et essais à réaliser. |
| [Headroom — Headroom Labs et contributeurs](https://github.com/headroomlabs-ai/headroom) | Compression de sorties d'outils et de contenu ; interfaces bibliothèque, proxy et MCP | Différé : commencer par mesurer les requêtes réelles, puis essayer une intégration limitée si le contexte représente un coût important. | Aucun proxy ni serveur MCP installé ; aucun gain mesuré sur Alfred v1. |
| [RTK — rtk-ai et contributeurs](https://github.com/rtk-ai/rtk) | Binaire Rust condensant les sorties de commandes courantes de développement | Candidat à un essai ciblé sur les commandes verbeuses. Le faible nombre de services permanents en fait un candidat intéressant, mais son intérêt doit être mesuré. | Binaire et réécriture de commandes non installés. |

Ces choix sont ceux de Project Alfred. Les capacités des outils sont documentées par leurs auteurs ; leurs pourcentages promotionnels ne constituent pas des mesures sur notre plateforme.

## ECC : une boîte à méthodes pour les ingénieurs

Un skill explique comment traiter une catégorie de problème. Il ne remplace ni les compétences du modèle, ni les données du client, ni les outils donnant accès à son infrastructure. Pour Alfred, la sélection doit couvrir des besoins concrets : investigation, développement, revue de code, vérification et rédaction de procédures.

La [documentation Hermes d'ECC](https://github.com/affaan-m/ECC/blob/ef648e01899ba3e8dc6371642deaaf64b4477775/docs/HERMES-SETUP.md) décrit notamment l'import de skills et une mémoire de coopération entre harnesses. Cette existence ne prouve pas sa compatibilité avec notre version verrouillée d'Hermes. Chaque skill retenu devra être lu, adapté aux permissions et rattaché aux rôles concernés ; son origine, sa révision et sa licence seront conservées.

Alfred conservera sa mémoire relationnelle ; les experts leurs procédures et connaissances techniques. Les faits clients auront un référentiel partagé avec source, date et statut de validation. Le Memory Vault d'ECC n'est pas retenu comme deuxième référentiel client initial : s'il est essayé plus tard pour des transmissions entre IDE, il devra respecter ce référentiel et les frontières de confidentialité. Ses contenus rappelés restent des informations à vérifier, pas des instructions autorisées.

**Acceptation :** une mission représentative avec puis sans les skills sélectionnés, résultats vérifiables, aucun déclenchement obligatoire sans pertinence, aucun déplacement de mémoire personnelle vers les experts. Aucun hook de l'alpha n'est reconduit automatiquement.

## Context7 : consulter la bonne notice au bon moment

Quand un ingénieur écrit du code pour une bibliothèque donnée, il peut résoudre son identifiant puis demander une documentation ciblée. Context7 vise cette consultation de documentation logicielle ; les pièces internes et configurations clients suivront leur propre stockage et recherche.

Le chargement des outils sera limité aux rôles et missions concernés. Les recherches envoyées au service devront porter sur des bibliothèques et questions techniques sans credentials ni pièces clients. La documentation obtenue devra correspondre à la version utilisée ; son exemple doit encore être vérifié par l'ingénieur. L'accès distant dépend aussi de la disponibilité du service et des limites du compte.

**Acceptation :** connexion avec le MCP du moteur verrouillé, recherche sur une version précise, essai d'indisponibilité avec recours à la documentation officielle, observation des délais et vérification du périmètre des requêtes.

## Headroom : vérifier que la compression aide le travail

Un proxy résident ajoute un service et peut modifier les échanges avec les fournisseurs. Une API de compression ou un serveur MCP n'a pas exactement le même périmètre. Le mode choisi devra être explicite : il ne suffit pas qu'un service réponde à un contrôle de santé pour prouver que les requêtes des agents y passent.

La petite VM impose de mesurer RAM et CPU, ainsi que les dépendances du mode retenu. Nous commencerons par limiter les lectures inutiles, cibler les recherches et utiliser les fonctions natives de gestion du contexte. Headroom devient pertinent si ces mesures laissent un coût significatif et si sa compression conserve les informations utiles à la décision.

**Acceptation :** mêmes missions et modèles avec puis sans compression ; tokens facturés, coût, latence, RAM/CPU, erreurs et qualité des livrables relevés. Les informations originales nécessaires à une vérification doivent rester récupérables. L'intégration devra respecter les restrictions de fournisseurs et le routage des clés propres à l'instance.

## RTK : condenser les sorties sans perdre les preuves

RTK peut réduire ce que le modèle lit sur des commandes de développement verbeuses. La sélection doit porter sur des commandes identifiées ; une réécriture générale de tout le terminal risquerait de masquer une erreur ou une donnée nécessaire à un diagnostic.

Le résultat condensé doit conserver les échecs et leurs codes de sortie. Les sorties brutes nécessaires aux preuves seront conservées dans les données opérationnelles privées, avec leurs règles de rétention, et resteront accessibles à l'ingénieur. Headroom et RTK seront évalués séparément avant un éventuel cumul pour attribuer correctement les gains et les pertes.

**Acceptation :** binaire ARM64 à version et empreinte verrouillées, comparaison de commandes représentatives réussies et échouées, fidélité des diagnostics, accès à la sortie brute et mesure du gain de contexte. Aucun pourcentage d'économie n'est garanti à ce stade.

## Zram : le composant déjà actif

La [zram via zram-tools](../THIRD_PARTY_NOTICES.md) fournit du swap compressé en RAM. Elle peut absorber certains pics en échange de CPU, sans ajouter de mémoire physique. Sa configuration actuelle utilise zstd, une taille logique égale à la RAM physique, la priorité 100 et une swappiness de 100. L'activation après redémarrage a été vérifiée ; le comportement avec l'équipe et les connecteurs en charge reste à mesurer.

## Sources et licences de l'étude

Les révisions ci-dessous identifient les sources examinées. **Ce sont des références d'étude, pas des versions installées ni un verrou de déploiement.** L'adoption d'un module ajoutera son verrou, son installation reproductible et son état vérifié aux [crédits des composants utilisés](../THIRD_PARTY_NOTICES.md).

| Projet | Révision examinée le 4 octobre 2026 | Licence du dépôt |
|---|---|---|
| ECC | [`ef648e01899ba3e8dc6371642deaaf64b4477775`](https://github.com/affaan-m/ECC/tree/ef648e01899ba3e8dc6371642deaaf64b4477775) | [MIT](https://github.com/affaan-m/ECC/blob/ef648e01899ba3e8dc6371642deaaf64b4477775/LICENSE) |
| Context7 | [`bfa02ea67b5707fe0e0a673faa49d0f50b28c80b`](https://github.com/upstash/context7/tree/bfa02ea67b5707fe0e0a673faa49d0f50b28c80b) | [MIT](https://github.com/upstash/context7/blob/bfa02ea67b5707fe0e0a673faa49d0f50b28c80b/LICENSE) |
| Headroom | [`1cf496612e781ef8d67ff87ee4f78037492f0bc7`](https://github.com/headroomlabs-ai/headroom/tree/1cf496612e781ef8d67ff87ee4f78037492f0bc7) | [Apache-2.0](https://github.com/headroomlabs-ai/headroom/blob/1cf496612e781ef8d67ff87ee4f78037492f0bc7/LICENSE) |
| RTK | [`c356374fc1c9cff132c02484d2b9195c796b8e8f`](https://github.com/rtk-ai/rtk/tree/c356374fc1c9cff132c02484d2b9195c796b8e8f) | [Apache-2.0](https://github.com/rtk-ai/rtk/blob/c356374fc1c9cff132c02484d2b9195c796b8e8f/LICENSE) |

La licence du code d'un client ne définit pas les conditions d'utilisation de son service distant. Chaque intégration précisera également ce qu'elle transmet et les accès dont elle dépend.
