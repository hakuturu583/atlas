"""View rendering routes."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.services.carla_manager import get_carla_manager

router = APIRouter(prefix="/views", tags=["views"])

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@router.get("/home", response_class=HTMLResponse)
async def home_view(request: Request):
    """ホーム画面"""
    return templates.TemplateResponse("views/home.html", {"request": request})


@router.get("/scenario_list", response_class=HTMLResponse)
async def scenario_list_view(request: Request):
    """シナリオ一覧画面"""
    return templates.TemplateResponse("views/scenario_list.html", {"request": request})


@router.get("/scenario_analysis", response_class=HTMLResponse)
async def scenario_analysis_view(request: Request):
    """シナリオ分析画面"""
    return templates.TemplateResponse("views/scenario_analysis.html", {"request": request})


@router.get("/rerun_viewer", response_class=HTMLResponse)
async def rerun_viewer_view(request: Request):
    """Rerunビューア画面"""
    return templates.TemplateResponse("views/rerun_viewer.html", {"request": request})


@router.get("/carla_settings", response_class=HTMLResponse)
async def carla_settings_view(request: Request):
    """CARLA設定画面"""
    carla_manager = get_carla_manager()
    settings = carla_manager.get_settings()
    carla_status = carla_manager.get_status()
    return templates.TemplateResponse(
        "views/carla_settings.html",
        {
            "request": request,
            "settings": settings,
            "carla_status": carla_status
        }
    )


@router.get("/fiftyone_viewer", response_class=HTMLResponse)
async def fiftyone_viewer_view(request: Request):
    """FiftyOneビューア画面"""
    fiftyone_manager = get_fiftyone_manager()
    fiftyone_url = fiftyone_manager.get_url()
    return templates.TemplateResponse(
        "views/fiftyone_viewer.html",
        {
            "request": request,
            "fiftyone_url": fiftyone_url
        }
    )
