#!/usr/bin/env bash
#
# One-shot Linux bootstrap for driving the Kachaka with NoMaD.
# Run from inside the cloned repo:
#
#   ./scripts/linux_quickstart.sh
#
# It creates a venv, installs everything (project + ML deps), clones the NoMaD
# model code, downloads the checkpoint, prepares .env, and runs a self-test.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

PYBIN="${PYBIN:-python3}"

echo "[1/4] Creating virtualenv (.venv) with $PYBIN ..."
if [ ! -d .venv ]; then
  "$PYBIN" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip >/dev/null

echo "[2/4] Installing project + NoMaD model code + checkpoint ..."
PYTHON="$(command -v python)" ./scripts/setup_nomad.sh

echo "[3/4] Preparing .env ..."
if [ ! -f .env ]; then
  cp .env.example .env
  echo "    -> created .env (EDIT it and set KACHAKA_HOST to your robot's IP)."
else
  echo "    -> .env already exists (make sure KACHAKA_HOST is your robot's IP)."
fi

echo "[4/4] Self-test: running NoMaD on synthetic frames (no robot needed) ..."
python -m kachaka_navigation.scripts.run_nomad_kachaka_control --self-test || true

cat <<'NEXT'

============================================================
Setup done. Next steps (same terminal):

  source .venv/bin/activate

  # 1) set the robot IP
  #    edit .env  ->  KACHAKA_HOST=<robot ip>   (same Wi-Fi as this machine)

  # 2) dry-run (robot does NOT move)
  python -m kachaka_navigation.scripts.run_nomad_kachaka_control --dry-run --max-iterations 30

  # 3) drive for real (robot WILL move; keep area clear, Ctrl-C to stop)
  python -m kachaka_navigation.scripts.run_nomad_kachaka_control \
      --device auto --max-linear-speed 0.1 --max-angular-speed 0.3
============================================================
NEXT
