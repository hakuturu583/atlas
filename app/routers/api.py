"""API endpoints."""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse, HTMLResponse
from typing import List, Optional
import aiofiles
from pathlib import Path

from app.services.scenario_manager import scenario_manager
from app.services.carla_manager import get_carla_manager
from app.models.scenario import Scenario, ScenarioListItem
from app.models.carla_settings import CarlaSettings
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/scenarios", response_model=List[ScenarioListItem])
async def list_scenarios():
    """シナリオ一覧を取得"""
    scenarios = scenario_manager.list_scenarios()
    return scenarios


@router.get("/scenarios/count")
async def scenarios_count():
    """シナリオ数を取得"""
    count = len(scenario_manager.list_scenarios())
    return f"{count}件のシナリオ"


@router.get("/scenarios/graph")
async def get_scenario_graph():
    """シナリオの階層構造をグラフ形式で取得（Cytoscape.js用）"""
    import json
    from pathlib import Path

    scenarios_dir = Path("data/scenarios")

    nodes = []
    edges = []
    node_ids = set()

    # 抽象シナリオを読み込み
    for abstract_file in scenarios_dir.glob("abstract_*.json"):
        try:
            with open(abstract_file) as f:
                data = json.load(f)
                abstract_uuid = data.get("uuid")

                if not abstract_uuid or abstract_uuid in node_ids:
                    continue

                node_ids.add(abstract_uuid)
                nodes.append({
                    "data": {
                        "id": abstract_uuid,
                        "label": data.get("name", "抽象シナリオ"),
                        "type": "abstract",
                        "description": data.get("description", ""),
                        "created_at": data.get("created_at", "")
                    }
                })
        except Exception as e:
            print(f"Error loading abstract scenario {abstract_file}: {e}")

    # 論理シナリオを読み込み
    for logical_file in scenarios_dir.glob("logical_*.json"):
        # パラメータファイルはスキップ
        if "_parameters" in logical_file.name:
            continue

        try:
            with open(logical_file) as f:
                data = json.load(f)
                logical_uuid = data.get("uuid")
                parent_uuid = data.get("parent_abstract_uuid")

                if not logical_uuid or logical_uuid in node_ids:
                    continue

                node_ids.add(logical_uuid)
                nodes.append({
                    "data": {
                        "id": logical_uuid,
                        "label": data.get("name", "論理シナリオ"),
                        "type": "logical",
                        "description": data.get("description", ""),
                        "created_at": data.get("created_at", "")
                    }
                })

                # 親へのエッジを追加
                if parent_uuid and parent_uuid in node_ids:
                    edges.append({
                        "data": {
                            "id": f"{parent_uuid}-{logical_uuid}",
                            "source": parent_uuid,
                            "target": logical_uuid
                        }
                    })
        except Exception as e:
            print(f"Error loading logical scenario {logical_file}: {e}")

    # パラメータセットを読み込み
    for params_file in scenarios_dir.glob("logical_*_parameters.json"):
        try:
            with open(params_file) as f:
                data = json.load(f)
                logical_uuid = data.get("logical_uuid")

                if not logical_uuid:
                    continue

                # 各パラメータセットをノードとして追加
                for param_uuid, param_data in data.get("parameters", {}).items():
                    node_id = f"param_{param_uuid}"

                    if node_id in node_ids:
                        continue

                    node_ids.add(node_id)

                    # パラメータの要約を作成
                    sampled = param_data.get("sampled_values", {})
                    summary = []
                    if "ego_vehicle" in sampled:
                        if "initial_speed" in sampled["ego_vehicle"]:
                            summary.append(f"速度: {sampled['ego_vehicle']['initial_speed']:.1f} km/h")
                        if "distance_to_light" in sampled["ego_vehicle"]:
                            summary.append(f"距離: {sampled['ego_vehicle']['distance_to_light']:.1f} m")

                    summary_text = ", ".join(summary) if summary else "パラメータセット"

                    nodes.append({
                        "data": {
                            "id": node_id,
                            "label": summary_text,
                            "type": "parameter",
                            "parameter_uuid": param_uuid,
                            "logical_uuid": logical_uuid,
                            "video_file": param_data.get("output", {}).get("mp4_file", ""),
                            "created_at": param_data.get("created_at", "")
                        }
                    })

                    # 論理シナリオへのエッジを追加
                    if logical_uuid in node_ids:
                        edges.append({
                            "data": {
                                "id": f"{logical_uuid}-{node_id}",
                                "source": logical_uuid,
                                "target": node_id
                            }
                        })
        except Exception as e:
            print(f"Error loading parameters {params_file}: {e}")

    return {
        "elements": {
            "nodes": nodes,
            "edges": edges
        },
        "stats": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "abstract_count": sum(1 for n in nodes if n["data"]["type"] == "abstract"),
            "logical_count": sum(1 for n in nodes if n["data"]["type"] == "logical"),
            "parameter_count": sum(1 for n in nodes if n["data"]["type"] == "parameter")
        }
    }


