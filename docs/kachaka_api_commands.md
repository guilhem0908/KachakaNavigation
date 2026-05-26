# Kachaka Direct API Commands

These commands call the Kachaka API directly. They are useful for validating
robot connectivity before using ROS2 navigation models.

## Checks

```bash
python -m kachaka_navigation.scripts.check_api_connection
python -m kachaka_navigation.scripts.smoke_test_connection
python -m kachaka_navigation.scripts.list_locations
python -m kachaka_navigation.scripts.list_shelves
```

## Known Locations

```text
home      = charging dock
S01_home  = large shelf home area
S02_home  = small shelf home area
L02       = shared drop-off area / 受付
```

## Move To A Location

```bash
python -m kachaka_navigation.scripts.return_home
python -m kachaka_navigation.scripts.move_to_location home
python -m kachaka_navigation.scripts.move_to_location S01_home
python -m kachaka_navigation.scripts.move_to_location S02_home
python -m kachaka_navigation.scripts.move_to_location L02
```

## Dock Or Undock A Shelf

```bash
python -m kachaka_navigation.scripts.dock_shelf
python -m kachaka_navigation.scripts.undock_shelf
python -m kachaka_navigation.scripts.dock_any_shelf_at_location home
python -m kachaka_navigation.scripts.undock_shelf_at_location home
```

## Move A Shelf

```bash
python -m kachaka_navigation.scripts.move_shelf S01 L02
python -m kachaka_navigation.scripts.move_shelf S02 home
python -m kachaka_navigation.scripts.return_shelf S01
python -m kachaka_navigation.scripts.return_shelf S02
```

## Stop Current Command

```bash
python -m kachaka_navigation.scripts.cancel_command
```
