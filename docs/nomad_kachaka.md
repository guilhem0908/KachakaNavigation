# Piloter Le Kachaka Avec NoMaD (Sur Ce PC, Sans ROS)

Ce guide explique comment piloter un Kachaka directement depuis cette machine
avec la politique **NoMaD** (`robodhruv/visualnav-transformer`). Tout tourne en
natif via `kachaka-api` (gRPC) : pas besoin de ROS.

## Flux

```text
caméra avant Kachaka  (get_front_camera_ros_compressed_image, JPEG)
  -> ImageFrame
  -> NomadOriginalModel.predict()
       décodage -> file de contexte -> encodeur vision NoMaD
       -> échantillonnage diffusion (DDPMScheduler)
       -> get_action (waypoints) -> contrôleur PD
  -> NavigationCommand.from_velocity(linear_x, angular_z)
  -> clamp sécurité (VelocityLimits)
  -> set_robot_velocity(linear, angular)
```

La boucle est implémentée par `NomadKachakaController`
(`src/kachaka_navigation/robot/nomad_controller.py`) et lancée par le script
`run_nomad_kachaka_control.py`.

## Sur Linux (GPU, sans VPN)

Le code est multiplateforme (Python pur + torch + kachaka-api en gRPC). Sur
Linux, tout-en-un :

```bash
git clone -b nomad-integration https://github.com/guilhem0908/KachakaNavigation.git
cd KachakaNavigation
./scripts/linux_quickstart.sh    # venv + deps + checkpoint + self-test
```

Ou étape par étape :

```bash
python3 -m venv .venv && source .venv/bin/activate   # ou conda
PYTHON=python ./scripts/setup_nomad.sh               # installe tout + checkpoint
cp .env.example .env                                 # mettre KACHAKA_HOST = IP du robot
python -m kachaka_navigation.scripts.run_nomad_kachaka_control --self-test
```

- **GPU** : `--device auto` (le défaut) prend automatiquement CUDA si une carte
  NVIDIA est présente — bien plus rapide que le CPU. Forcer avec `--device cuda`
  ou `--device cpu`.
- **Réseau** : mets la machine Linux **sur le même WiFi que le Kachaka** (pas de
  VPN full-tunnel qui capte le réseau local), puis renseigne son IP dans `.env`.
- **ROS2** (optionnel) : disponible nativement sur Linux si tu veux aussi le
  pipeline ROS2 du projet.

## Prérequis

- Environnement conda `kachaka-nav` (Python 3.10).
- Un fichier `.env` avec au moins :

```text
KACHAKA_HOST=<ip-du-robot>
KACHAKA_PORT=26400
```

- Le robot et le Mac sur le même réseau.

## Installation (une seule fois)

```bash
conda activate kachaka-nav
./scripts/setup_nomad.sh
```

Le script :

1. installe le projet + l'extra `nomad` (`pip install -e ".[nomad]"` : torch,
   diffusers, efficientnet, einops, gdown…) ;
2. clone `visualnav-transformer` dans `third_party/` (code du modèle) ;
3. vendorise les 3 modules `diffusion_policy` nécessaires ;
4. télécharge le checkpoint `nomad.pth` (~73 Mo) dans
   `models/nomad_original/checkpoints/` ;
5. copie la config `nomad.yaml` dans `models/nomad_original/configs/`.

`third_party/` et les poids sont ignorés par Git ; le script les recrée.

## Étape 0 — Self-test (sans robot)

Vérifier que NoMaD tourne sur ce PC, sans se connecter au robot (images
synthétiques) :

```bash
python -m kachaka_navigation.scripts.run_nomad_kachaka_control --self-test
```

On doit voir `SELF-TEST OK: NoMaD produced velocity commands on this machine.`

## Étape 1 — Dry-run (le robot NE bouge PAS)

Toujours commencer par un dry-run. Il se connecte au robot, récupère la caméra,
exécute NoMaD, et **journalise** les vitesses sans les envoyer :