@router.get("/scenarios/{scenario_id}", response_model=Scenario)
async def get_scenario(scenario_id: str):
    """シナリオ詳細を取得"""
    scenario = scenario_manager.get_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


@router.post("/scenarios", response_model=Scenario, status_code=201)
async def create_scenario(scenario: Scenario):
    """シナリオを作成"""
    created = scenario_manager.create_scenario(scenario)
    return created


@router.put("/scenarios/{scenario_id}", response_model=Scenario)
async def update_scenario(scenario_id: str, updates: dict):
    """シナリオを更新"""
    updated = scenario_manager.update_scenario(scenario_id, **updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return updated


@router.delete("/scenarios/{scenario_id}", status_code=204)
async def delete_scenario(scenario_id: str):
    """シナリオを削除"""
    success = scenario_manager.delete_scenario(scenario_id)
    if not success:
        raise HTTPException(status_code=404, detail="Scenario not found")


@router.get("/scenarios/{scenario_id}/analysis")
async def get_scenario_analysis(scenario_id: str):
    """シナリオの分析結果を取得"""
    scenario = scenario_manager.get_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    return {
        "scenario_id": scenario_id,
        "name": scenario.name,
        "metrics": scenario.metrics,
        "last_run": scenario.last_run_at
    }


# Rerun関連のエンドポイント
@router.get("/rerun/files")
async def list_rerun_files():
    """利用可能なRRDファイルのリストを取得"""
    rerun_dir = Path("data/rerun")
    rerun_dir.mkdir(parents=True, exist_ok=True)

    files = []
    for rrd_file in rerun_dir.glob("*.rrd"):
        files.append({
            "name": rrd_file.name,
            "path": str(rrd_file),
            "size": rrd_file.stat().st_size
        })

    return files


@router.post("/rerun/upload")
async def upload_rerun_file(file: UploadFile = File(...)):
    """RRDファイルをアップロード"""
    if not file.filename.endswith('.rrd'):
        raise HTTPException(status_code=400, detail="Only .rrd files are allowed")

    rerun_dir = Path("data/rerun")
    rerun_dir.mkdir(parents=True, exist_ok=True)

    file_path = rerun_dir / file.filename

    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)

    return {
        "filename": file.filename,
        "file_path": str(file_path),
        "size": len(content)
    }


# CARLA管理のエンドポイント
@router.post("/carla/launch")
async def launch_carla(port: Optional[int] = None, map_name: Optional[str] = None):
    """CARLAサーバーを起動"""
    carla_manager = get_carla_manager()
    result = await carla_manager.launch_carla(port=port, map_name=map_name)

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])

    # 状態表示HTMLを返す
    status = carla_manager.get_status()
    return HTMLResponse(content=_render_status_html(status))


@router.post("/carla/stop", response_class=HTMLResponse)
async def stop_carla():
    """CARLAサーバーを停止"""
    carla_manager = get_carla_manager()
    result = carla_manager.stop_carla()

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])

    # 状態表示HTMLを返す
    status = carla_manager.get_status()
    return HTMLResponse(content=_render_status_html(status))


@router.get("/carla/status")
async def get_carla_status():
    """CARLAサーバーの状態を取得"""
    carla_manager = get_carla_manager()
    return carla_manager.get_status()


