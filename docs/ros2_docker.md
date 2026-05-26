# Docker ROS2

Le Docker ROS2 sert à donner un environnement reproductible au superviseur.
Il installe ROS2 Humble, `rclpy`, `sensor_msgs`, `std_msgs`, `cv_bridge`,
OpenCV et le paquet Python en mode développement.

Construire l'image:

```bash
docker compose build ros2
```

Ouvrir un shell ROS2:

```bash
docker compose run --rm ros2
```

Dans le container, les commandes principales sont:

```bash
python -m kachaka_navigation.scripts.run_ros2_trajectory_generator --model noop
python -m kachaka_navigation.scripts.run_ros2_command_sender
python -m kachaka_navigation.scripts.run_ros2_image_sender
python -m kachaka_navigation.scripts.run_ros2_kachaka_command_executor --dry-run
```

Pour tester le chemin bas niveau `cmd_vel`, voir
[docs/low_level_velocity.md](low_level_velocity.md).

Sur Linux, `network_mode: host` simplifie la découverte ROS2. Sur macOS, Docker
Desktop isole davantage le réseau: il peut être nécessaire d'exécuter ROS2
directement sur la machine, ou d'utiliser une configuration réseau ROS2 dédiée.
