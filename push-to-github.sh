#!/usr/bin/env bash
set -euo pipefail

REMOTE_URL="https://github.com/sfeetudiant37-kayce/skulvi.git"
REPO_PATH="sfeetudiant37-kayce/skulvi"
BRANCH="main"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

for command in git gh; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "Erreur : installe d’abord $command, puis relance ce script." >&2
    exit 1
  fi
done

if ! gh auth status --hostname github.com >/dev/null 2>&1; then
  gh auth login --hostname github.com --git-protocol https --web
fi
gh auth setup-git

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  rm -rf .git
  git init --initial-branch="$BRANCH"
fi
git branch -M "$BRANCH"

current_remote="$(git remote get-url origin 2>/dev/null || true)"
if [[ -z "$current_remote" ]]; then
  git remote add origin "$REMOTE_URL"
elif [[ "$current_remote" != "$REMOTE_URL" ]]; then
  git remote set-url origin "$REMOTE_URL"
fi

if ! git config user.name >/dev/null; then
  read -r -p "Nom à afficher comme auteur du commit : " author_name
  git config user.name "$author_name"
fi
if ! git config user.email >/dev/null; then
  read -r -p "E-mail d’auteur Git (tu peux utiliser l’adresse noreply de GitHub) : " author_email
  git config user.email "$author_email"
fi

git add -A
if ! git rev-parse --verify HEAD >/dev/null 2>&1; then
  git commit -m "Initial commit: Talent Engine MVP"
elif ! git diff --cached --quiet; then
  git commit -m "Update Talent Engine MVP"
else
  echo "Aucun changement à committer."
fi

login="$(gh api user --jq '.login')"
push_allowed="$(gh api "repos/$REPO_PATH" --jq '.permissions.push // false' 2>/dev/null || echo false)"
if [[ "$push_allowed" != "true" ]]; then
  echo "Le compte GitHub '$login' n’a pas le droit d’écriture sur le dépôt cible." >&2
  exit 1
fi

git push --set-upstream origin "$BRANCH"
echo "Push terminé : $REMOTE_URL (branche $BRANCH), compte $login."