@router.post("/carla/settings", response_class=HTMLResponse)
async def save_carla_settings(
    carla_path: str = Form(...),
    executable_name: str = Form(...),
    default_port: int = Form(...),
    default_map: str = Form(...),
    quality_level: str = Form(...),
    additional_args: str = Form(""),
    timeout: int = Form(...),
    auto_start: Optional[str] = Form(None)
):
    """CARLA設定を保存（フォームデータ）"""
    import logging
    logger = logging.getLogger(__name__)

    # チェックボックスの値をboolに変換（チェックされていれば値が送信される）
    auto_start_bool = auto_start is not None

    logger.info(f"Received settings: carla_path={carla_path}, executable_name={executable_name}, "
                f"default_port={default_port}, default_map={default_map}, quality_level={quality_level}, "
                f"additional_args='{additional_args}', timeout={timeout}, auto_start={auto_start_bool}")

    carla_manager = get_carla_manager()

    settings_dict = {
        "carla_path": carla_path,
        "executable_name": executable_name,
        "default_port": default_port,
        "default_map": default_map,
        "quality_level": quality_level,
        "additional_args": additional_args,
        "timeout": timeout,
        "auto_start": auto_start_bool
    }

    try:
        updated = carla_manager.update_settings(settings_dict)
        return HTMLResponse(
            content='<div class="p-4 mb-4 text-green-700 bg-green-100 rounded-lg">'
                    '✓ 設定を保存しました</div>'
        )
    except Exception as e:
        return HTMLResponse(
            content=f'<div class="p-4 mb-4 text-red-700 bg-red-100 rounded-lg">'
                    f'✗ エラー: {str(e)}</div>',
            status_code=400
        )


@router.get("/carla/settings", response_model=CarlaSettings)
async def get_carla_settings():
    """CARLA設定を取得"""
    carla_manager = get_carla_manager()
    return carla_manager.get_settings()


def _render_status_html(status: dict) -> str:
    """CARLA状態のHTMLを生成"""
    running = status["running"]
    pid = status.get("pid")

    html = f'''
    <div class="bg-white shadow rounded-lg p-6 mb-6" id="carla-status">
        <h2 class="text-xl font-semibold text-gray-900 mb-4">サーバー状態</h2>
        <div class="flex items-center justify-between">
            <div>
                <span class="text-sm text-gray-600">ステータス:</span>
                <span class="ml-2 px-3 py-1 rounded-full text-sm font-medium
                    {'bg-green-100 text-green-800' if running else 'bg-gray-100 text-gray-800'}">
                    {'実行中' if running else '停止中'}
                </span>
    '''

    if pid:
        html += f'<span class="ml-2 text-sm text-gray-500">(PID: {pid})</span>'

    html += '''
            </div>
            <div class="space-x-2">
    '''

    if running:
        html += '''
                <button
                    hx-post="/api/carla/stop"
                    hx-target="#carla-status"
                    hx-swap="outerHTML"
                    class="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500">
                    停止
                </button>
        '''
    else:
        html += '''
                <button
                    hx-post="/api/carla/launch"
                    hx-target="#carla-status"
                    hx-swap="outerHTML"
                    class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500">
                    起動
                </button>
        '''

    html += '''
            </div>
        </div>
    '''

    if running and status.get("memory_mb"):
        html += f'''
        <div class="mt-4 grid grid-cols-2 gap-4 text-sm">
            <div>
                <span class="text-gray-600">メモリ使用量:</span>
                <span class="ml-2 font-medium">{status['memory_mb']:.1f} MB</span>
            </div>
            <div>
                <span class="text-gray-600">CPU使用率:</span>
                <span class="ml-2 font-medium">{status.get('cpu_percent', 0):.1f}%</span>
            </div>
        </div>
        '''

    html += '''
    </div>
    '''

    return html


# FiftyOne関連のエンドポイント（旧形式 - 削除予定）
# 新しいFiftyOne API は下記を参照


# FiftyOne データセット操作 API
from app.services.fiftyone_manager import fiftyone_manager as fo_manager


@router.get("/fiftyone/stats")
async def get_fiftyone_stats():
    """データセットの統計情報を取得"""
    result = fo_manager.get_stats()
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result.get("error", "Unknown error"))
    return result


@router.get("/fiftyone/samples")
async def list_fiftyone_samples(limit: int = 10):
    """サンプル一覧を取得"""
    result = fo_manager.list_samples(limit=limit)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result.get("error", "Unknown error"))
    return result


