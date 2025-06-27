# config_manager.py
import json
import os

CONFIG_FILE_NAME = "app_config.json"

DEFAULT_CONFIG = {
    "gemini_api_key": "",
    "recipient_email": "",
    "smtp_settings": {
        "server": "smtp.example.com",
        "port": 587,
        "user": "user@example.com",
        "password": "", # Store passwords securely, e.g., using keyring or encrypted
        "use_tls": True
    },
    "scheduled_tasks": [
        # Example task structure:
        # {
        # "id": "unique_task_id_1",
        # "prompt": "What's the weather like tomorrow?",
        # "interval": "1 day 07:00", # Parsable by scheduler.py
        # "search_internet": True,
        # "enabled": True # To easily disable tasks without deleting
        # }
    ]
}

def get_config_path():
    """Determines the path for the config file (e.g., in user's app data directory)."""
    # For simplicity, saving in the same directory as the script for now.
    # A more robust solution would use platform-specific directories:
    # For example, using appdirs library:
    # from appdirs import user_config_dir
    # config_dir = user_config_dir("GeminiTaskScheduler", "YourAppName")
    # if not os.path.exists(config_dir):
    #     os.makedirs(config_dir)
    # return os.path.join(config_dir, CONFIG_FILE_NAME)
    return CONFIG_FILE_NAME


def load_config():
    """Loads configuration from the JSON file. Returns default config if file not found or invalid."""
    config_path = get_config_path()
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config_data = json.load(f)
                # Basic validation: ensure all top-level keys from default are present
                for key in DEFAULT_CONFIG:
                    if key not in config_data:
                        config_data[key] = DEFAULT_CONFIG[key]
                    # Specifically for smtp_settings, ensure all sub-keys are present
                    if key == "smtp_settings":
                        for sub_key in DEFAULT_CONFIG["smtp_settings"]:
                            if sub_key not in config_data["smtp_settings"]:
                               config_data["smtp_settings"][sub_key] = DEFAULT_CONFIG["smtp_settings"][sub_key]

                print(f"ConfigManager: Configuration loaded from {config_path}")
                return config_data
        else:
            print(f"ConfigManager: Config file not found at {config_path}. Using default configuration.")
            save_config(DEFAULT_CONFIG) # Save default config if none exists
            return DEFAULT_CONFIG
    except json.JSONDecodeError:
        print(f"ConfigManager: Error decoding JSON from {config_path}. Using default configuration.")
        return DEFAULT_CONFIG
    except Exception as e:
        print(f"ConfigManager: An error occurred loading config: {e}. Using default configuration.")
        return DEFAULT_CONFIG

def save_config(config_data):
    """Saves the given configuration data to the JSON file."""
    config_path = get_config_path()
    try:
        # Ensure the directory exists (important if using user_config_dir)
        # config_dir = os.path.dirname(config_path)
        # if not os.path.exists(config_dir):
        #     os.makedirs(config_dir, exist_ok=True)

        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=4)
        print(f"ConfigManager: Configuration saved to {config_path}")
        return True
    except IOError as e:
        print(f"ConfigManager: Error saving configuration to {config_path}: {e}")
    except Exception as e:
        print(f"ConfigManager: An unexpected error occurred while saving config: {e}")
    return False

# --- Functions to manage specific parts of the config ---

def get_tasks():
    config = load_config()
    return config.get("scheduled_tasks", [])

def add_task_to_config(task_data):
    """Adds a single task to the configuration and saves it."""
    config = load_config()
    if "scheduled_tasks" not in config:
        config["scheduled_tasks"] = []
    
    # Basic check for existing ID to prevent duplicates, can be made more robust
    existing_ids = {t.get("id") for t in config["scheduled_tasks"] if t.get("id")}
    if task_data.get("id") and task_data["id"] in existing_ids:
        print(f"ConfigManager: Task with ID '{task_data['id']}' already exists. Not adding.")
        return False # Or update existing, depending on desired behavior

    config["scheduled_tasks"].append(task_data)
    return save_config(config)

def update_task_in_config(task_id, updated_task_data):
    """Updates an existing task in the configuration by its ID."""
    config = load_config()
    task_found = False
    for i, task in enumerate(config.get("scheduled_tasks", [])):
        if task.get("id") == task_id:
            config["scheduled_tasks"][i] = updated_task_data
            task_found = True
            break
    if task_found:
        return save_config(config)
    else:
        print(f"ConfigManager: Task with ID '{task_id}' not found for update.")
        return False

