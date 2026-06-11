# Lancer NoMaD sur le Kachaka — mémo

Les commandes, dans l'ordre. Guide détaillé : [docs/nomad_kachaka.md](docs/nomad_kachaka.md).

## 0. Installation (une seule fois)

```bash
git clone -b nomad-integration https://github.com/guilhem0908/KachakaNavigation.git
cd KachakaNavigation
./scripts/linux_quickstart.sh      # venv + deps + checkpoint + self-test
```

> Besoin d'Internet pour cette étape (pip + téléchargement du checkpoint).

## 1. À chaque session : activer l'environnement

```bash
source .venv/bin/activate
```

## 2. Vérifier NoMaD (sans robot)

```bash
python -m kachaka_navigation.scripts.run_nomad_kachaka_control --self-test
```

→ attendu : `SELF-TEST OK: NoMaD produced velocity commands on this machine.`

## 3. Régler l'IP du robot

```bash
nano .env        # KACHAKA_HOST=<ip du robot>   (PC et robot sur le même réseau)
```

## 4. Dry-run — le robot NE bouge PAS

```bash
python -m kachaka_navigation.scripts.run_nomad_kachaka_control --dry-run --max-iterations 30
```

Vérifie : connexion OK, caméra OK, vitesses proposées cohérentes.

## 5. Pilotage réel — le robot BOUGE

> ⚠️ Dégager la zone, garder une main sur l'arrêt d'urgence. `Ctrl-C` arrête
> proprement (vitesse nulle + contrôle manuel désactivé).

```bash
python -m kachaka_navigation.scripts.run_nomad_kachaka_control \
    --device auto --max-linear-speed 0.1 --max-angular-speed 0.3
```

## Prendre une photo avec la caméra du Kachaka

```bash
python -m kachaka_navigation.scripts.capture_camera_image -o photo.jpg          # caméra avant
python -m kachaka_navigation.scripts.capture_camera_image -c back -o back.jpg   # caméra arrière (ou -c tof)
```

La photo est enregistrée en `.jpg` dans le dossier courant. Pour la **récupérer**
sur une autre machine : `scp user@<ip>:chemin/photo.jpg .`

## Aller jusqu'à une image-objectif et s'y arrêter — séquence complète (shell Linux)

Toutes les commandes, dans l'ordre, à lancer depuis le PC Linux (même réseau
que le robot).

### Étape 1 — Mettre à jour le code et activer l'environnement

```bash
cd ~/KachakaNavigation          # ton clone
git pull origin nomad-integration
source .venv/bin/activate
```

### Étape 2 — Capturer l'image-objectif

Amène le robot (app Kachaka ou à la main) **à l'endroit cible**, orienté comme
il arrivera, puis capture ce que voit sa caméra :

```bash
python -m kachaka_navigation.scripts.capture_camera_image \
  -o models/nomad_original/goals/goal.jpg
```

> ⚠️ L'image-objectif doit être **la vue du robot à l'arrêt sur la cible** —
> pas une photo prise 2 m avant, ni d'un autre point de vue. C'est elle qui
> sert de référence d'arrivée.

### Étape 3 — Calibrer le seuil d'arrêt (robot SUR la cible, ne bouge pas)

Sans déplacer le robot, lance un dry-run court et note les valeurs
`goal_distance=` affichées — c'est la distance prédite quand il est arrivé :

```bash
python -m kachaka_navigation.scripts.run_nomad_kachaka_control \
  --goal-image models/nomad_original/goals/goal.jpg \
  --dry-run --max-iterations 10
```

Choisis comme seuil cette valeur **+ une petite marge** (ex. valeurs ~2-3 →
seuil 3.5 ; valeurs ~4-5 → seuil 5.5).

### Étape 4 — Ramener le robot au départ, puis dry-run du trajet

Replace le robot au point de départ (à **quelques mètres**, cible dans un
champ visuel proche — NoMaD est courte portée), puis vérifie le comportement
sans le faire bouger :

```bash
python -m kachaka_navigation.scripts.run_nomad_kachaka_control \
  --goal-image models/nomad_original/goals/goal.jpg \
  --goal-reached-distance 3.5 \
  --dry-run --max-iterations 30
```

### Étape 5 — Navigation réelle (le robot BOUGE)

> Zone dégagée, `Ctrl-C` arrête proprement.

