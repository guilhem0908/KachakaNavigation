#!/usr/bin/env bash
#
# Reproducible setup for running NoMaD on this machine.
#
#   - installs the ML dependencies
#   - clones robodhruv/visualnav-transformer into third_party/ (model code)
#   - vendors the 3 diffusion_policy modules NoMaD needs
#   - downloads the published NoMaD checkpoint (nomad.pth, ~73 MB)
#   - copies the upstream nomad.yaml config next to the checkpoint
#
# Usage:
#   conda activate kachaka-nav
#   ./scripts/setup_nomad.sh
#
# Override the interpreter with PYTHON, e.g. `PYTHON=python3.10 ./scripts/setup_nomad.sh`.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

# Pick an interpreter: $PYTHON, else python, else python3 (Linux often lacks `python`).
if [ -z "${PYTHON:-}" ]; then
  if command -v python >/dev/null 2>&1; then
    PYTHON=python
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON=python3
  else
    echo "ERROR: no python interpreter found. Set PYTHON=/path/to/python and re-run." >&2
    exit 1
  fi
fi
NOMAD_DRIVE_ID="1YJhkkMJAYOiKNyCaelbS_alpUpAJsOUb"
VNT_DIR="third_party/visualnav-transformer"
DP_DIR="third_party/diffusion_policy/diffusion_policy/model/diffusion"

echo "[1/5] Installing project + ML dependencies into: $($PYTHON -c 'import sys; print(sys.prefix)')"
# Installs the project plus the 'nomad' extra (torch, diffusers, efficientnet, ...).
# On Linux with an NVIDIA GPU, pip pulls a CUDA-enabled torch wheel automatically.
$PYTHON -m pip install -e ".[nomad]"

echo "[2/5] Cloning visualnav-transformer (model code)..."
mkdir -p third_party
if [ ! -d "$VNT_DIR" ]; then
  git clone --depth 1 https://github.com/robodhruv/visualnav-transformer.git "$VNT_DIR"
else
  echo "      already present, skipping."
fi

echo "[3/5] Vendoring diffusion_policy modules..."
mkdir -p "$DP_DIR"
touch third_party/diffusion_policy/diffusion_policy/__init__.py \
      third_party/diffusion_policy/diffusion_policy/model/__init__.py \
      "$DP_DIR/__init__.py"
DP_BASE="https://raw.githubusercontent.com/real-stanford/diffusion_policy/main/diffusion_policy/model/diffusion"
for f in conditional_unet1d.py conv1d_components.py positional_embedding.py; do
  curl -fsSL "$DP_BASE/$f" -o "$DP_DIR/$f"
done

echo "[4/5] Downloading NoMaD checkpoint (~73 MB)..."
mkdir -p models/nomad_original/checkpoints models/nomad_original/configs
if [ ! -f models/nomad_original/checkpoints/nomad.pth ]; then
  $PYTHON -m gdown "$NOMAD_DRIVE_ID" -O models/nomad_original/checkpoints/nomad.pth
else
  echo "      checkpoint already present, skipping."
fi

echo "[5/5] Copying NoMaD config..."
cp -f "$VNT_DIR/train/config/nomad.yaml" models/nomad_original/configs/nomad.yaml

echo
echo "Setup complete. Smoke-test without moving the robot:"
echo "  $PYTHON -m kachaka_navigation.scripts.run_nomad_kachaka_control --dry-run --max-iterations 10"
echo
echo "Then drive for real (robot WILL move; keep the area clear):"
echo "  $PYTHON -m kachaka_navigation.scripts.run_nomad_kachaka_control --max-linear-speed 0.1 --max-angular-speed 0.3"
