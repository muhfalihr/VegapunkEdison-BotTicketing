import yaml
import time
import pytz
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List


def get_config_yaml(config_path: str = "config.yml") -> Dict[str, Any]:
    """Get Config from YAML file.

    Args:
        config_path: str
            
            Config file path is located. Default: config.yml
    
    Returns:

    """
    try:
        with open(config_path, "r") as stream:
            config: Dict[str, Any] = yaml.safe_load(stream.read())
        return config
    except (FileNotFoundError, Exception) as e:
        raise e


def generate_id(user_id: int) -> str:
    """Create uniq id for each users."""
    current_time: float = time.time()
    return hashlib.sha256(f"{user_id}-{current_time}".encode()).hexdigest()[:16]


def epodate(epoch: int, store=False) -> str:
    dt: datetime = datetime.fromtimestamp(epoch, timezone.utc)
    dt_gmt7 = dt.astimezone(timezone(timedelta(hours=7)))
    if not store:
        fmt_time = dt_gmt7.strftime("%A, %d %B %Y %H:%M:%S")
    else:
        fmt_time = dt_gmt7.strftime("%Y-%m-%d %H:%M:%S")
    return fmt_time


def chakey(json: Dict[str, Any], key: str, new_key: str) -> Dict[str, Any]:
    """Change Key Json"""
    json[new_key] = json.pop(key)
    return json


def arson(**kwargs) -> Dict[str, Any]:
    """Argument to Dictionary."""
    return kwargs

def curtime(timezone: str):
    """Get Current Timestamp with specific Timezone"""
    tz = pytz.timezone(timezone)
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")