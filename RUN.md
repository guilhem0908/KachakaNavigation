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

Pour t'en servir comme **image-objectif** NoMaD (navigation ciblée) :

```bash
python -m kachaka_navigation.scripts.capture_camera_image -o models/nomad_original/goals/goal.jpg
python -m kachaka_navigation.scripts.run_nomad_kachaka_control --goal-image models/nomad_original/goals/goal.jpg
```

## Options utiles

| Option | Défaut | Rôle |
|--------|--------|------|
| `--device` | `auto` | `auto` / `cpu` / `cuda` / `mps` (auto = GPU si dispo) |
| `--num-samples` | 8 | trajectoires échantillonnées (latence ↑ avec la valeur) |
| `--waypoint-index` | 2 | waypoint utilisé (2 = mouvement plus droit) |
| `--frame-rate` | 3 | cadence de la boucle (Hz) |
| `--goal-image <img>` | — | navigation vers une image-objectif (sinon : exploration) |
| `--max-iterations N` | 0 | 0 = jusqu'à `Ctrl-C` |