```bash
# s'arrêter sur la cible (défaut)
python -m kachaka_navigation.scripts.run_nomad_kachaka_control \
  --goal-image models/nomad_original/goals/goal.jpg \
  --goal-reached-distance 3.5 \
  --max-linear-speed 0.1 --max-angular-speed 0.3

# variante : s'arrêter + annoncer au haut-parleur
python -m kachaka_navigation.scripts.run_nomad_kachaka_control \
  --goal-image models/nomad_original/goals/goal.jpg \
  --goal-reached-distance 3.5 \
  --on-goal-reached speak --goal-reached-text "Objectif atteint" \
  --max-linear-speed 0.1 --max-angular-speed 0.3

# variante : s'arrêter + rentrer à la base
python -m kachaka_navigation.scripts.run_nomad_kachaka_control \
  --goal-image models/nomad_original/goals/goal.jpg \
  --goal-reached-distance 3.5 \
  --on-goal-reached return_home \
  --max-linear-speed 0.1 --max-angular-speed 0.3
```

### Étape 6 — Ajuster si besoin

| Symptôme | Correctif |
|----------|-----------|
| Ne s'arrête jamais | augmenter `--goal-reached-distance` (4, 5, 6…) |
| S'arrête trop tôt / au mauvais endroit | baisser `--goal-reached-distance`, ou augmenter `--goal-reached-patience` (3-4) |
| `goal_distance` reste haute (~10-16) **même robot posé sur la cible** | la tête de distance est inutilisable sur cette caméra → passer au détecteur par similarité (ci-dessous) |
| Erre, ne s'oriente pas vers la cible | cible trop loin / hors champ : rapprocher le départ, ou re-prendre `goal.jpg` depuis le point de vue d'approche |
| Dépasse la cible avant de s'arrêter | baisser `--max-linear-speed` (0.08) |

### Étape 7 — Si la distance est inutilisable : détecteur par SIMILARITÉ

Si la calibration (étape 3) donne une `goal_distance` quasi identique sur la
cible et en approche (ex. ~15 partout), utilise la **similarité d'image
directe** avec la photo-goal — insensible au biais du modèle. Le seuil
**s'auto-calibre depuis la position de départ** : les premières lectures
mesurent à quel point la vue de départ ressemble déjà à la photo, et le seuil
se place entre cette base et 1.0 — donc pas de réglage manuel, quel que soit
le point de départ :

```bash
python -m kachaka_navigation.scripts.run_nomad_kachaka_control \
  --goal-image models/nomad_original/goals/goal.jpg \
  --arrival-detector similarity \
  --goal-reached-patience 3 \
  --max-linear-speed 0.08 --max-angular-speed 0.3
```

Les logs montrent `goal_similarity=` (1.0 = la caméra voit exactement la
photo) et `goal_similarity_threshold=` (le seuil auto-calculé, affiché après
les ~5 premières frames).

Réglage si besoin, via `--goal-similarity-margin` (défaut 0.5) :

| Symptôme | Correctif |
|----------|-----------|
| S'arrête trop tôt (en chemin) | monter la marge : `--goal-similarity-margin 0.65` |
| Ne s'arrête pas sur la cible | baisser la marge : `--goal-similarity-margin 0.35` |
| Je veux un seuil fixe | `--goal-similarity-threshold 0.85` (désactive l'auto) |

`--arrival-detector any` accepte le premier des deux signaux (distance ou
similarité) qui se déclenche. Note : la navigation reste 100 % NoMaD — seul le
critère d'arrêt change.

## Options utiles

| Option | Défaut | Rôle |
|--------|--------|------|
| `--device` | `auto` | `auto` / `cpu` / `cuda` / `mps` (auto = GPU si dispo) |
| `--num-samples` | 8 | trajectoires échantillonnées (latence ↑ avec la valeur) |
| `--waypoint-index` | 2 | waypoint utilisé (2 = mouvement plus droit) |
| `--waypoint-aggregation` | mean | `mean` = moyenne des trajectoires (cap plus stable), `first` = comportement upstream |
| `--no-center-crop` | — | désactive le recadrage 4:3 appliqué avant le resize modèle |
| `--frame-rate` | 3 | cadence de la boucle (Hz) |
| `--goal-image <img>` | — | navigation vers une image-objectif (sinon : exploration) |
| `--arrival-detector` | distance | signal d'arrivée : `distance` / `similarity` / `any` |
| `--goal-reached-distance` | 3.0 | seuil de distance prédite sous lequel = « arrivé » |
| `--goal-similarity-threshold` | auto | seuil de similarité fixe (0-1) ; omis = auto-calibration au départ |
| `--goal-similarity-margin` | 0.5 | auto-calibration : seuil = base + marge × (1 − base) |
| `--goal-reached-patience` | 2 | lectures consécutives positives avant arrêt |
| `--on-goal-reached` | stop | action à l'arrivée : `stop` / `speak` / `return_home` |
| `--goal-reached-text` | Objectif atteint | texte dit si `speak` |
| `--max-iterations N` | 0 | 0 = jusqu'à `Ctrl-C` |
