import os
import json
from dotenv import load_dotenv

load_dotenv()

def load_hana_config():
    base_path = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_path, 'config', 'env_cloud.json')
    with open(config_path) as f:
        return json.load(f)

def load_aicore_config():
    base_path = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_path, 'config', 'env_config.json')
    with open(config_path) as f:
        return json.load(f)
