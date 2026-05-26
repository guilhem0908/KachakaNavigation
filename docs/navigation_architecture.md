# Architecture navigation visuelle

Cette architecture sépare clairement quatre responsabilités.

1. Le robot produit des images et applique des commandes.
2. Le serveur génère des trajectoires avec un modèle interchangeable.
3. Le serveur valide/convertit ces trajectoires et envoie des commandes.
4. Le robot applique les commandes Kachaka.

Le dépôt de référence est `robodhruv/visualnav-transformer`:
https://github.com/robodhruv/visualnav-transformer

## Flux ROS2 demandé

Topologie recommandée pour Kachaka:

```text
camera quelconque
    -> /camera/image_raw ou /camera/image/compressed
    -> kachaka_image_sender
    -> /kachaka_navigation/image

serveur:
    /kachaka_navigation/image
    -> kachaka_trajectory_generator
    -> /kachaka_navigation/trajectory
    -> kachaka_command_sender
    -> /kachaka_navigation/robot_command

Kachaka:
    /kachaka_navigation/robot_command
    -> kachaka_command_executor
    -> Kachaka API
```

Les deux noeuds serveur sont donc:

- `kachaka_trajectory_generator`: lit les images en temps réel et produit une
  trajectoire ou commande de navigation.
- `kachaka_command_sender`: vérifie que la trajectoire est encore récente,
  prépare la commande robot et la publie vers Kachaka.

Côté Kachaka/caméra:

- `kachaka_image_sender`: relaie un topic image configurable vers le topic
  attendu par le serveur. Il peut être lancé sur Kachaka, sur un PC caméra, ou
  ignoré si une autre source publie déjà sur `/kachaka_navigation/image`.
- `kachaka_command_executor`: consomme les commandes et appelle l'API Kachaka.

Cette séparation permet de changer la caméra sans changer le modèle. La caméra
peut être celle de Kachaka, une webcam USB, un téléphone, un simulateur, ou un
autre noeud ROS2, tant qu'elle publie un `sensor_msgs/Image` ou
`sensor_msgs/CompressedImage`.

## Temps réel image

Les noeuds image utilisent une QoS capteur avec profondeur 1: le système garde
la frame la plus récente plutôt que d'accumuler une file d'images anciennes.

`kachaka_trajectory_generator` vérifie aussi l'âge des images avant d'appeler le
modèle. Par défaut, une image plus vieille que `0.5` seconde est rejetée et le
noeud publie une commande `stop`.

Variables utiles:

```text
ROS2_CAMERA_INPUT_TOPIC=/camera/image_raw
ROS2_IMAGE_TOPIC=/kachaka_navigation/image
ROS2_IMAGE_TYPE=raw
ROS2_TRAJECTORY_TOPIC=/kachaka_navigation/trajectory
ROS2_ROBOT_COMMAND_TOPIC=/kachaka_navigation/robot_command
MAX_IMAGE_AGE_SECONDS=0.5
```

## Flux TCP hors ROS

```text
Kachaka / ROS camera topic
    -> Ros1ImageTopicSource
    -> RobotNavigationClient
    -> NavigationTcpClient
    -> NavigationTcpServer
    -> NavigationService
    -> NavigationModel
    -> NavigationCommand
    -> KachakaCommandExecutor
    -> Kachaka API
```

Le robot peut donc rester léger: il publie les images vers le serveur et
exécute seulement les commandes retournées. Le serveur peut tourner sur une
machine plus puissante avec PyTorch, les checkpoints NoMaD et les futurs
modèles.

## Flux ROS1 legacy

Quand le serveur est sur le même graphe ROS que la caméra, le script
`run_ros_navigation_server` lit directement un topic `sensor_msgs/Image` et
publie des commandes JSON sur `/kachaka_navigation/command`.

```text
/usb_cam/image_raw
    -> Ros1ImageTopicSource
    -> NavigationService
    -> NavigationModel
    -> Ros1JsonCommandPublisher
    -> /kachaka_navigation/command
```

Ce mode reste utile pour reproduire progressivement le déploiement ROS1 du
VisualNav Transformer original. Pour Kachaka, la trajectoire principale du
projet doit viser ROS2.

## Contrats stables

Les fichiers sous `kachaka_navigation/core` sont le noyau de l'architecture:

- `ImageFrame`: image compressée, métadonnées ROS, timestamp et frame id.
- `RobotState`: état facultatif du robot, utile pour les futurs modèles.
- `NavigationCommand`: commande générique renvoyée par un modèle.
- `NavigationModel`: interface commune pour NoMaD et les modèles futurs.
- `CommandExecutor`: interface robot qui applique les commandes.

Les modèles ne doivent pas appeler directement l'API Kachaka. Ils renvoient
uniquement un `NavigationCommand`. C'est ce qui permet de remplacer NoMaD par
un autre modèle sans réécrire le client robot.

## NoMaD original

`NomadOriginalModel` est volontairement un adaptateur fin. Il garde déjà une
queue de contexte d'images, comme le déploiement VisualNav, mais la partie
PyTorch/checkpoint n'est pas encore câblée.

Prochaine étape d'intégration:

1. Cloner ou vendoriser `robodhruv/visualnav-transformer`.
2. Charger la configuration NoMaD et le checkpoint dans
   `NomadOriginalModel`.
3. Convertir l'image JPEG en tenseur avec le preprocessing original.
4. Convertir le waypoint prédit en `NavigationCommand.from_waypoint(...)`.
5. Ajouter un exécuteur Kachaka capable d'appliquer un waypoint ou une vitesse.

Pour l'instant, `KachakaCommandExecutor` applique les commandes haut niveau
déjà disponibles dans `KachakaRobotClient`. Les commandes `velocity` et
`waypoint` lèvent une erreur explicite tant que le pont `cmd_vel` ou waypoint
Kachaka n'est pas ajouté.

## Commandes utiles

Serveur ROS2, noeud qui génère les trajectoires:

```bash
python -m kachaka_navigation.scripts.run_ros2_trajectory_generator --model noop
```

Serveur ROS2, noeud qui envoie les commandes vers Kachaka:

```bash
python -m kachaka_navigation.scripts.run_ros2_command_sender
```

Noeud caméra/Kachaka qui relaie un topic image configurable:

```bash
python -m kachaka_navigation.scripts.run_ros2_image_sender \
  --input-image-topic /camera/image_raw \
  --output-image-topic /kachaka_navigation/image
```

Noeud Kachaka qui exécute les commandes, en mode dry-run au début:

```bash
python -m kachaka_navigation.scripts.run_ros2_kachaka_command_executor --dry-run
```

Serveur modèle TCP, sans modèle actif:

```bash
python -m kachaka_navigation.scripts.run_navigation_server --model noop
```

Client robot qui lit `/usb_cam/image_raw` et affiche les commandes sans toucher
au robot:

```bash
python -m kachaka_navigation.scripts.run_robot_navigation_client --dry-run
```

Serveur ROS local qui publie les commandes sur `/kachaka_navigation/command`:

```bash
python -m kachaka_navigation.scripts.run_ros_navigation_server --model noop
```

Préparation NoMaD, quand le checkpoint est disponible:

```bash
python -m kachaka_navigation.scripts.run_navigation_server \
  --model nomad_original \
  --nomad-checkpoint /path/to/nomad.ckpt \
  --nomad-config /path/to/model.yaml \
  --nomad-goal-image /path/to/goal.jpg
```
