#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
mkdir -p .git/hooks

cat > .git/hooks/pre-commit <<'HOOK'
#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "[pre-commit] running Jarvis validation..."

staged_files="$(git diff --cached --name-only | tr '\n' '|' | sed 's/|$//')"

python3 -m py_compile jarvis.py cli.py db.py executor.py files.py llm.py skills.py verifier.py

if [[ -n "$staged_files" ]]; then
  JARVIS_ALLOWED_DIRTY_PATH="$staged_files" bash tests/run_all.sh
else
  bash tests/run_all.sh
fi

echo "[pre-commit] validation passed"
HOOK

chmod +x .git/hooks/pre-commit

echo "Installed Jarvis pre-commit hook."
