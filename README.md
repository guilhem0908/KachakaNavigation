# KachakaNavigation

KachakaNavigation est un projet de navigation visuelle pour tester plusieurs
modèles de navigation sur un robot Kachaka avec ROS2.

Le principe général:

```text
topic camera
  -> image_sender
  -> trajectory_generator avec modèle interchangeable
  -> command_sender
  -> command_executor Kachaka
```

Le modèle par défaut est `noop`: il ne déplace pas le robot et sert à vérifier
le câblage. L'adaptateur `nomad_original` intègre le NoMaD original de
`robodhruv/visualnav-transformer` et permet de piloter le Kachaka en natif sur
ce PC (voir [docs/nomad_kachaka.md](docs/nomad_kachaka.md)).

## Organisation

```text
KachakaNavigation/
├── src/kachaka_navigation/
│   ├── core/          # contrats input/output des modèles
│   ├── models/        # adaptateurs Python des modèles
│   ├── ros2/          # noeuds ROS2
│   ├── robot/         # exécution des commandes Kachaka
│   └── scripts/       # commandes lançables
├── models/            # checkpoints, configs, images objectif
├── docs/              # architecture et guides
├── tests/
├── Dockerfile.ros2
└── docker-compose.yml
```

Séparation importante:

- `src/kachaka_navigation/models/` contient le code Python des modèles.
- `models/` contient les fichiers lourds: checkpoints, configs, goal images.

## Installation

Installation locale:

```bash
cd ~/Desktop/KachakaNavigation
conda activate kachaka-nav
python -m pip install -e .
```

Outils de développement:

```bash
python -m pip install -e ".[dev]"
```

Environnement ROS2 reproductible:

```bash
docker compose build ros2
docker compose run --rm ros2
```

Voir [docs/ros2_docker.md](docs/ros2_docker.md).

## Configuration

Copier le fichier d'exemple:

```bash
cp .env.example .env
```

Configurer au minimum:

```text
KACHAKA_HOST=<adresse-ip-du-robot>
KACHAKA_PORT=26400
ROS2_CAMERA_INPUT_TOPIC=/camera/image_raw
ROS2_IMAGE_TOPIC=/kachaka_navigation/image
ROS2_TRAJECTORY_TOPIC=/kachaka_navigation/trajectory
ROS2_ROBOT_COMMAND_TOPIC=/kachaka_navigation/robot_command
ROS2_CMD_VEL_TOPIC=/kachaka/manual_control/cmd_vel
MAX_IMAGE_AGE_SECONDS=0.5
CMD_VEL_PUBLISH_RATE_HZ=20.0
VELOCITY_COMMAND_TIMEOUT_SECONDS=0.25
MAX_LINEAR_SPEED_MPS=0.2
MAX_ANGULAR_SPEED_RADPS=0.5
```

Vérifier l'API Kachaka:

```bash
python -m kachaka_navigation.scripts.check_api_connection
python -m kachaka_navigation.scripts.smoke_test_connection
```

## Où Mettre Les Modèles

Les fichiers des modèles vont dans `models/`.

Pour NoMaD (créés par `./scripts/setup_nomad.sh`):

```text
models/nomad_original/
├── checkpoints/
│   └── nomad.pth
├── configs/
│   └── nomad.yaml
└── goals/
    └── goal.jpg   # optionnel (mode objectif)
```

Les checkpoints et gros fichiers sont ignorés par Git. Il faut seulement
commiter les README et placeholders.

Voir [models/README.md](models/README.md).

## Contrat D'un Modèle

Chaque modèle reçoit un objet:

```python
ImageFrame
```

Champs principaux:

```text
data       bytes de l'image, souvent JPEG
encoding   jpeg, raw, png, ou format compressé
width      largeur optionnelle
height     hauteur optionnelle
frame_id   frame ROS si disponible
timestamp  timestamp image en secondes
metadata   topic source, temps de réception, infos additionnelles
```

Chaque modèle retourne:

```python
NavigationCommand
```

Types de commandes prévus:

```text
stop
noop
velocity
waypoint
move_to_location
return_home
dock_shelf
undock_shelf
cancel
speak
```

L'exécuteur Kachaka applique les commandes haut niveau via l'API Kachaka.
Les commandes `velocity` sont supportées via ROS2 `geometry_msgs/Twist` quand
`--enable-velocity-control` est activé. Les commandes `waypoint` restent à
câbler.

Guide complet: [docs/model_integration.md](docs/model_integration.md).

## Lancer Le Modèle Sûr

Commencer avec `noop`. Il valide le flux ROS2 sans bouger le robot.