def remove_task_from_config(task_id):
    """Removes a task from the configuration by its ID."""
    config = load_config()
    initial_len = len(config.get("scheduled_tasks", []))
    config["scheduled_tasks"] = [
        task for task in config.get("scheduled_tasks", []) if task.get("id") != task_id
    ]
    if len(config.get("scheduled_tasks", [])) < initial_len:
        return save_config(config)
    else:
        print(f"ConfigManager: Task with ID '{task_id}' not found for removal.")
        return False

if __name__ == '__main__':
    print("Testing ConfigManager...")

    # Clean up any existing config file for a fresh test
    test_config_path = get_config_path()
    if os.path.exists(test_config_path):
        os.remove(test_config_path)
        print(f"Removed existing test config file: {test_config_path}")

    # 1. Load initial config (should create default)
    print("\n1. Loading initial config (should be default):")
    initial_config = load_config()
    print(json.dumps(initial_config, indent=2))
    assert initial_config["gemini_api_key"] == ""
    assert len(initial_config["scheduled_tasks"]) == 0

    # 2. Modify and save config
    print("\n2. Modifying and saving config:")
    initial_config["gemini_api_key"] = "test_api_key_123"
    initial_config["recipient_email"] = "test@example.com"
    initial_config["smtp_settings"]["user"] = "smtp_user@example.com"
    save_config(initial_config)

    # 3. Load modified config
    print("\n3. Loading modified config:")
    loaded_config = load_config()
    print(json.dumps(loaded_config, indent=2))
    assert loaded_config["gemini_api_key"] == "test_api_key_123"
    assert loaded_config["recipient_email"] == "test@example.com"
    assert loaded_config["smtp_settings"]["user"] == "smtp_user@example.com"

    # 4. Test task management
    print("\n4. Testing task management:")
    task1 = {
        "id": "task_001", "prompt": "Daily summary", "interval": "1 day 08:00",
        "search_internet": False, "enabled": True
    }
    task2 = {
        "id": "task_002", "prompt": "Tech news", "interval": "1 hour",
        "search_internet": True, "enabled": True
    }

    print("Adding task1...")
    add_task_to_config(task1)
    print("Adding task2...")
    add_task_to_config(task2)
    
    tasks_after_add = get_tasks()
    print("Current tasks:", json.dumps(tasks_after_add, indent=2))
    assert len(tasks_after_add) == 2
    assert tasks_after_add[0]["id"] == "task_001"

    print("\nUpdating task1...")
    updated_task1 = task1.copy()
    updated_task1["prompt"] = "Daily news summary"
    updated_task1["enabled"] = False
    update_task_in_config("task_001", updated_task1)

    tasks_after_update = get_tasks()
    print("Current tasks after update:", json.dumps(tasks_after_update, indent=2))
    assert tasks_after_update[0]["prompt"] == "Daily news summary"
    assert not tasks_after_update[0]["enabled"]

    print("\nRemoving task2...")
    remove_task_from_config("task_002")
    tasks_after_remove = get_tasks()
    print("Current tasks after removal:", json.dumps(tasks_after_remove, indent=2))
    assert len(tasks_after_remove) == 1
    assert tasks_after_remove[0]["id"] == "task_001"
    
    print("\nAttempting to remove non-existent task:")
    remove_task_from_config("task_999")


    # Test loading config with missing SMTP sub-keys (to test default filling)
    print("\n5. Testing config load with missing SMTP sub-keys:")
    if os.path.exists(test_config_path):
        with open(test_config_path, 'r')as f:
            temp_conf = json.load(f)
        del temp_conf["smtp_settings"]["use_tls"] # Remove a sub-key
        with open(test_config_path, 'w') as f:
            json.dump(temp_conf, f, indent=4)
        
        reloaded_conf = load_config()
        print(json.dumps(reloaded_conf["smtp_settings"], indent=2))
        assert "use_tls" in reloaded_conf["smtp_settings"]
        assert reloaded_conf["smtp_settings"]["use_tls"] == DEFAULT_CONFIG["smtp_settings"]["use_tls"]


    # Clean up the test config file
    # if os.path.exists(test_config_path):
    #     os.remove(test_config_path)
    #     print(f"\nRemoved test config file: {test_config_path}")

    print("\nConfigManager test complete.")
