"""WebSocket routes for terminal communication."""

import asyncio
import json
import os
import pty
import fcntl
import struct
import termios
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

# アクティブな接続を管理
active_connections: Set[WebSocket] = set()


class TerminalManager:
    """ターミナルセッション管理"""

    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}
        self.processes: Dict[str, tuple] = {}  # (process, fd_master)

    async def connect(self, websocket: WebSocket, session_id: str):
        """クライアントを接続"""
        logger.info(f"Accepting WebSocket connection for {session_id}")
        await websocket.accept()
        self.connections[session_id] = websocket
        active_connections.add(websocket)
        logger.info(f"WebSocket accepted for {session_id}")

        # 作業ディレクトリを設定（atlasワークスペース）
        workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))

        # .claudeディレクトリの存在を確認
        claude_dir = os.path.join(workspace_dir, '.claude')
        has_claude_config = os.path.isdir(claude_dir)

        # プラグインとMCP設定の確認
        plugin_dir = os.path.join(claude_dir, 'atlas-plugin')
        has_plugin = os.path.isdir(plugin_dir)
        settings_file = os.path.join(claude_dir, 'settings.local.json')
        has_settings = os.path.isfile(settings_file)

        # スキルファイルの確認
        skills_dir = os.path.join(plugin_dir, 'skills')
        skills = []
        if os.path.isdir(skills_dir):
            for skill_file in os.listdir(skills_dir):
                if skill_file.endswith('.md'):
                    skills.append(skill_file.replace('.md', ''))

        # ウェルカムメッセージを送信
        welcome_msg = "\x1b[1;36m=== Claude Code Terminal ===\x1b[0m\r\n"
        welcome_msg += "\x1b[32mConnected successfully!\x1b[0m\r\n"
        welcome_msg += f"\x1b[33mWorking directory: {workspace_dir}\x1b[0m\r\n"
        welcome_msg += "\r\n"

        if has_claude_config:
            welcome_msg += "\x1b[1;32m✓ .claude directory detected\x1b[0m\r\n"
            if has_plugin:
                welcome_msg += "\x1b[1;32m✓ atlas-plugin will be loaded\x1b[0m\r\n"
                if skills:
                    welcome_msg += "\x1b[1;36m  Skills available:\x1b[0m\r\n"
                    for skill in skills:
                        welcome_msg += f"\x1b[36m    - {skill}\x1b[0m\r\n"
            if has_settings:
                welcome_msg += "\x1b[1;32m✓ settings.local.json will be applied\x1b[0m\r\n"
        else:
            welcome_msg += "\x1b[33m⚠ No .claude directory found\x1b[0m\r\n"

        welcome_msg += "\r\n"
        welcome_msg += "\x1b[33mStarting Claude Code...\x1b[0m\r\n"
        welcome_msg += "\r\n"
        await websocket.send_text(welcome_msg)
        logger.info(f"Welcome message sent to {session_id}")
        logger.info(f"Claude config check - dir:{has_claude_config}, plugin:{has_plugin}, settings:{has_settings}, skills:{skills}")

        # PTYを使ってClaude Codeを起動
        try:
            # PTYペアを作成
            fd_master, fd_slave = pty.openpty()

            # ターミナルサイズを設定（デフォルト値）
            winsize = struct.pack('HHHH', 24, 80, 0, 0)
            fcntl.ioctl(fd_master, termios.TIOCSWINSZ, winsize)

            # 環境変数を設定
            env = dict(os.environ)
            env['PWD'] = workspace_dir  # 現在の作業ディレクトリを明示的に設定
            env['CLAUDE_PROJECT_DIR'] = workspace_dir  # Claude Codeにプロジェクトディレクトリを通知

            # Claude Codeプロセスを起動
            process = await asyncio.create_subprocess_exec(
                'claude',
                stdin=fd_slave,
                stdout=fd_slave,
                stderr=fd_slave,
                cwd=workspace_dir,  # 作業ディレクトリを指定
                env=env,
                preexec_fn=os.setsid
            )

            logger.info(f"Claude Code started in: {workspace_dir}")

            # スレーブ側は子プロセスで使用されるのでクローズ
            os.close(fd_slave)

            self.processes[session_id] = (process, fd_master)
            logger.info(f"Claude Code process started for {session_id} in {workspace_dir}")

            # 出力を読み取ってクライアントに送信
            asyncio.create_task(self._read_pty_output(session_id, fd_master, websocket))
        except Exception as e:
            logger.error(f"Failed to start Claude Code process for {session_id}: {e}")
            await websocket.send_text(f"\x1b[31mError starting Claude Code: {e}\x1b[0m\r\n")

    async def disconnect(self, session_id: str):
        """クライアントを切断"""
        logger.info(f"Disconnecting session: {session_id}")

        if session_id in self.connections:
            ws = self.connections[session_id]
            try:
                if ws in active_connections:
                    active_connections.remove(ws)
            except (ValueError, KeyError):
                logger.debug(f"WebSocket for {session_id} already removed from active connections")

            try:
                del self.connections[session_id]
                logger.debug(f"Removed WebSocket connection for {session_id}")
            except KeyError:
                logger.debug(f"Connection {session_id} already removed")

        if session_id in self.processes:
            process, fd_master = self.processes[session_id]
            logger.debug(f"Terminating process for {session_id} (PID: {process.pid}, FD: {fd_master})")
            try:
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=5.0)
                logger.debug(f"Process terminated gracefully for {session_id}")
            except asyncio.TimeoutError:
                logger.warning(f"Process termination timeout for {session_id}, killing...")
                process.kill()
                await process.wait()
                logger.debug(f"Process killed for {session_id}")
            finally:
                # Close file descriptor if still valid
                try:
                    os.close(fd_master)
                    logger.debug(f"Closed FD {fd_master} for {session_id}")
                except OSError as e:
                    # File descriptor already closed, ignore
                    logger.debug(f"FD {fd_master} already closed for session {session_id}: {e}")

                # Remove from processes dict (may already be removed by another task)
                try:
                    del self.processes[session_id]
                    logger.info(f"Session {session_id} fully disconnected")
                except KeyError:
                    logger.debug(f"Session {session_id} already removed from processes")

    async def send_input(self, session_id: str, data: str):
        """入力をPTYに送信"""
        if session_id in self.processes:
            _, fd_master = self.processes[session_id]
            try:
                os.write(fd_master, data.encode('utf-8'))
            except OSError as e:
                logger.error(f"Error writing to PTY for {session_id}: {e}")

    async def resize_terminal(self, session_id: str, rows: int, cols: int):
        """ターミナルのサイズを変更"""
        if session_id in self.processes:
            _, fd_master = self.processes[session_id]
            try:
                # TIOCSWINSZ: ウィンドウサイズ設定
                winsize = struct.pack('HHHH', rows, cols, 0, 0)
                fcntl.ioctl(fd_master, termios.TIOCSWINSZ, winsize)
                logger.debug(f"Terminal resized for {session_id}: {rows}x{cols}")
            except OSError as e:
                logger.error(f"Error resizing terminal for {session_id}: {e}")

    async def _read_pty_output(self, session_id: str, fd_master: int, websocket: WebSocket):
        """PTYの出力を読み取ってクライアントに送信"""
        loop = asyncio.get_event_loop()
        buffer_size = 4096  # バッファサイズを増やして効率化

        try:
            while session_id in self.processes:
                # ファイルディスクリプタから非同期的に読み取り
                data = await loop.run_in_executor(None, os.read, fd_master, buffer_size)
                if not data:
                    logger.debug(f"PTY output stream ended for {session_id}")
                    break

                # UTF-8デコード（エラーは置換）
                text = data.decode('utf-8', errors='replace')

                # WebSocketで送信（エラーハンドリング付き）
                try:
                    await websocket.send_text(text)
                except Exception as send_error:
                    logger.error(f"Failed to send PTY output to {session_id}: {send_error}")
                    break

                # 短い待機でCPU使用率を下げる
                await asyncio.sleep(0.001)

        except OSError as e:
            logger.error(f"Error reading PTY output for session {session_id}: {e}")
        except Exception as e:
            logger.error(f"Error in PTY output reader for session {session_id}: {e}")
        finally:
            logger.info(f"PTY output reader stopped for {session_id}")
            await self.disconnect(session_id)