Terminal 1, génération des trajectoires:

```bash
python -m kachaka_navigation.scripts.run_ros2_trajectory_generator --model noop
```

Terminal 2, envoi des commandes:

```bash
python -m kachaka_navigation.scripts.run_ros2_command_sender
```

Terminal 3, relais caméra:

```bash
python -m kachaka_navigation.scripts.run_ros2_image_sender \
  --input-image-topic /camera/image_raw \
  --output-image-topic /kachaka_navigation/image
```

Terminal 4, exécution Kachaka en dry-run:

```bash
python -m kachaka_navigation.scripts.run_ros2_kachaka_command_executor --dry-run
```

Vérifier que les images arrivent en temps réel:

```bash
ros2 topic hz /kachaka_navigation/image
ros2 topic echo /kachaka_navigation/robot_command
```

## Tester Une Commande Bas Niveau

Le modèle intégré `constant_velocity` produit une petite commande `velocity`.
Il sert à valider le chemin bas niveau avant NoMaD.

Générateur:

```bash
python -m kachaka_navigation.scripts.run_ros2_trajectory_generator \
  --model constant_velocity \
  --constant-linear-x 0.03 \
  --constant-angular-z 0.0 \
  --constant-duration 0.2
```

Exécuteur en dry-run:

```bash
python -m kachaka_navigation.scripts.run_ros2_kachaka_command_executor \
  --dry-run \
  --enable-velocity-control
```

Exécuteur avec publication `cmd_vel`, après vérification du topic Kachaka:

```bash
python -m kachaka_navigation.scripts.run_ros2_kachaka_command_executor \
  --enable-velocity-control \
  --disable-kachaka-api \
  --cmd-vel-topic /kachaka/manual_control/cmd_vel
```

Voir [docs/low_level_velocity.md](docs/low_level_velocity.md).

## Piloter Le Kachaka Avec NoMaD (Sur Ce PC, Sans ROS)

L'adaptateur `nomad_original` charge le vrai checkpoint NoMaD
(`robodhruv/visualnav-transformer`) et le branche sur le contrat
`ImageFrame -> NavigationCommand`. Sur ce Mac, on pilote le robot en natif via
`kachaka-api` (caméra avant -> NoMaD -> vitesse), **sans ROS**.

Installation (une fois):

```bash
conda activate kachaka-nav
./scripts/setup_nomad.sh
```

Dry-run (le robot ne bouge pas, on journalise seulement les vitesses):

```bash
python -m kachaka_navigation.scripts.run_nomad_kachaka_control \
  --dry-run --max-iterations 20
```

Pilotage réel (le robot bouge — dégager la zone, `Ctrl-C` pour arrêter):

```bash
python -m kachaka_navigation.scripts.run_nomad_kachaka_control \
  --max-linear-speed 0.1 --max-angular-speed 0.3 --frame-rate 3
```

Guide complet: [docs/nomad_kachaka.md](docs/nomad_kachaka.md).

### NoMaD via ROS2 (optionnel)

L'adaptateur fonctionne aussi avec le générateur de trajectoires ROS2:

```bash
python -m kachaka_navigation.scripts.run_ros2_trajectory_generator \
  --model nomad_original \
  --nomad-checkpoint models/nomad_original/checkpoints/nomad.pth \
  --nomad-config models/nomad_original/configs/nomad.yaml
```

## Ajouter Un Nouveau Modèle

1. Créer un adaptateur dans `src/kachaka_navigation/models/`.
2. Implémenter l'interface `NavigationModel`.

```python
class MyModel:
    name = "my_model"

    def reset(self) -> None:
        ...

    def predict(
        self,
        frame: ImageFrame,
        state: RobotState | None = None,
    ) -> NavigationCommand:
        ...
```

3. L'enregistrer dans `src/kachaka_navigation/models/registry.py`.
4. Placer les poids/configs dans `models/my_model/`.
5. Le lancer avec:

```bash
python -m kachaka_navigation.scripts.run_ros2_trajectory_generator --model my_model
```

Tutoriel détaillé: [docs/model_integration.md](docs/model_integration.md).

## Documentation

- [Piloter le Kachaka avec NoMaD](docs/nomad_kachaka.md)
- [Architecture ROS2](docs/navigation_architecture.md)
- [Guide d'intégration des modèles](docs/model_integration.md)
- [Commandes bas niveau cmd_vel](docs/low_level_velocity.md)
- [Docker ROS2](docs/ros2_docker.md)
- [Commandes directes Kachaka](docs/kachaka_api_commands.md)
