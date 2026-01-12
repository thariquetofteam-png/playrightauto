import os

def load_env_properties(file_path="config/env.properties"):
    env_data = {}

    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"Environment file not found: {file_path}"
        )

    with open(file_path, "r") as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                env_data[key.strip()] = value.strip()

    return env_data