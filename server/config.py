"""
Server configuration utilities.

Provides a way to map passphrases to DB keys via either:
- Environment variable GHF_PASSPHRASE_MAP containing a JSON object
- JSON file at server/config/passphrases.json
Fallback: if no mapping found, treat passphrase as the key itself.
"""

from __future__ import annotations

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
    cfg_path = Path(__file__).parent / "config" / "passphrases.json"
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
    """返回开发阶段的模拟登录设置。

    来源优先级：
    1) 环境变量 GHF_MOCK_AUTH (JSON字符串)
    2) 文件 server/config/dev_mock.json

        返回字段（默认值）：
    {
            "mock_enabled": false,
            "open_id": "",
            "nickname": "",
            "unique_per_login": false
    }
    """
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
            data = json.loads(env_val)
            if isinstance(data, dict):
                _MOCK_CACHE = {
                    "mock_enabled": bool(data.get("mock_enabled", False)),
                    "open_id": str(data.get("open_id", "")),
                    "nickname": str(data.get("nickname", "")),
                    "unique_per_login": bool(data.get("unique_per_login", False)),
                }
                return _MOCK_CACHE
        except Exception:
            pass

    # 2) JSON file
    cfg_path = Path(__file__).parent / "config" / "dev_mock.json"
    try:
        if cfg_path.exists():
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                _MOCK_CACHE = {
                    "mock_enabled": bool(data.get("mock_enabled", False)),
                    "open_id": str(data.get("open_id", "")),
                    "nickname": str(data.get("nickname", "")),
                    "unique_per_login": bool(data.get("unique_per_login", False)),
                }
                return _MOCK_CACHE
    except Exception:
        pass

    _MOCK_CACHE = defaults
    return _MOCK_CACHE
