# Assets NoMaD Original

Placer ici les fichiers NoMaD originaux quand ils sont disponibles.

Structure attendue:

```text
models/nomad_original/
├── checkpoints/
│   └── nomad.ckpt
├── configs/
│   └── nomad.yaml
└── goals/
    └── goal.jpg
```

Commande exemple:

```bash
python -m kachaka_navigation.scripts.run_ros2_trajectory_generator \
  --model nomad_original \
  --nomad-checkpoint models/nomad_original/checkpoints/nomad.ckpt \
  --nomad-config models/nomad_original/configs/nomad.yaml \
  --nomad-goal-image models/nomad_original/goals/goal.jpg
```

L'adaptateur actuel réserve le point d'intégration, mais ne charge pas encore le
checkpoint PyTorch du VisualNav Transformer.