```bash
python -m kachaka_navigation.scripts.run_nomad_kachaka_control \
  --dry-run --max-iterations 20
```

On doit voir d'abord quelques itérations à vitesse nulle (remplissage du
contexte de 4 images), puis des commandes `linear/angular` non nulles.

## Étape 2 — Pilotage réel (le robot BOUGE)

> ⚠️ Le robot se déplace. Dégager la zone, garder une main sur l'arrêt
> d'urgence, commencer à vitesse basse. `Ctrl-C` arrête proprement (vitesse
> nulle + désactivation du contrôle manuel).

```bash
python -m kachaka_navigation.scripts.run_nomad_kachaka_control \
  --max-linear-speed 0.1 \
  --max-angular-speed 0.3 \
  --frame-rate 3
```

Le script active le contrôle manuel du Kachaka
(`set_manual_control_enabled(True)`) avant d'envoyer des vitesses, et le
désactive à la sortie.

## Modes : exploration vs objectif

- **Exploration (défaut)** : pas d'image objectif, le masque ignore le but, le
  modèle explore librement.
- **Objectif** : fournir une image cible :

```bash
python -m kachaka_navigation.scripts.run_nomad_kachaka_control \
  --goal-image models/nomad_original/goals/goal.jpg
```

### Détection d'arrivée (mode objectif)

En mode objectif, la **tête de distance** de NoMaD (`dist_pred_net`) estime à
chaque pas une distance temporelle au but. Quand elle passe sous
`--goal-reached-distance` (défaut 3.0) pendant `--goal-reached-patience`
lectures consécutives (défaut 2), le robot **s'arrête** et exécute l'action
choisie :

```text
--on-goal-reached stop          s'arrête (défaut)
--on-goal-reached speak         s'arrête + annonce (--goal-reached-text)
--on-goal-reached return_home   s'arrête + retourne à la base
```

Réglage du seuil : observer `goal_distance=` dans les logs en plaçant le robot
sur l'objectif. La distance est en « pas de modèle » (pas en mètres) et peut
être biaisée vers le haut par l'écart caméra Kachaka/données d'entraînement —
si le robot ne s'arrête jamais, monter le seuil à 4-6.

**Si la distance est inutilisable** (valeur quasi identique sur la cible et en
approche, ex. ~15 partout — cas observé sur le Kachaka) : utiliser
`--arrival-detector similarity`. Ce détecteur compare directement l'image
courante à la photo-goal (similarité cosinus, 1.0 = vue identique) et ignore
la tête de distance.

Par défaut le seuil **s'auto-calibre depuis la position de départ** : les
premières lectures (`--goal-similarity-baseline-frames`, défaut 5) forment une
base B (à quel point la vue de départ ressemble déjà à la photo), et le seuil
devient `B + marge × (1 − B)` (`--goal-similarity-margin`, défaut 0.5). Le
déclenchement s'adapte donc au point de départ, sans réglage manuel. Un seuil
fixe reste possible via `--goal-similarity-threshold`. `--arrival-detector
any` combine distance et similarité. Les deux signaux sont toujours loggés en
mode objectif, quel que soit le détecteur actif.

### Assist de cap visuel (mode objectif)

Sur une caméra éloignée des données d'entraînement, l'encodeur de but du
modèle peut être incapable de situer la cible dans le champ de vision — le
robot passe à côté d'un but pourtant visible (même cause racine que la
distance saturée). L'assist de cap (activé par défaut) balaie des fenêtres
horizontales de l'image courante, repère celle qui ressemble le plus à la
photo-goal, en déduit un cap (`goal_bearing_deg`, positif = gauche), et
applique une commande angulaire proportionnelle vers ce cap. Le cap n'est
appliqué que si la localisation est nette (`goal_contrast` ≥
`--goal-visible-contrast`, défaut 0.05) ; il est confirmé sur
`--goal-bearing-patience` frames, lissé (`--goal-bearing-smoothing`), et une
zone morte (`--goal-bearing-deadband-deg`, défaut 3°) fait rouler parfaitement
droit quand la cible est centrée — évite le zigzag. Gain angulaire :
`--goal-steering-gain` (défaut 1.5). Sinon le comportement standard (moyenne
des échantillons) s'applique. Désactivation : `--no-goal-heading-assist`.

