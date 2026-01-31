import json
import os

CONFIG_FILE = "config.json"


def load_config():
    if not os.path.exists(CONFIG_FILE):
        return None

    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def save_config(config: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)


def get_or_create_config():
    config = load_config()

    if config is not None:
        return config

    # In GUI mode, do not ask for input via stdin
    # Just return defaults. The UI will handle missing keys.
    config = {
        "real_debrid_api_key": "",
        "min_seeders": 5,
        "min_resolution": 720,
        "delay_between_movies": 5,
        "max_per_quality": 1,
        "allow_packs_fallback": True,
        "run_mode": "oneshot",
        "repeat_minutes": 60,
    }

    save_config(config)
    return config
