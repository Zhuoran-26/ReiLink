#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "services" / "backend"
DESKTOP_DIR = ROOT / "apps" / "desktop"


def ok(message: str) -> None:
    print(f"✅ {message}")


def warn(message: str) -> None:
    print(f"⚠️ {message}")


def run(args: list[str], cwd: Path = ROOT, timeout: float = 3) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None


def command_version(command: str) -> str | None:
    path = shutil.which(command)
    if not path:
        return None
    result = run([command, "--version"])
    if result and result.returncode == 0:
        return result.stdout.strip().splitlines()[0]
    return path


def venv_python() -> Path:
    if sys.platform == "win32":
        return BACKEND_DIR / ".venv" / "Scripts" / "python.exe"
    return BACKEND_DIR / ".venv" / "bin" / "python"


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def port_is_occupied(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.25):
            return True
    except OSError:
        return False


def git_check_ignore(path: str) -> bool:
    result = run(["git", "check-ignore", "-q", path])
    return bool(result and result.returncode == 0)


def check_python() -> None:
    ok(f"Python 可用：{sys.version.split()[0]}")
    venv_dir = BACKEND_DIR / ".venv"
    python_path = venv_python()
    if venv_dir.is_dir() and python_path.is_file():
        ok("Backend venv 已找到")
        result = run(
            [
                str(python_path),
                "-c",
                "import fastapi, uvicorn, psutil, pydantic, pytest, httpx",
            ]
        )
        if result and result.returncode == 0:
            ok("Backend requirements 可用")
        else:
            warn("Backend requirements 可能未安装完整，请运行 make install-backend")
    else:
        warn("Backend venv 不存在，请运行 make install-backend")


def check_node() -> None:
    node_version = command_version("node")
    npm_version = command_version("npm")
    if node_version:
        ok(f"Node 可用：{node_version}")
    else:
        warn("Node 不可用")
    if npm_version:
        ok(f"npm 可用：{npm_version}")
    else:
        warn("npm 不可用")

    node_modules = DESKTOP_DIR / "node_modules"
    if node_modules.is_dir():
        ok("Desktop node_modules 已找到")
    else:
        warn("Desktop node_modules 不存在，请运行 make install-desktop")

    package_json = json.loads((DESKTOP_DIR / "package.json").read_text(encoding="utf-8"))
    has_electron_dependency = "electron" in {
        **package_json.get("dependencies", {}),
        **package_json.get("devDependencies", {}),
    }
    if has_electron_dependency and (node_modules / "electron").is_dir():
        ok("Electron dependency 已安装")
    elif has_electron_dependency:
        warn("Electron dependency 已声明但未安装，请运行 make install-desktop")
    else:
        warn("Electron dependency 未声明")


def check_env() -> None:
    env_path = BACKEND_DIR / ".env"
    if env_path.is_file():
        ok("services/backend/.env 已找到")
    else:
        warn("services/backend/.env 不存在")

    env_values = read_env_file(env_path)
    api_key = os.environ.get("DEEPSEEK_API_KEY") or env_values.get("DEEPSEEK_API_KEY", "")
    if api_key.strip():
        ok("DeepSeek API Key 已加载")
    else:
        warn("DeepSeek API Key 未配置")


def check_ports() -> None:
    for port in (8000, 5173):
        if port_is_occupied(port):
            warn(f"端口 {port} 已被占用")
        else:
            ok(f"端口 {port} 可用")


def check_git() -> None:
    if git_check_ignore("data/memory/user_profile.json"):
        ok("data/memory 本地数据文件已被 gitignore")
    else:
        warn("data/memory 本地数据文件未被 gitignore")

    if git_check_ignore("data/session/game_session_state.json"):
        ok("data/session 本地状态文件已被 gitignore")
    else:
        warn("data/session 本地状态文件未被 gitignore")

    branch = run(["git", "branch", "--show-current"])
    if branch and branch.returncode == 0:
        ok(f"当前 git 分支：{branch.stdout.strip() or 'unknown'}")
    else:
        warn("无法读取当前 git 分支")

    status = run(["git", "status", "--porcelain"])
    if status and status.returncode == 0:
        if status.stdout.strip():
            warn("当前工作区有未提交改动")
        else:
            ok("当前工作区 clean")
    else:
        warn("无法读取 git 工作区状态")


def main() -> int:
    print("ReiLink doctor")
    check_python()
    check_node()
    check_env()
    check_ports()
    check_git()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
