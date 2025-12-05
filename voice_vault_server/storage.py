#!/usr/bin/env python3
"""
storage.py

JSON-based storage utilities for Voice Vault.
-Manage users and their audio samples
-Store and load voiceprints
-Store last authentication result
-Store authentication attempts log
-Load secrets for the vault
"""

import json
import os
from typing import Dict, Any, List, Optional

import numpy as np

from config import (
    DATA_DIR,
    AUDIO_DIR,
    SECRETS_DIR,
    USERS_JSON,
    VOICEPRINTS_JSON,
    LAST_AUTH_JSON,
    ATTEMPTS_JSON,
    SECRETS_JSON,
)



# Helpers

def _read_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _convert_to_native_types(obj: Any) -> Any:
    """
    Convert numpy types to native Python types for JSON serialization.
    """
    import numpy as np
    
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: _convert_to_native_types(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_convert_to_native_types(item) for item in obj]
    else:
        return obj


def _write_json(path: str, data: Any) -> None:
    # Convert numpy types to native Python types before JSON serialization
    data = _convert_to_native_types(data)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# Users

def load_users() -> Dict[str, Any]:
    return _read_json(USERS_JSON, default={})


def save_users(users: Dict[str, Any]) -> None:
    _write_json(USERS_JSON, users)


def create_user(username: str) -> None:
    users = load_users()
    # First ensure that the user entry does not exist already
    if username not in users:
        users[username] = {
            "audio_samples": []
        }
        save_users(users)


def register_sample(username: str, audio_path: str, features: Any) -> None:
    """
    Register a new enrollment sample for a user.

    """
    users = load_users()
    if username not in users:
        users[username] = {"audio_samples": []}

    # Convert features to list (JSON serializable)
    if isinstance(features, np.ndarray):
        feat_list = features.tolist()
    else:
        feat_list = list(features)

    sample_entry = {
        "path": audio_path,
        "features": feat_list,
    }
    users[username]["audio_samples"].append(sample_entry)
    save_users(users)


# Voiceprints

def load_voiceprints() -> Dict[str, np.ndarray]:
    raw = _read_json(VOICEPRINTS_JSON, default={})
    vp: Dict[str, np.ndarray] = {}
    for username, vec in raw.items():
        try:
            vp[username] = np.array(vec, dtype=float)
        except Exception:
            continue
    return vp


def save_voiceprints(voiceprints: Dict[str, np.ndarray]) -> None:

    raw = {u: v.tolist() for u, v in voiceprints.items()}
    _write_json(VOICEPRINTS_JSON, raw)


def recompute_voiceprint(username: str) -> None:
    # First ensure that the user entry exists
    users = load_users()
    if username not in users:
        return

    samples = users[username].get("audio_samples", [])
    if not samples:
        return

    feature_list = []
    for s in samples:
        feats = s.get("features")
        if feats is not None:
            try:
                feature_list.append(np.array(feats, dtype=float))
            except Exception:
                continue

    if not feature_list:
        return

    # Stack and get mean along axis 0
    stacked = np.stack(feature_list, axis=0)  
    centroid = np.mean(stacked, axis=0)
    voiceprints = load_voiceprints()
    voiceprints[username] = centroid
    save_voiceprints(voiceprints)


# Last auth result

def load_last_auth_result() -> Optional[Dict[str, Any]]:
    return _read_json(LAST_AUTH_JSON, default=None)


def save_last_auth_result(result: Dict[str, Any]) -> None:
    _write_json(LAST_AUTH_JSON, result)


# Attempts log

def load_attempts() -> List[Dict[str, Any]]:
    return _read_json(ATTEMPTS_JSON, default=[])


def save_attempts(attempts: List[Dict[str, Any]]) -> None:
    _write_json(ATTEMPTS_JSON, attempts)


def log_attempt(
    timestamp: str,
    recognized_user: Optional[str],
    distance: Optional[float],
    success: bool,
    audio_path: str,
) -> None:
    attempts = load_attempts()
    attempts.append(
        {
            "timestamp": timestamp,
            "recognized_user": recognized_user,
            "distance": distance,
            "success": success,
            "audio_path": audio_path,
        }
    )
    save_attempts(attempts)


# Secrets

def load_secrets() -> Dict[str, Any]:
    # Provide defaults if file doesn't exist
    default = {
        "global_message": "This is the default global secret. Edit secrets/secrets.json to customize.",
        "user_notes": {}
    }
    return _read_json(SECRETS_JSON, default=default)
