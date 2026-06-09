# Assets NoMaD Original

Ces fichiers sont récupérés automatiquement par `./scripts/setup_nomad.sh`
(ignorés par Git, sauf ce README et les `.gitkeep`).

Structure attendue:

```text
models/nomad_original/
├── checkpoints/
│   └── nomad.pth      # checkpoint publié (~73 Mo, Google Drive)
├── configs/
│   └── nomad.yaml     # config d'entraînement (copiée depuis le repo upstream)
└── goals/
    └── goal.jpg       # optionnel: image objectif (mode goal-conditioned)
```

L'adaptateur `nomad_original` charge ce checkpoint, exécute l'encodeur vision +
l'échantillonnage par diffusion, puis convertit le waypoint prédit en commande
`velocity` (contrôleur PD).

## Pilotage direct sur ce PC (sans ROS)

```bash
# 1) installation (une fois)
./scripts/setup_nomad.sh

# 2) dry-run, le robot ne bouge pas
python -m kachaka_navigation.scripts.run_nomad_kachaka_control --dry-run --max-iterations 20

# 3) pilotage réel (le robot bouge)
python -m kachaka_navigation.scripts.run_nomad_kachaka_control \
  --max-linear-speed 0.1 --max-angular-speed 0.3 --frame-rate 3
```

Guide complet: [docs/nomad_kachaka.md](../../docs/nomad_kachaka.md).

## Provenance

- Code modèle: [robodhruv/visualnav-transformer](https://github.com/robodhruv/visualnav-transformer) (MIT).
- Bloc de diffusion `ConditionalUnet1D`: [real-stanford/diffusion_policy](https://github.com/real-stanford/diffusion_policy) (MIT).
- Checkpoint NoMaD: poids publiés par les auteurs (voir le repo upstream).