### Limites du goal lointain — et la bonne méthode

NoMaD est une politique **courte portée** : l'image-objectif doit avoir un
**recouvrement visuel** avec ce que voit le robot (même pièce, quelques
mètres, angle similaire). Une photo lointaine ou hors champ → le modèle ne
peut pas s'orienter et erre. Pour aller loin, la méthode prévue par les
auteurs est la **carte topologique** : une suite de photos rapprochées le
long du trajet, enchaînées comme sous-buts (cf. `navigate.py` upstream). À
défaut, prendre la photo-goal **depuis le point de vue du robot** (même
hauteur, même direction d'approche) améliore beaucoup l'accroche.

## Prendre une photo avec la caméra du Kachaka

Pour capturer une image (caméra avant par défaut) et l'enregistrer en `.jpg` :

```bash
python -m kachaka_navigation.scripts.capture_camera_image -o photo.jpg
python -m kachaka_navigation.scripts.capture_camera_image -c back -o back.jpg   # ou -c tof
```

Le fichier est écrit dans le dossier courant. Pour le récupérer sur une autre
machine : `scp user@<ip>:chemin/photo.jpg .`.

C'est aussi la façon de fabriquer une **image-objectif** pour la navigation
ciblée : on capture la destination, puis on la passe en `--goal-image`.

```bash
python -m kachaka_navigation.scripts.capture_camera_image \
  -o models/nomad_original/goals/goal.jpg
python -m kachaka_navigation.scripts.run_nomad_kachaka_control \
  --goal-image models/nomad_original/goals/goal.jpg
```

Caméras disponibles : `front` (défaut), `back`, `tof`. Prérequis : robot
joignable (`KACHAKA_HOST` correct, même réseau).

## Paramètres utiles

| Option | Défaut | Rôle |
|--------|--------|------|
| `--device` | `cpu` | `cpu` / `mps` (Apple Silicon) / `cuda` / `auto` |
| `--num-samples` | 8 | trajectoires échantillonnées par pas (latence ↑ avec la valeur) |
| `--num-diffusion-iters` | 10 | pas de débruitage diffusion |
| `--waypoint-index` | 2 | waypoint utilisé pour la commande (2 = milieu, mouvement plus droit) |
| `--max-linear-speed` | 0.15 | borne de vitesse linéaire (m/s) |
| `--max-angular-speed` | 0.3 | borne de vitesse angulaire (rad/s) |
| `--frame-rate` | 3.0 | cadence de la boucle (Hz) |
| `--max-iterations` | 0 | 0 = jusqu'à `Ctrl-C` |

Sur CPU (Apple Silicon), une itération NoMaD prend ~0.5–0.7 s avec les valeurs
par défaut. Pour accélérer : baisser `--num-samples`, ou tester `--device mps`.

## Sécurité

- Double protection sur la vitesse : le modèle borne déjà via le contrôleur PD,
  et la boucle re-borne via `VelocityLimits`.
- En cas d'erreur (caméra, modèle), la boucle envoie immédiatement une vitesse
  nulle.
- À la sortie (normale, `Ctrl-C`, ou exception), la boucle envoie une vitesse
  nulle puis désactive le contrôle manuel.

## Dépannage

- `kachaka-api is required` : `pip install kachaka-api` dans `kachaka-nav`.
- `Could not import the NoMaD model code` : relancer `./scripts/setup_nomad.sh`.
- `NoMaD checkpoint not found` : le téléchargement a échoué, relancer le setup.
- Le robot ne bouge pas en mode réel : vérifier que rien d'autre ne tient le
  contrôle manuel et que `KACHAKA_HOST` pointe le bon robot.
