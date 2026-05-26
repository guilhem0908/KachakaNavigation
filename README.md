# KachakaNavigation - commandes terminal

## Initialisation

Ouvre le dossier du projet.

```bash
cd ~/Desktop/KachakaNavigation
```

Active l'environnement Python.

```bash
conda activate kachaka-nav
```

Installe le projet en mode développement.

```bash
python -m pip install -e .
```

---

## Vérifications

Vérifie rapidement que le port API de Kachaka est joignable.

```bash
python -m kachaka_navigation.scripts.check_api_connection
```

Teste la connexion API.

```bash
python -m kachaka_navigation.scripts.smoke_test_connection
```

Liste les zones connues.

```bash
python -m kachaka_navigation.scripts.list_locations
```

Liste les étagères connues.

```bash
python -m kachaka_navigation.scripts.list_shelves
```

---

## Architecture navigation visuelle

L'architecture ROS2 et client-serveur est décrite dans
[docs/navigation_architecture.md](docs/navigation_architecture.md).

Le principe recommandé pour Kachaka:

```text
camera -> image_sender -> trajectory_generator -> command_sender -> command_executor
```

Côté serveur, lancer le noeud qui génère les trajectoires.

```bash
python -m kachaka_navigation.scripts.run_ros2_trajectory_generator --model noop
```

Côté serveur, lancer le noeud qui envoie les commandes vers Kachaka.

```bash
python -m kachaka_navigation.scripts.run_ros2_command_sender
```

Côté caméra/Kachaka, relayer une caméra quelconque vers le topic attendu.

```bash
python -m kachaka_navigation.scripts.run_ros2_image_sender \
  --input-image-topic /camera/image_raw \
  --output-image-topic /kachaka_navigation/image
```

Côté Kachaka, exécuter les commandes. Commencer en dry-run.

```bash
python -m kachaka_navigation.scripts.run_ros2_kachaka_command_executor --dry-run
```

Pour un environnement ROS2 reproductible, voir
[docs/ros2_docker.md](docs/ros2_docker.md).

---

## Zones connues

```text
home      = dock de charge
S01_home  = zone de la grande étagère
S02_home  = zone de la petite étagère
L02       = zone de dépôt commune / 受付
```

Coordonnées de `L02` :

```text
x     = 5.6937123263245724
y     = 0.79818810199356616
theta = 1.6002418814260775
```

---

## Étagères connues

```text
S01 = grande étagère / シェルフ / home_location_id S01_home
S02 = petite étagère / 本棚 / home_location_id S02_home
```

---

## Aller à une zone

Retourne au dock de charge.

```bash
python -m kachaka_navigation.scripts.return_home
```

Va au dock de charge.

```bash
python -m kachaka_navigation.scripts.move_to_location home
```

Va à la zone de la grande étagère.

```bash
python -m kachaka_navigation.scripts.move_to_location S01_home
```

Va à la zone de la petite étagère.

```bash
python -m kachaka_navigation.scripts.move_to_location S02_home
```

Va à la zone de dépôt commune.

```bash
python -m kachaka_navigation.scripts.move_to_location L02
```

---

## Charger / prendre une étagère dans une zone

Va à `home` et prend l'étagère devant le robot.

```bash
python -m kachaka_navigation.scripts.dock_any_shelf_at_home
```

Équivalent avec la commande générique.

```bash
python -m kachaka_navigation.scripts.dock_any_shelf_at_location home
```

Va à `S01_home` et prend l'étagère devant le robot.

```bash
python -m kachaka_navigation.scripts.dock_any_shelf_at_location S01_home
```

Va à `S02_home` et prend l'étagère devant le robot.

```bash
python -m kachaka_navigation.scripts.dock_any_shelf_at_location S02_home
```

Va à `L02` et prend l'étagère devant le robot.

```bash
python -m kachaka_navigation.scripts.dock_any_shelf_at_location L02
```

---

## Décharger / déposer une étagère dans une zone

Va à `home` et dépose l'étagère transportée.

```bash
python -m kachaka_navigation.scripts.undock_shelf_at_home
```

Équivalent avec la commande générique.

```bash
python -m kachaka_navigation.scripts.undock_shelf_at_location home
```

Va à `S01_home` et dépose l'étagère transportée.

```bash
python -m kachaka_navigation.scripts.undock_shelf_at_location S01_home
```

Va à `S02_home` et dépose l'étagère transportée.

```bash
python -m kachaka_navigation.scripts.undock_shelf_at_location S02_home
```

Va à `L02` et dépose l'étagère transportée.

```bash
python -m kachaka_navigation.scripts.undock_shelf_at_location L02
```

---

## Charger / décharger à la position actuelle

Prend l'étagère située devant le robot.

```bash
python -m kachaka_navigation.scripts.dock_shelf
```

Dépose l'étagère à la position actuelle.

```bash
python -m kachaka_navigation.scripts.undock_shelf
```

---

## Déplacer automatiquement une étagère vers une zone

Déplace la grande étagère `S01` vers `home`, puis la dépose.

```bash
python -m kachaka_navigation.scripts.move_shelf S01 home
```

Déplace la grande étagère `S01` vers `S01_home`, puis la dépose.

```bash
python -m kachaka_navigation.scripts.move_shelf S01 S01_home
```

Déplace la grande étagère `S01` vers `S02_home`, puis la dépose.

```bash
python -m kachaka_navigation.scripts.move_shelf S01 S02_home
```

Déplace la grande étagère `S01` vers `L02`, puis la dépose.

```bash
python -m kachaka_navigation.scripts.move_shelf S01 L02
```

Déplace la petite étagère `S02` vers `home`, puis la dépose.

```bash
python -m kachaka_navigation.scripts.move_shelf S02 home
```

Déplace la petite étagère `S02` vers `S01_home`, puis la dépose.

```bash
python -m kachaka_navigation.scripts.move_shelf S02 S01_home
```

Déplace la petite étagère `S02` vers `S02_home`, puis la dépose.

```bash
python -m kachaka_navigation.scripts.move_shelf S02 S02_home
```

Déplace la petite étagère `S02` vers `L02`, puis la dépose.

```bash
python -m kachaka_navigation.scripts.move_shelf S02 L02
```

---

## Ramener une étagère à sa zone enregistrée

Ramène la grande étagère `S01` à sa position enregistrée.

```bash
python -m kachaka_navigation.scripts.return_shelf S01
```

Ramène la petite étagère `S02` à sa position enregistrée.

```bash
python -m kachaka_navigation.scripts.return_shelf S02
```

---

## Stop

Annule la commande en cours.

```bash
python -m kachaka_navigation.scripts.cancel_command
```
