# Guide D'Intégration Des Modèles

Ce guide explique comment relier un modèle de navigation au reste du projet.

## Séparation Code / Assets

Le code Python d'un modèle va ici:

```text
src/kachaka_navigation/models/
```

Les fichiers lourds vont ici:

```text
models/
```

Exemple:

```text
models/my_model/
├── checkpoints/
│   └── model.ckpt
├── configs/
│   └── model.yaml
└── goals/
    └── goal.jpg
```

Les checkpoints sont ignorés par Git. Le dépôt doit contenir la structure et la
documentation, pas les poids lourds.

## Flux ROS2

```text
camera
  -> kachaka_image_sender
  -> /kachaka_navigation/image
  -> kachaka_trajectory_generator
  -> /kachaka_navigation/trajectory
  -> kachaka_command_sender
  -> /kachaka_navigation/robot_command
  -> kachaka_command_executor
  -> Kachaka API
```

Le modèle est appelé uniquement par `kachaka_trajectory_generator`.

## Input Modèle

Un modèle reçoit:

```python
ImageFrame
```

Définition simplifiée:

```python
@dataclass(frozen=True, slots=True)
class ImageFrame:
    data: bytes
    encoding: str
    width: int | None = None
    height: int | None = None
    frame_id: str = ""
    timestamp: float | None = None
    metadata: dict[str, str | int | float | bool | None] = field(default_factory=dict)
```

Sources possibles:

```text
sensor_msgs/Image           -> converti en JPEG par le noeud ROS2
sensor_msgs/CompressedImage -> envoyé tel quel au modèle
camera non ROS              -> possible via un autre ImageSource plus tard
```

Champs importants:

```text
data       image en bytes
encoding   "jpeg", "png", "rgb8", "bgr8", ou format compressé
timestamp  utilisé pour vérifier que l'image est récente
metadata   contient notamment source_topic et received_at
```

Le modèle ne doit pas lire directement un topic ROS. Il reçoit déjà une image
normalisée par le noeud d'entrée.

## Output Modèle

Un modèle retourne:

```python
NavigationCommand
```

Exemples:

```python
NavigationCommand.stop("No target")
NavigationCommand.from_waypoint(x=1.0, y=0.2, heading=0.0)
NavigationCommand.from_velocity(linear_x=0.1, angular_z=0.0)
```

Types disponibles:

```text
noop              ne fait rien
stop              stop/cancel côté robot
velocity          vitesse linéaire/angulaire
waypoint          waypoint local
move_to_location  commande Kachaka haut niveau
return_home       retour dock
dock_shelf        prise étagère
undock_shelf      dépôt étagère
cancel            annule la commande courante
speak             fait parler Kachaka
```

Règle importante: un modèle ne doit pas appeler directement l'API Kachaka. Il
doit seulement retourner un `NavigationCommand`.

`velocity` est exécuté via ROS2 `geometry_msgs/Twist` quand
`kachaka_command_executor` est lancé avec `--enable-velocity-control`.
`waypoint` reste réservé pour une future intégration.

Guide bas niveau: [docs/low_level_velocity.md](low_level_velocity.md).

## Ajouter Un Modèle

Créer un fichier:

```text
src/kachaka_navigation/models/my_model.py
```

Exemple minimal:

```python
from kachaka_navigation.core.messages import (
    ImageFrame,
    NavigationCommand,
    RobotState,
)


class MyNavigationModel:
    name = "my_model"

    def reset(self) -> None:
        return None

    def predict(
        self,
        frame: ImageFrame,
        state: RobotState | None = None,
    ) -> NavigationCommand:
        return NavigationCommand.stop("Model not implemented yet.")
```

Enregistrer le modèle dans:

```text
src/kachaka_navigation/models/registry.py
```

Ajouter:

```python
from kachaka_navigation.models.my_model import MyNavigationModel

registry.register(MyNavigationModel.name, MyNavigationModel)
```

Lancer:

```bash
python -m kachaka_navigation.scripts.run_ros2_trajectory_generator --model my_model
```

## Ajouter Des Arguments CLI

Si le modèle a besoin d'un checkpoint ou d'un fichier config, créer une
dataclass de configuration dans l'adaptateur:

```python
@dataclass(frozen=True, slots=True)
class MyModelConfig:
    checkpoint_path: Path
    config_path: Path | None = None
    device: str = "cpu"
```

Puis ajouter les arguments dans:

```text
src/kachaka_navigation/scripts/model_cli.py
```

## NoMaD Original

NoMaD doit suivre le même contrat:

```text
ImageFrame -> NomadOriginalModel.predict(...) -> NavigationCommand
```

Assets attendus:

```text
models/nomad_original/checkpoints/nomad.ckpt
models/nomad_original/configs/nomad.yaml
models/nomad_original/goals/goal.jpg
```

Commande:

```bash
python -m kachaka_navigation.scripts.run_ros2_trajectory_generator \
  --model nomad_original \
  --nomad-checkpoint models/nomad_original/checkpoints/nomad.ckpt \
  --nomad-config models/nomad_original/configs/nomad.yaml \
  --nomad-goal-image models/nomad_original/goals/goal.jpg
```

À câbler ensuite:

1. Charger le repo ou package VisualNav Transformer.
2. Charger la config et le checkpoint NoMaD.
3. Appliquer le preprocessing image original.
4. Convertir la sortie modèle en waypoint ou vitesse.
5. Pour `velocity`, utiliser l'exécuteur `cmd_vel` déjà disponible.
6. Pour `waypoint`, ajouter un pont Kachaka/ROS2 dédié.

## Modèle De Test `constant_velocity`

Le modèle `constant_velocity` permet de tester le chemin bas niveau:

```bash
python -m kachaka_navigation.scripts.run_ros2_trajectory_generator \
  --model constant_velocity \
  --constant-linear-x 0.03 \
  --constant-angular-z 0.0 \
  --constant-duration 0.2
```

Il retourne:

```python
NavigationCommand.from_velocity(...)
```

Il doit d'abord être testé avec l'exécuteur en `--dry-run`.

## Temps Réel

Le noeud `kachaka_trajectory_generator` rejette les images trop anciennes.

Paramètre:

```text
MAX_IMAGE_AGE_SECONDS=0.5
```

Vérifier le flux:

```bash
ros2 topic hz /kachaka_navigation/image
ros2 topic echo /kachaka_navigation/trajectory
ros2 topic echo /kachaka_navigation/robot_command
```
