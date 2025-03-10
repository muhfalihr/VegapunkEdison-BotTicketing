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
    """Convert Unix timestamp to formatted date string in GMT+7 timezone.
    
    Args:
        epoch: Unix timestamp (seconds since Jan 1, 1970)
        store: If True, use compact format for storage, otherwise use readable format
        
    Returns:
        Formatted date string
    """
    tz_gmt7 = timezone(timedelta(hours=7))
    
    dt_gmt7 = datetime.fromtimestamp(epoch, tz_gmt7)
    
    fmt = "%Y-%m-%d %H:%M:%S" if store else "%A, %d %B %Y %H:%M:%S"
    return dt_gmt7.strftime(fmt)


def reltime(past_time: datetime) -> str:
    """Convert a datetime to a human-readable relative time string.
    
    Args:
        past_time: The datetime in the past to compare against now
        
    Returns:
        A human-readable string like "5 minutes ago" or "3 months ago"
    """
    if past_time.tzinfo is None:
        past_time = past_time.replace(tzinfo=timezone.utc)
    
    datetime_now = datetime.now(timezone.utc)
    diff = datetime_now - past_time
    
    seconds_diff = diff.total_seconds()
    
    if seconds_diff < 60:
        return "just now"
    elif seconds_diff < 3600:  # 1 hour
        return f"{int(seconds_diff // 60)} minutes ago"
    elif seconds_diff < 86400:  # 1 day
        return f"{int(seconds_diff // 3600)} hours ago"
    elif seconds_diff < 604800:  # 1 week
        return f"{diff.days} days ago"
    elif seconds_diff < 2592000:  # 30 days
        return f"{diff.days // 7} weeks ago"
    elif seconds_diff < 31536000:  # 365 days
        return f"{diff.days // 30} months ago"
    else:
        return f"{diff.days // 365} years ago"


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