terminal_manager = TerminalManager()


@router.websocket("/ws/terminal")
async def terminal_websocket(websocket: WebSocket):
    """ターミナルWebSocket接続"""
    logger.info("Terminal WebSocket connection attempt")
    session_id = f"session_{id(websocket)}"

    try:
        logger.info(f"Connecting terminal session: {session_id}")
        await terminal_manager.connect(websocket, session_id)
        logger.info(f"Terminal session connected: {session_id}")

        while True:
            message = await websocket.receive_text()
            try:
                data = json.loads(message)
                msg_type = data.get('type')

                if msg_type == 'input':
                    await terminal_manager.send_input(session_id, data.get('data', ''))
                elif msg_type == 'resize':
                    # ターミナルサイズ変更
                    rows = data.get('rows', 24)
                    cols = data.get('cols', 80)
                    await terminal_manager.resize_terminal(session_id, rows, cols)
            except json.JSONDecodeError:
                # JSON以外のメッセージは直接入力として扱う
                await terminal_manager.send_input(session_id, message)

    except WebSocketDisconnect:
        logger.info(f"Terminal session {session_id} disconnected")
    except Exception as e:
        logger.error(f"Terminal error for session {session_id}: {e}")
    finally:
        await terminal_manager.disconnect(session_id)


@router.websocket("/ws/ui-state")
async def ui_state_websocket(websocket: WebSocket):
    """UI状態更新のWebSocket接続"""
    await websocket.accept()
    active_connections.add(websocket)

    from app.services.ui_state_manager import ui_state_manager

    async def state_change_handler(state):
        """状態変更をクライアントに通知"""
        try:
            await websocket.send_json(state.model_dump())
        except Exception as e:
            logger.error(f"Error sending state update: {e}")

    # 購読
    ui_state_manager.subscribe(state_change_handler)

    try:
        # 初期状態を送信
        await websocket.send_json(ui_state_manager.current_state.model_dump())

        # 接続を維持
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        logger.info("UI state WebSocket disconnected")
    except Exception as e:
        logger.error(f"UI state WebSocket error: {e}")
    finally:
        ui_state_manager.unsubscribe(state_change_handler)
        if websocket in active_connections:
            active_connections.remove(websocket)
