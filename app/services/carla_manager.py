"""CARLAサーバー管理サービス（シェルスクリプト起動版）"""

import asyncio
import json
import os
import signal
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
import psutil
import socket

from app.models.carla_settings import CarlaSettings


class CarlaManager:
    """CARLAサーバーの起動・停止・状態管理（CarlaUnreal.sh実行）"""

    def __init__(self, settings_path: str = "data/carla_settings.json"):
        self.settings_path = Path(settings_path)
        self.settings: Optional[CarlaSettings] = None
        self.process: Optional[subprocess.Popen] = None
        self._load_settings()

    def _load_settings(self) -> None:
        """設定ファイルから読み込み"""
        if self.settings_path.exists():
            with open(self.settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.settings = CarlaSettings(**data)
        else:
            # デフォルト設定
            self.settings = CarlaSettings()
            self._save_settings()

    def _save_settings(self) -> None:
        """設定ファイルに保存"""
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.settings_path, "w", encoding="utf-8") as f:
            json.dump(self.settings.model_dump(), f, indent=2, ensure_ascii=False)

    def update_settings(self, settings: Dict[str, Any]) -> CarlaSettings:
        """設定を更新

        Args:
            settings: 更新する設定の辞書

        Returns:
            更新後のCarlaSettings
        """
        self.settings = CarlaSettings(**settings)
        self._save_settings()
        return self.settings

    def get_settings(self) -> CarlaSettings:
        """現在の設定を取得"""
        if self.settings is None:
            self._load_settings()
        return self.settings

    async def launch_carla(
        self,
        port: Optional[int] = None,
        map_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """CARLAサーバーを起動（CarlaUnreal.sh実行）

        Args:
            port: ポート番号（Noneの場合は設定から取得）
            map_name: マップ名（Noneの場合は設定から取得）

        Returns:
            起動結果の辞書
        """
        if self.is_running():
            return {
                "success": False,
                "message": "CARLAは既に起動しています",
                "pid": self.process.pid if self.process else None
            }

        # 実行ファイルの存在確認
        executable_path = self.settings.get_executable_path()
        if not os.path.exists(executable_path):
            return {
                "success": False,
                "message": f"CARLA実行ファイルが見つかりません: {executable_path}",
                "error": "FileNotFoundError"
            }

        # 起動コマンドを生成
        cmd = self.settings.get_launch_command(port=port, map_name=map_name)

        try:
            # プロセスを起動
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
                cwd=self.settings.carla_path  # CARLAディレクトリで実行
            )

            # 起動を待機（ポートが開くまで待つ）
            actual_port = port or self.settings.default_port
            if await self._wait_for_port(
                host="localhost",
                port=actual_port,
                timeout=self.settings.timeout
            ):
                return {
                    "success": True,
                    "message": f"CARLAを起動しました (PID: {self.process.pid})",
                    "pid": self.process.pid,
                    "host": "localhost",
                    "port": actual_port,
                    "command": " ".join(cmd)
                }
            else:
                # タイムアウト
                self.stop_carla()
                return {
                    "success": False,
                    "message": f"CARLAの起動がタイムアウトしました ({self.settings.timeout}秒)",
                    "error": "TimeoutError"
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"CARLA起動中にエラーが発生しました: {str(e)}",
                "error": type(e).__name__
            }

    async def _wait_for_port(
        self,
        host: str,
        port: int,
        timeout: int
    ) -> bool:
        """CARLAサーバーが起動するまで待機（ポート接続チェック）

        Args:
            host: ホスト
            port: ポート
            timeout: タイムアウト（秒）

        Returns:
            起動成功したらTrue
        """
        import time
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # ソケット接続をテスト
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((host, port))
                sock.close()

                if result == 0:
                    # ポートが開いた
                    return True
            except Exception:
                pass

            # プロセスが死んでいないか確認
            if self.process and self.process.poll() is not None:
                # プロセスが終了した
                return False

            await asyncio.sleep(2)

        return False

    def stop_carla(self) -> Dict[str, Any]:
        """CARLAサーバーを停止

        Returns:
            停止結果の辞書
        """
        if not self.is_running():
            return {
                "success": False,
                "message": "CARLAは実行されていません"
            }

        try:
            pid = self.process.pid

            # プロセスグループ全体を終了
            os.killpg(os.getpgid(pid), signal.SIGTERM)

            # 終了を待機（最大10秒）
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                # 強制終了
                os.killpg(os.getpgid(pid), signal.SIGKILL)
                self.process.wait()

            self.process = None

            return {
                "success": True,
                "message": f"CARLAを停止しました (PID: {pid})",
                "pid": pid
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"CARLA停止中にエラーが発生しました: {str(e)}",
                "error": type(e).__name__
            }

    def is_running(self) -> bool:
        """CARLAが実行中かどうか

        Returns:
            実行中ならTrue
        """
        if self.process is None:
            return False

        # プロセスが生存しているか確認
        if self.process.poll() is None:
            return True
        else:
            self.process = None
            return False

    def get_status(self) -> Dict[str, Any]:
        """CARLAサーバーの状態を取得

        Returns:
            状態情報の辞書
        """
        running = self.is_running()
        pid = self.process.pid if running else None

        status = {
            "running": running,
            "pid": pid,
            "host": "localhost",
            "port": self.settings.default_port,
            "settings": self.settings.model_dump()
        }

        # プロセス情報を追加
        if running and pid:
            try:
                proc = psutil.Process(pid)
                status["memory_mb"] = proc.memory_info().rss / (1024 * 1024)
                status["cpu_percent"] = proc.cpu_percent(interval=0.1)
                status["create_time"] = proc.create_time()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        return status


# シングルトンインスタンス
_carla_manager: Optional[CarlaManager] = None


def get_carla_manager() -> CarlaManager:
    """グローバルなCarlaManagerインスタンスを取得"""
    global _carla_manager
    if _carla_manager is None:
        _carla_manager = CarlaManager()
    return _carla_manager
