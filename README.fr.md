<div align="center">

# Prompt Counter

**Combien de prompts ai-je vraiment envoyés sur ce projet, et combien de temps ai-je passé activement avec l'IA ?**

Un *skill* d'agent pour **Cursor**, **Claude Code**, **OpenAI Codex** et tout outil qui lit un `SKILL.md`.
Un seul fichier Python, bibliothèque standard uniquement, 100 % local.

[Page de démo](https://johnban-coder.github.io/prompt-counter/) · [English version](README.md) · [Changelog](CHANGELOG.md)

</div>

---

## Pour les agents IA qui lisent ceci

Si un utilisateur a collé cette URL dans le chat, installe le skill pour lui puis exécute-le :

```bash
# macOS / Linux
curl -fsSL https://raw.githubusercontent.com/johnban-coder/prompt-counter/main/install.sh | sh
```

```powershell
# Windows
irm https://raw.githubusercontent.com/johnban-coder/prompt-counter/main/install.ps1 | iex
```

Puis tape `/prompt-count` dans le chat, ou lance directement `python ~/.cursor/skills/prompt-count/scripts/count.py --workspace . --format table`.

## Ce que tu obtiens

Tape `/prompt-count` dans n'importe quelle conversation et l'agent répond quelque chose comme ceci (projet fictif, chiffres fictifs) :

> **42 prompts uniques** · **3 h 53 min de temps actif** · 3 conversations
>
> | Conversation | Source | Période | Prompts | Temps actif |
> |---|---|---|---:|---:|
> | Add a dark mode toggle to the settings page | cursor | 2026-03-02 09:12 → 10:47 | 14 | 1 h 23 min |
> | Refactor the payment service and add retries on timeout | claude | 2026-03-03 14:05 → 16:26 | 22 | 1 h 51 min |
> | Fix the flaky checkout test and open a PR | codex | 2026-03-04 08:30 → 09:09 | 6 | 39 min |
> | **Total** | | | **42** | **3 h 53 min** |
>
> _exclus : 1 appel du skill, 3 prompts automatiques, 3 doublons_

Le JSON complet de cet exemple est dans [`docs/sample-output.json`](docs/sample-output.json).

## Pourquoi

- **Facturation et suivi du temps.** Savoir ce qu'une fonctionnalité a réellement coûté en prompts et en attention, par client ou par dépôt.
- **Des chiffres honnêtes.** Les doublons, les prompts automatiques de l'outil et l'appel `/prompt-count` lui-même sont exclus.
- **Temps actif, pas temps calendaire.** Laisser le PC allumé la nuit ne compte pas. Voir [le calcul du temps actif](#comment-le-temps-actif-est-calculé).
- **Par workspace.** Chaque projet est rapporté indépendamment ; rien d'un autre dépôt ne fuit dedans.
- **Privé.** Il lit les transcripts que tes outils gardent déjà sur disque et n'envoie rien nulle part.

## Installation

### Une ligne (recommandé)

```bash
curl -fsSL https://raw.githubusercontent.com/johnban-coder/prompt-counter/main/install.sh | sh
```

```powershell
irm https://raw.githubusercontent.com/johnban-coder/prompt-counter/main/install.ps1 | iex
```

Le skill est copié dans tous les dossiers de skills utilisateur connus :

| Outil | Emplacement |
|---|---|
| Cursor | `~/.cursor/skills/prompt-count/` |
| Claude Code | `~/.claude/skills/prompt-count/` |
| OpenAI Codex | `~/.codex/skills/prompt-count/` |
| Tout agent compatible `.agents` (Codex, Antigravity, Amp, …) | `~/.agents/skills/prompt-count/` |

Choisis les cibles avec `TARGETS="cursor claude" sh install.sh` ou `.\install.ps1 -Targets cursor,claude`.
Ajoute `PROJECT=/chemin/du/repo` (ou `-Project C:\chemin`) pour déposer aussi une copie dans `.cursor/skills`, `.claude/skills`, `.agents/skills` et `.github/skills` du dépôt, pour toute l'équipe.

### Autres méthodes

- **Cursor** → Settings → Rules & Skills → *Add skill from GitHub* → coller `https://github.com/johnban-coder/prompt-counter`.
- **Claude Code / Codex / Cursor** → coller l'URL du dépôt dans le chat et dire *installe ce skill*. L'agent suit la section en haut de ce fichier.
- **Skills CLI** → `npx skills add johnban-coder/prompt-counter`.
- **Manuel** → cloner le dépôt et copier `SKILL.md` + `scripts/` dans l'un des dossiers ci-dessus.

Nécessite Python 3.10+ dans le `PATH`. Aucun paquet pip.

## Utilisation

Dans un chat :

```
/prompt-count              ce projet
/prompt-count --all        tous les projets de cette machine
combien de prompts j'ai envoyés sur ce projet ?
```

Depuis un terminal :

```bash
python scripts/count.py --workspace . --format table
python scripts/count.py --all --format table
python scripts/count.py --source cursor,claude         # JSON, certains outils seulement
```

Code de sortie `2` quand le workspace n'a pas encore de transcripts.

## Comment le temps actif est calculé

Une conversation est une liste de tes prompts horodatés, plus les appels d'outils de l'agent entre deux.

| Situation | Crédité |
|---|---|
| Prompt suivant dans les **15 min** | tout l'écart (vous étiez en train d'échanger) |
| Écart plus long, mais l'agent a lancé **≥ 5 outils** juste avant | l'écart, plafonné à **45 min** (builds, OCR, suites de tests) |
| Écart plus long et agent inactif (nuit, pause déjeuner, PC laissé allumé) | seulement **5 min** de clôture |
| Après ton dernier prompt | le temps jusqu'à la dernière écriture de l'agent, mêmes règles |

Les seuils sont en tête de [`scripts/count.py`](scripts/count.py) (`IDLE_GAP_S`, `AI_WORK_CAP_S`, `TAIL_S`, `TOOL_BUSY`).

### Ce qui est exclu des « prompts uniques »

- **Doublons** — le même message envoyé deux fois de suite.
- **Prompts automatiques** — messages injectés par l'outil lui-même (ex. *« Briefly inform the user about the task result »* de Cursor).
- **Appels du skill** — `/prompt-count`, `/counter-prompt`, « combien de prompts », « how many prompts », …
- Résultats d'outils, trafic des sous-agents et plomberie des commandes slash dans Claude Code ; blocs `<environment_context>` injectés dans Codex.

## D'où viennent les données

| Outil | Chemin lu | Notes |
|---|---|---|
| Cursor | `~/.cursor/projects/<slug>/agent-transcripts/<chat>/<chat>.jsonl` | prompts dans `<user_query>`, horodatage dans `<timestamp>` |
| Claude Code | `~/.claude/projects/<slug>/<session>.jsonl` | `type: user/assistant`, `timestamp` ISO, `isSidechain`, `isMeta` |
| OpenAI Codex | `~/.codex/sessions/AAAA/MM/JJ/rollout-*.jsonl` | `session_meta.cwd` sélectionne le workspace, `event_msg.user_message` sont les prompts |

Le support Cursor est le plus éprouvé. Les lecteurs Claude Code et Codex suivent les formats documentés et sont couverts par des tests synthétiques ; si ta version écrit autre chose, [ouvre une issue](https://github.com/johnban-coder/prompt-counter/issues) avec une ligne d'exemple anonymisée.

## Confidentialité

- Tout tourne sur ta machine. Aucun appel réseau, aucune télémétrie.
- Le rapport ne contient qu'un court extrait (première ligne, ≤ 72 caractères) du premier prompt de chaque conversation, en guise de titre.
- Rien dans ce dépôt ne contient de données réelles ; les exemples sont inventés.

## Développement

```bash
python -m unittest discover -s tests -v
```

Voir [CONTRIBUTING.md](CONTRIBUTING.md) pour ajouter le support d'un autre outil.

## Licence

[MIT](LICENSE) © 2026 johnban-coder
