"""
Passphrase mapping utility functions.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any


_CACHE: Dict[str, str] | None = None
_MOCK_CACHE: Dict[str, Any] | None = None


def get_passphrase_map() -> Dict[str, str]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE

    # 1) Env var
    env_val = os.getenv("GHF_PASSPHRASE_MAP")
    if env_val:
        try:
            m = json.loads(env_val)
            if isinstance(m, dict):
                _CACHE = {str(k): str(v) for k, v in m.items()}
                return _CACHE
        except Exception:
            pass

    # 2) JSON file
    cfg_path = Path(__file__).parent / "passphrases.json"
    try:
        if cfg_path.exists():
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                _CACHE = {str(k): str(v) for k, v in data.items()}
                return _CACHE
    except Exception:
        pass

    _CACHE = {}
    return _CACHE


def get_mock_settings() -> Dict[str, Any]:
    """返回开发阶段的模拟登录设置。"""
    global _MOCK_CACHE
    if _MOCK_CACHE is not None:
        return _MOCK_CACHE

    # 默认
    defaults = {
        "mock_enabled": False,
        "open_id": "",
        "nickname": "",
        "unique_per_login": False,
    }

    # 1) Env var
    env_val = os.getenv("GHF_MOCK_AUTH")
    if env_val:
        try:
            m = json.loads(env_val)
            if isinstance(m, dict):
                _MOCK_CACHE = {**defaults, **m}
                return _MOCK_CACHE
        except Exception:
            pass

    # 2) JSON file
    cfg_path = Path(__file__).parent / "dev_mock.json"
    try:
        if cfg_path.exists():
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                # Normalize field names
                normalized = {}
                for k, v in data.items():
                    if k == "enabled":
                        normalized["mock_enabled"] = v
                    elif k == "openid":
                        normalized["open_id"] = v
                    else:
                        normalized[k] = v
                _MOCK_CACHE = {**defaults, **normalized}
                return _MOCK_CACHE
    except Exception:
        pass

    _MOCK_CACHE = defaults
    return _MOCK_CACHE