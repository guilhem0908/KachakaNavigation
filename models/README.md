# Fichiers De Modèles

Ce dossier est réservé aux fichiers de modèles qui ne doivent pas vivre dans le
paquet Python.

```text
models/
└── nomad_original/
    ├── checkpoints/   # fichiers .ckpt, .pth, .pt
    ├── configs/       # configs YAML/JSON du modèle
    └── goals/         # images objectif ou assets de trajectoire
```

Le code Python des adaptateurs vit ici:

```text
src/kachaka_navigation/models/
```

Seuls les README et placeholders `.gitkeep` doivent être commités ici. Les
checkpoints, datasets et gros fichiers sont ignorés par `.gitignore`.
