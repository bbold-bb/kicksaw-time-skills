#!/usr/bin/env bash
#
# Install or update the log-time and time-report skills.
#
# Copying a skill folder is a snapshot, so `git pull` does not update an
# installed skill; re-run this script after pulling. It is safe to run over an
# existing install: your profile lives in ~/.claude/kicksaw-time/profile.json,
# outside the skill folders, so an update cannot replace it.
#
#   ./install.sh                  install or update in ~/.claude/skills
#   ./install.sh --project PATH   install or update in PATH/.claude/skills
#   ./install.sh --check          compare what is installed against this repo
#   ./install.sh --codex          for Codex: ~/.agents/skills, or PATH/.agents/skills
#                                 with --project; combines with --check
#   ./install.sh --help

set -euo pipefail

SKILLS=(log-time time-report)
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Skill folders live under skills/, the layout the Skills CLI expects.
SRC="$REPO/skills"
PROJECT=""
AGENT=claude
# User data, deliberately outside any folder this script replaces.
PROFILE_HOME="$HOME/.claude/kicksaw-time/profile.json"
MODE=install

usage() { sed -n '3,16p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

while [ $# -gt 0 ]; do
  case "$1" in
    --check)   MODE=check; shift ;;
    --codex)   AGENT=codex; shift ;;
    --project) [ $# -ge 2 ] || { echo "--project needs a path" >&2; exit 2; }
               PROJECT="$(cd "$2" 2>/dev/null && pwd)" || {
                 echo "No such directory: $2" >&2; exit 2; }
               shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *)         echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

# Claude Code reads skills from .claude/skills; Codex reads them from .agents/skills.
if [ "$AGENT" = codex ]; then SKILLS_DIR=.agents/skills; else SKILLS_DIR=.claude/skills; fi
DEST_ROOT="${PROJECT:-$HOME}/$SKILLS_DIR"

# Version lives in the SKILL.md frontmatter; it is the only source.
# No pipe here: under `set -o pipefail` a missing file would make this return
# non-zero, and `set -e` would abort the run before the first install.
version_of() {
  [ -f "$1/SKILL.md" ] || return 0
  awk '/^version:/ { sub(/^version:[ ]*/, ""); print; exit }' "$1/SKILL.md"
}

for s in "${SKILLS[@]}"; do
  [ -f "$SRC/$s/SKILL.md" ] || { echo "Not a skills repo: $SRC/$s/SKILL.md is missing" >&2; exit 1; }
done
REPO_VERSION="$(version_of "$SRC/log-time")"

if [ "$MODE" = check ]; then
  echo "repo      $REPO_VERSION   $REPO"
  echo "installed          $DEST_ROOT"
  rc=0
  for s in "${SKILLS[@]}"; do
    if [ -d "$DEST_ROOT/$s" ]; then
      have="$(version_of "$DEST_ROOT/$s")"
      if [ "$have" = "$REPO_VERSION" ]; then
        printf '  %-13s %-8s current\n' "$s" "${have:-unknown}"
      else
        printf '  %-13s %-8s OUT OF DATE (repo has %s)\n' "$s" "${have:-unknown}" "$REPO_VERSION"; rc=1
      fi
    else
      printf '  %-13s %-8s not installed\n' "$s" "-"; rc=1
    fi
  done
  [ $rc -eq 0 ] || echo $'\nRun ./install.sh to update.'
  exit $rc
fi

mkdir -p "$DEST_ROOT"
for s in "${SKILLS[@]}"; do
  dest="$DEST_ROOT/$s"
  had="$(version_of "$dest")"
  staging="$(mktemp -d "${TMPDIR:-/tmp}/kts.XXXXXX")"

  # Build the new folder beside the old one, then swap it in. Copying onto an
  # existing directory would nest it (dest/log-time) instead of replacing it.
  cp -R "$SRC/$s" "$staging/$s"
  # The profile is user data and never ships. It used to live inside the skill
  # folder; anything found there is moved to PROFILE_HOME rather than carried
  # along, so the next update has nothing left to clobber.
  rm -f "$staging/$s/profile.json"
  kept=""
  if [ -f "$dest/profile.json" ]; then
    mkdir -p "$(dirname "$PROFILE_HOME")"
    if [ -f "$PROFILE_HOME" ]; then
      kept=" (left an old profile.json behind in the skill folder; $PROFILE_HOME wins)"
      mv "$dest/profile.json" "$dest/profile.json.superseded"
    else
      mv "$dest/profile.json" "$PROFILE_HOME"
      kept=" (moved your profile to $PROFILE_HOME)"
    fi
  fi

  if [ -e "$dest" ]; then
    rm -rf "$dest.replacing"
    mv "$dest" "$dest.replacing"
    mv "$staging/$s" "$dest"
    rm -rf "$dest.replacing"
    printf '  updated   %-13s %s -> %s%s\n' "$s" "${had:-unknown}" "$REPO_VERSION" "$kept"
  else
    mv "$staging/$s" "$dest"
    printf '  installed %-13s %s\n' "$s" "$REPO_VERSION"
  fi
  rm -rf "$staging"
done

echo "  into      $DEST_ROOT"

# A same-named slash command shadows the skill, which is confusing rather than fatal.
# Claude Code only; Codex has no ~/.claude/commands.
if [ "$AGENT" = claude ]; then
commands_dirs="$HOME/.claude/commands"
sibling="$(dirname "$DEST_ROOT")/commands"
[ "$sibling" != "$commands_dirs" ] && commands_dirs="$commands_dirs
$sibling"
for s in "${SKILLS[@]}"; do
  while IFS= read -r d; do
    if [ -f "$d/$s.md" ]; then
      echo "  warning:  $d/$s.md will shadow the $s skill; move it aside"
    fi
  done <<< "$commands_dirs"
done
fi

if [ ! -f "$PROFILE_HOME" ]; then
  if [ "$AGENT" = codex ]; then run='$log-time'; else run='/log-time'; fi
  echo $'\nNo profile yet. Run '"$run"$' once and it will walk you through setup.'
else
  echo "  profile   $PROFILE_HOME (yours; updates never touch it)"
fi
