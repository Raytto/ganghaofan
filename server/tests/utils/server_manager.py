"""
测试服务器管理器
负责启动、停止和管理测试服务器
"""

import subprocess
import time
import signal
import os
from pathlib import Path
from typing import Optional, Dict, Any
import requests

from .config_manager import get_config_manager


class TestServerManager:
    """测试服务器管理器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """初始化服务器管理器"""
        if config is None:
            config = get_config_manager().get_server_config()
        
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.server_pid: Optional[int] = None
        
        # 服务器配置
        self.host = config["host"]
        self.port = config["port"]
        self.startup_timeout = config.get("startup_timeout", 30)
        
        # 项目路径
        self.server_dir = Path(__file__).parent.parent.parent
    
    def start_server(self) -> bool:
        """启动测试服务器"""
        if self.is_server_running():
            print(f"✓ Server already running on {self.host}:{self.port}")
            return True
        
        try:
            print(f"Starting test server on {self.host}:{self.port}...")
            
            # 设置环境变量
            env = os.environ.copy()
            env.update({
                "TESTING": "true",
                "TEST_DB_PATH": "data/test_ganghaofan.duckdb",
                "TEST_SERVER_PORT": str(self.port),
                "JWT_SECRET_KEY": "test-secret-key-for-e2e-testing"
            })
            
            # 构建启动命令（使用当前Python环境）
            cmd = [
                "python", "-m", "uvicorn", "server.app:app",
                "--reload", "--host", self.host, "--port", str(self.port)
            ]
            
            # 启动服务器进程
            self.process = subprocess.Popen(
                cmd,
                cwd=self.server_dir.parent,  # 在项目根目录运行
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # 创建新的进程组
            )
            
            self.server_pid = self.process.pid
            
            # 等待服务器启动
            if self.wait_for_server():
                print(f"✓ Test server started successfully (PID: {self.server_pid})")
                return True
            else:
                print("✗ Test server failed to start")
                self.stop_server()
                return False
                
        except Exception as e:
            print(f"✗ Failed to start test server: {e}")
            self.stop_server()
            return False
    
    def stop_server(self):
        """停止测试服务器"""
        try:
            if self.process:
                print(f"Stopping test server (PID: {self.server_pid})...")
                
                # 终止进程组（包括子进程）
                try:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                except (OSError, ProcessLookupError):
                    pass
                
                # 等待进程结束
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # 强制终止
                    try:
                        os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                        self.process.wait(timeout=2)
                    except (OSError, ProcessLookupError, subprocess.TimeoutExpired):
                        pass
                
                self.process = None
                self.server_pid = None
                
                print("✓ Test server stopped")
            
            # 额外检查端口是否被其他进程占用
            self._kill_port_process()
            
        except Exception as e:
            print(f"Warning: Error stopping server: {e}")
    
    def _kill_port_process(self):
        """终止占用测试端口的进程"""
        try:
            # 查找占用端口的进程
            cmd = f"lsof -ti:{self.port}"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    try:
                        pid = int(pid.strip())
                        os.kill(pid, signal.SIGTERM)
                        print(f"Killed process {pid} using port {self.port}")
                    except (ValueError, OSError):
                        pass
        except Exception:
            pass
    
    def is_server_running(self) -> bool:
        """检查服务器是否运行"""
        try:
            response = requests.get(f"http://{self.host}:{self.port}/health", timeout=1)
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def wait_for_server(self, timeout: Optional[int] = None) -> bool:
        """等待服务器启动完成"""
        if timeout is None:
            timeout = self.startup_timeout
        
        print(f"Waiting for server to start (timeout: {timeout}s)...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_server_running():
                elapsed = time.time() - start_time
                print(f"✓ Server is ready (took {elapsed:.1f}s)")
                return True
            
            # 检查进程是否还在运行
            if self.process and self.process.poll() is not None:
                print("✗ Server process terminated unexpectedly")
                self._print_server_logs()
                return False
            
            time.sleep(0.5)
        
        print(f"✗ Server not ready after {timeout}s")
        self._print_server_logs()
        return False
    
    def _print_server_logs(self):
        """打印服务器日志（用于调试）"""
        if not self.process:
            return
        
        try:
            # 读取stdout和stderr
            if self.process.stdout:
                stdout = self.process.stdout.read().decode('utf-8', errors='ignore')
                if stdout.strip():
                    print("=== Server stdout ===")
                    print(stdout)
            
            if self.process.stderr:
                stderr = self.process.stderr.read().decode('utf-8', errors='ignore')
                if stderr.strip():
                    print("=== Server stderr ===")
                    print(stderr)
                    
        except Exception as e:
            print(f"Failed to read server logs: {e}")
    
    def get_server_url(self) -> str:
        """获取服务器URL"""
        return f"http://{self.host}:{self.port}"
    
    def get_health_url(self) -> str:
        """获取健康检查URL"""
        return f"{self.get_server_url()}/health"
    
    def restart_server(self) -> bool:
        """重启服务器"""
        print("Restarting test server...")
        self.stop_server()
        time.sleep(1)  # 等待端口释放
        return self.start_server()
    
    def get_server_status(self) -> Dict[str, Any]:
        """获取服务器状态信息"""
        is_running = self.is_server_running()
        
        status = {
            "running": is_running,
            "url": self.get_server_url(),
            "pid": self.server_pid,
            "config": self.config
        }
        
        if is_running:
            try:
                response = requests.get(self.get_health_url(), timeout=5)
                status["health_check"] = response.json()
            except Exception as e:
                status["health_error"] = str(e)
        
        return status
    
    def __enter__(self):
        """上下文管理器入口"""
        if not self.start_server():
            raise RuntimeError("Failed to start test server")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop_server()


if __name__ == "__main__":
    # 测试服务器管理器
    try:
        print("Testing server manager...")
        
        server_mgr = TestServerManager()
        
        # 获取状态
        status = server_mgr.get_server_status()
        print(f"Initial status: {status['running']}")
        
        # 启动服务器
        if server_mgr.start_server():
            print("✓ Server started successfully")
            
            # 检查状态
            final_status = server_mgr.get_server_status()
            print(f"Final status: {final_status}")
            
            # 停止服务器
            server_mgr.stop_server()
            print("✓ Server stopped successfully")
            
        else:
            print("✗ Server start failed")
        
        print("✓ Server manager test completed")
        
    except KeyboardInterrupt:
        print("\nTest interrupted, cleaning up...")
        if 'server_mgr' in locals():
            server_mgr.stop_server()
    except Exception as e:
        print(f"✗ Server manager test failed: {e}")
        if 'server_mgr' in locals():
            server_mgr.stop_server()