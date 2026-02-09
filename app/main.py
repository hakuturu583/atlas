from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import logging
import atexit

from app.routers import views, api, websocket
from app.services.carla_manager import get_carla_manager
from app.services.sandbox_manager import sandbox_manager

logger = logging.getLogger(__name__)

app = FastAPI(
    title="ATLAS",
    description="Analytic Transparent LAnguage-driven Scenario generator for CARLA",
    version="0.1.0"
)

# 静的ファイルとテンプレートの設定
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# ルーターの登録
app.include_router(views.router)
app.include_router(api.router)
app.include_router(websocket.router)


# アプリケーション起動時の処理
@app.on_event("startup")
async def startup_event():
    """アプリケーション起動時の初期化処理"""
    logger.info("ATLAS application starting up...")

    # CARLA設定を読み込み
    carla_manager = get_carla_manager()
    settings = carla_manager.get_settings()

    logger.info(f"CARLA settings loaded: {settings.carla_path}")

    # 自動起動が有効な場合はCARLAを起動
    if settings.auto_start:
        logger.info("Auto-starting CARLA server...")
        result = await carla_manager.launch_carla()
        if result["success"]:
            logger.info(f"CARLA started successfully (PID: {result['pid']})")
        else:
            logger.warning(f"Failed to auto-start CARLA: {result['message']}")


# アプリケーション終了時の処理
@app.on_event("shutdown")
async def shutdown_event():
    """アプリケーション終了時のクリーンアップ処理"""
    logger.info("ATLAS application shutting down...")

    # 1. すべてのSandboxコンテナを停止
    logger.info("Stopping all sandbox containers...")
    try:
        result = sandbox_manager.stop_all_sandboxes(
            remove_workspaces=False,
            force=True
        )
        if result.returncode == 0:
            logger.info("All sandbox containers stopped successfully")
        else:
            logger.warning(f"Failed to stop some sandbox containers: {result.stderr}")
    except Exception as e:
        logger.error(f"Error stopping sandbox containers: {e}")

    # 2. CARLAサーバーを停止
    logger.info("Stopping CARLA server...")
    try:
        carla_manager = get_carla_manager()
        if carla_manager.is_running():
            result = carla_manager.stop_carla()
            if result["success"]:
                logger.info(f"CARLA stopped successfully (PID: {result['pid']})")
            else:
                logger.warning(f"Failed to stop CARLA: {result['message']}")
        else:
            logger.info("CARLA was not running")
    except Exception as e:
        logger.error(f"Error stopping CARLA: {e}")

    logger.info("ATLAS application shutdown complete")


# atexitハンドラーも登録（プロセス終了時のフォールバック）
def cleanup_on_exit():
    """プロセス終了時のクリーンアップ（フォールバック）"""
    try:
        carla_manager = get_carla_manager()
        if carla_manager.is_running():
            logger.info("atexit: Stopping CARLA server...")
            carla_manager.stop_carla()
    except Exception as e:
        logger.error(f"atexit: Error stopping CARLA: {e}")


atexit.register(cleanup_on_exit)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """メインページ - 2ペインUI"""
    return templates.TemplateResponse(
        "app.html",
        {"request": request, "title": "ATLAS - CARLA Scenario Generator"}
    )


@app.get("/legacy", response_class=HTMLResponse)
async def legacy_index(request: Request):
    """旧インデックスページ"""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "ATLAS - CARLA Scenario Generator"}
    )


@app.get("/health", response_class=HTMLResponse)
async def health_check():
    """ヘルスチェック用エンドポイント - htmx用HTMLフラグメント"""
    return """
    <div class="flex items-center space-x-2">
        <span class="inline-block w-3 h-3 bg-green-500 rounded-full animate-pulse"></span>
        <span class="text-green-700 font-semibold">System Online</span>
    </div>
    """


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
