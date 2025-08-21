# -*- coding: utf-8 -*-
"""
环境切换脚本
用于在本地开发和远程服务器环境之间切换配置
"""

import json
import os
import sys
import codecs

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 配置文件路径
CONFIG_FILE = os.path.join(PROJECT_ROOT, "config", "environment.json")
FRONTEND_API_CONFIG = os.path.join(PROJECT_ROOT, "client", "miniprogram", "core", "constants", "api.ts")
FRONTEND_UTILS_API = os.path.join(PROJECT_ROOT, "client", "miniprogram", "utils", "api.ts")
BACKEND_SETTINGS = os.path.join(PROJECT_ROOT, "server", "config", "settings.py")

def load_config():
    """加载环境配置"""
    with codecs.open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(config):
    """保存环境配置"""
    with codecs.open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def get_base_url(env_config):
    """根据环境配置生成API基础URL"""
    backend = env_config['backend']
    return "{protocol}://{host}:{port}/api/v1".format(
        protocol=backend['protocol'],
        host=backend['host'],
        port=backend['port']
    )

def update_frontend_api_config(base_url):
    """更新前端API配置文件"""
    # 读取当前文件
    with codecs.open(FRONTEND_API_CONFIG, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换BASE_URL
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.strip().startswith("BASE_URL:"):
            lines[i] = "  BASE_URL: '{}',".format(base_url)
            break
    
    # 写回文件
    with codecs.open(FRONTEND_API_CONFIG, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

def update_frontend_utils_api(base_url):
    """更新前端utils/api.ts文件中的BASE_URL"""
    # 读取当前文件
    with codecs.open(FRONTEND_UTILS_API, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换BASE_URL
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.strip().startswith("const BASE_URL ="):
            lines[i] = "const BASE_URL = '{}';".format(base_url)
            break
    
    # 写回文件
    with codecs.open(FRONTEND_UTILS_API, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

def update_backend_settings(env_config):
    """更新后端配置文件"""
    database_path = env_config['database']['path']
    
    # 读取当前文件
    with codecs.open(BACKEND_SETTINGS, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换database_url
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.strip().startswith("database_url:"):
            lines[i] = '    database_url: str = "duckdb://{}"'.format(database_path)
            break
    
    # 写回文件
    with codecs.open(BACKEND_SETTINGS, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

def switch_environment(env_name):
    """切换到指定环境"""
    config = load_config()
    
    if env_name not in config['environments']:
        print("Error: Environment '{}' does not exist".format(env_name))
        print("Available environments: {}".format(list(config['environments'].keys())))
        return False
    
    # 更新活动环境
    config['active'] = env_name
    save_config(config)
    
    # 获取环境配置
    env_config = config['environments'][env_name]
    base_url = get_base_url(env_config)
    
    # 更新各配置文件
    print("Switching to environment: {}".format(env_name))
    print("API URL: {}".format(base_url))
    
    try:
        update_frontend_api_config(base_url)
        print("✓ Updated frontend API config")
        
        update_frontend_utils_api(base_url)
        print("✓ Updated frontend utils API config")
        
        update_backend_settings(env_config)
        print("✓ Updated backend config")
        
        print("✓ Environment switch completed: {}".format(env_name))
        return True
        
    except Exception as e:
        print("Error: Failed to update config files - {}".format(e))
        return False

def show_current_environment():
    """显示当前环境信息"""
    config = load_config()
    current_env = config['active']
    env_config = config['environments'][current_env]
    base_url = get_base_url(env_config)
    
    print("Current environment: {}".format(current_env))
    print("API URL: {}".format(base_url))
    print("Database path: {}".format(env_config['database']['path']))

def show_help():
    """显示帮助信息"""
    print("Environment switching script")
    print("Usage:")
    print("  python switch-env.py [environment_name]")
    print("  python switch-env.py --current  # Show current environment")
    print("  python switch-env.py --help     # Show this help")
    print()
    print("Available environments:")
    config = load_config()
    for env_name, env_config in config['environments'].items():
        status = " (current)" if env_name == config['active'] else ""
        print("  {}{}".format(env_name, status))

def main():
    """主函数"""
    if len(sys.argv) < 2:
        show_current_environment()
        return
    
    arg = sys.argv[1]
    
    if arg == "--help" or arg == "-h":
        show_help()
    elif arg == "--current" or arg == "-c":
        show_current_environment()
    else:
        switch_environment(arg)

if __name__ == "__main__":
    main()