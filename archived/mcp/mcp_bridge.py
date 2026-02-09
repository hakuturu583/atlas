"""MCP bridge router - MCPサーバーとWebUIの橋渡し"""

from fastapi import APIRouter, HTTPException
from app.services.ui_state_manager import ui_state_manager
from app.models.ui_state import ViewType, ViewTransition

router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.post("/change-view")
async def change_view(view: str, scenario_id: str = None, rerun_file: str = None):
    """MCPサーバーから呼び出される画面遷移エンドポイント"""
    try:
        view_type = ViewType(view)
        transition = ViewTransition(
            target_view=view_type,
            scenario_id=scenario_id,
            rerun_file=rerun_file
        )

        new_state = await ui_state_manager.transition_to_view(transition)

        return {
            "success": True,
            "state": new_state.model_dump()
        }

    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid view type: {view}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/state")
async def get_state():
    """現在のUI状態を取得"""
    return ui_state_manager.current_state.model_dump()


@router.post("/update-state")
async def update_state(updates: dict):
    """UI状態を部分更新"""
    try:
        new_state = await ui_state_manager.update_state(**updates)
        return {
            "success": True,
            "state": new_state.model_dump()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
