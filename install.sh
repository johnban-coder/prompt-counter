#!/usr/bin/env sh
# Installs the Prompt Counter skill for Cursor, Claude Code, Codex and any agent
# that reads ~/.agents/skills.
#
#   curl -fsSL https://raw.githubusercontent.com/johnban-coder/prompt-counter/main/install.sh | sh
#
#   TARGETS="cursor claude" sh install.sh        # only some tools
#   PROJECT=/path/to/repo sh install.sh          # also install inside a repo
set -eu

REPO="johnban-coder/prompt-counter"
REF="${REF:-main}"
SKILL_NAME="prompt-count"
TARGETS="${TARGETS:-cursor claude codex agents}"
PROJECT="${PROJECT:-}"

here="$(cd "$(dirname "$0")" 2>/dev/null && pwd || true)"
if [ -n "$here" ] && [ -f "$here/SKILL.md" ]; then
  SRC="$here"
else
  tmp="$(mktemp -d)"
  echo "Downloading $REPO@$REF ..."
  if command -v git >/dev/null 2>&1; then
    git clone --quiet --depth 1 --branch "$REF" "https://github.com/$REPO.git" "$tmp/src"
    SRC="$tmp/src"
  else
    curl -fsSL "https://github.com/$REPO/archive/refs/heads/$REF.tar.gz" | tar -xz -C "$tmp"
    SRC="$(find "$tmp" -maxdepth 1 -mindepth 1 -type d | head -n 1)"
  fi
fi

install_skill() {
  dest="$1"
  mkdir -p "$dest"
  cp "$SRC/SKILL.md" "$dest/"
  rm -rf "$dest/scripts" && cp -R "$SRC/scripts" "$dest/scripts"
  [ -f "$SRC/LICENSE" ] && cp "$SRC/LICENSE" "$dest/" || true
  echo "  installed -> $dest"
}

echo "Prompt Counter — installing skill '$SKILL_NAME'"
for t in $TARGETS; do
  case "$t" in
    cursor) install_skill "$HOME/.cursor/skills/$SKILL_NAME" ;;
    claude) install_skill "$HOME/.claude/skills/$SKILL_NAME" ;;
    codex)  install_skill "$HOME/.codex/skills/$SKILL_NAME" ;;
    agents) install_skill "$HOME/.agents/skills/$SKILL_NAME" ;;
    *) echo "  unknown target '$t' (cursor, claude, codex, agents)" >&2 ;;
  esac
done

if [ -n "$PROJECT" ]; then
  for rel in .cursor/skills .claude/skills .agents/skills .github/skills; do
    install_skill "$PROJECT/$rel/$SKILL_NAME"
  done
fi

if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
  echo "warning: Python 3.10+ not found on PATH — the skill needs it to run." >&2
fi

echo
echo "Done. Open a chat in your AI tool and type:  /prompt-count"
