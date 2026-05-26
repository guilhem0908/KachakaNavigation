# Commandes Bas Niveau `cmd_vel`

Le projet supporte maintenant les commandes bas niveau de type:

```python
NavigationCommand.from_velocity(
    linear_x=0.05,
    angular_z=0.0,
    duration_seconds=0.2,
)
```

Ces commandes sont converties en messages ROS2:

```text
geometry_msgs/msg/Twist
```

sur le topic configuré par:

```text
ROS2_CMD_VEL_TOPIC=/kachaka/manual_control/cmd_vel
```

Le nom exact du topic Kachaka doit être vérifié dans l'environnement ROS2 réel:

```bash
ros2 topic list | grep cmd_vel
ros2 topic info /kachaka/manual_control/cmd_vel
```

## Vitesse Base Mobile, Pas Roues Directes

Le contrat actuel commande la base mobile:

```text
linear.x   vitesse avant/arrière en m/s
angular.z  vitesse de rotation en rad/s
```

Le contrôleur du robot convertit ensuite ces valeurs en vitesses de roues. Si
Kachaka expose une interface roue gauche/droite plus basse que `cmd_vel`, il
faudra ajouter un exécuteur séparé.

## Sécurité

Le noeud Kachaka n'envoie pas de `cmd_vel` par défaut. Il faut activer
explicitement:

```bash
python -m kachaka_navigation.scripts.run_ros2_kachaka_command_executor \
  --enable-velocity-control
```

Options de sécurité:

```text
--max-linear-speed       limite abs(linear.x), défaut 0.2 m/s
--max-angular-speed      limite abs(angular.z), défaut 0.5 rad/s
--velocity-timeout       durée par défaut si le modèle n'en donne pas
--max-velocity-duration  durée maximale acceptée
--cmd-vel-publish-rate   fréquence de publication du Twist
```

Le noeud republie la vitesse active à fréquence fixe. Si aucune nouvelle
commande n'arrive avant le timeout, il publie automatiquement un Twist nul.

## Test En Dry-Run

Lancer le modèle de test:

```bash
python -m kachaka_navigation.scripts.run_ros2_trajectory_generator \
  --model constant_velocity \
  --constant-linear-x 0.03 \
  --constant-angular-z 0.0 \
  --constant-duration 0.2
```

Lancer le sender:

```bash
python -m kachaka_navigation.scripts.run_ros2_command_sender
```

Lancer l'exécuteur en dry-run:

```bash
python -m kachaka_navigation.scripts.run_ros2_kachaka_command_executor \
  --dry-run \
  --enable-velocity-control
```

Observer les commandes:

```bash
ros2 topic echo /kachaka_navigation/robot_command
```

## Test Avec Publication `cmd_vel`

Quand le topic `cmd_vel` Kachaka est confirmé:

```bash
python -m kachaka_navigation.scripts.run_ros2_kachaka_command_executor \
  --enable-velocity-control \
  --disable-kachaka-api \
  --cmd-vel-topic /kachaka/manual_control/cmd_vel \
  --max-linear-speed 0.1 \
  --max-angular-speed 0.3
```

`--disable-kachaka-api` permet d'utiliser seulement le pont ROS2 `cmd_vel`, sans
appeler les commandes haut niveau de l'API Python Kachaka.
