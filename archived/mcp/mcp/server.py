"""MCP server implementation for ATLAS UI control."""

import logging
import httpx
import os
from typing import Any
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

from app.services.ui_state_manager import ui_state_manager
from app.services.scenario_manager import scenario_manager
from app.services.scenario_writer import scenario_writer
from app.services.carla_manager import get_carla_manager
from app.models.ui_state import ViewType, ViewTransition

logger = logging.getLogger(__name__)

# FastAPIサーバーのベースURL
FASTAPI_BASE_URL = os.getenv("FASTAPI_BASE_URL", "http://localhost:8000")

# MCPサーバーインスタンス
app = Server("atlas-mcp-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="change_view",
            description="UI画面を切り替えます。rerun viewer、FiftyOne viewer、シナリオ選択、シナリオ分析などの画面に遷移できます。",
            inputSchema={
                "type": "object",
                "properties": {
                    "view": {
                        "type": "string",
                        "enum": ["home", "scenario_list", "scenario_editor", "scenario_analysis", "rerun_viewer", "fiftyone_viewer", "simulation"],
                        "description": "遷移先の画面"
                    },
                    "scenario_id": {
                        "type": "string",
                        "description": "シナリオID（オプション）"
                    },
                    "rerun_file": {
                        "type": "string",
                        "description": "rerunファイルのパス（オプション）"
                    }
                },
                "required": ["view"]
            }
        ),
        Tool(
            name="get_current_view",
            description="現在のUI状態を取得します。",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="list_scenarios",
            description="すべてのシナリオのリストを取得します。",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_scenario",
            description="特定のシナリオの詳細情報を取得します。",
            inputSchema={
                "type": "object",
                "properties": {
                    "scenario_id": {
                        "type": "string",
                        "description": "取得するシナリオのID"
                    }
                },
                "required": ["scenario_id"]
            }
        ),
        Tool(
            name="create_scenario",
            description="新しいシナリオを作成します。",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "シナリオID"},
                    "name": {"type": "string", "description": "シナリオ名"},
                    "description": {"type": "string", "description": "シナリオの説明"},
                    "carla_config": {"type": "object", "description": "CARLA設定"},
                    "vehicles": {"type": "array", "description": "車両リスト"},
                    "pedestrians": {"type": "array", "description": "歩行者リスト"},
                    "weather": {"type": "object", "description": "天候設定"}
                },
                "required": ["id", "name", "description"]
            }
        ),
        Tool(
            name="update_scenario",
            description="既存のシナリオを更新します。",
            inputSchema={
                "type": "object",
                "properties": {
                    "scenario_id": {"type": "string", "description": "更新するシナリオのID"},
                    "name": {"type": "string", "description": "シナリオ名"},
                    "description": {"type": "string", "description": "シナリオの説明"},
                    "carla_config": {"type": "object", "description": "CARLA設定"},
                    "vehicles": {"type": "array", "description": "車両リスト"},
                    "pedestrians": {"type": "array", "description": "歩行者リスト"},
                    "weather": {"type": "object", "description": "天候設定"}
                },
                "required": ["scenario_id"]
            }
        ),
        Tool(
            name="delete_scenario",
            description="シナリオを削除します。",
            inputSchema={
                "type": "object",
                "properties": {
                    "scenario_id": {
                        "type": "string",
                        "description": "削除するシナリオのID"
                    }
                },
                "required": ["scenario_id"]
            }
        ),
        Tool(
            name="generate_abstract_scenario",
            description="ユーザーの自然言語要件から抽象シナリオを生成します。",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "ユーザーの自然言語要件"
                    }
                },
                "required": ["prompt"]
            }
        ),
        Tool(
            name="generate_logical_scenario",
            description="抽象シナリオから論理シナリオ（OpenDRIVE非依存）を生成します。",
            inputSchema={
                "type": "object",
                "properties": {
                    "abstract_scenario": {
                        "type": "object",
                        "description": "抽象シナリオのJSON表現"
                    }
                },
                "required": ["abstract_scenario"]
            }
        ),
        Tool(
            name="generate_concrete_scenario",
            description="論理シナリオから具体シナリオとJSONパラメータを生成します。",
            inputSchema={
                "type": "object",
                "properties": {
                    "logical_scenario": {
                        "type": "object",
                        "description": "論理シナリオのJSON表現"
                    },
                    "carla_map": {
                        "type": "string",
                        "description": "CARLAマップ名（デフォルト: Town04）"
                    }
                },
                "required": ["logical_scenario"]
            }
        ),
        Tool(
            name="launch_scenario_with_retry",
            description="C++コードをビルド・実行します（自動リトライ機能付き）。",
            inputSchema={
                "type": "object",
                "properties": {
                    "cpp_code": {
                        "type": "string",
                        "description": "C++ソースコード"
                    },
                    "config_json": {
                        "type": "string",
                        "description": "JSONパラメータ"
                    },
                    "scenario_uuid": {
                        "type": "string",
                        "description": "シナリオUUID"
                    },
                    "max_retries": {
                        "type": "integer",
                        "description": "最大リトライ回数（デフォルト: 5）",
                        "default": 5
                    }
                },
                "required": ["cpp_code", "config_json", "scenario_uuid"]
            }
        ),
        Tool(
            name="save_scenario_trace",
            description="シナリオのトレース情報をJSONファイルに保存します。",
            inputSchema={
                "type": "object",
                "properties": {
                    "trace": {
                        "type": "object",
                        "description": "ScenarioTraceのJSON表現"
                    }
                },
                "required": ["trace"]
            }
        ),
        Tool(
            name="launch_carla",
            description="CARLAサーバーを起動します。",
            inputSchema={
                "type": "object",
                "properties": {
                    "port": {
                        "type": "integer",
                        "description": "ポート番号（オプション、デフォルトは設定から取得）"
                    },
                    "map_name": {
                        "type": "string",
                        "description": "マップ名（オプション、デフォルトは設定から取得）"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="stop_carla",
            description="CARLAサーバーを停止します。",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_carla_status",
            description="CARLAサーバーの状態を取得します。",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="save_carla_settings",
            description="CARLA設定を保存します。",
            inputSchema={
                "type": "object",
                "properties": {
                    "settings": {
                        "type": "object",
                        "description": "保存するCARLA設定"
                    }
                },
                "required": ["settings"]
            }
        ),
        Tool(
            name="get_carla_settings",
            description="現在のCARLA設定を取得します。",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "change_view":
            view_type = ViewType(arguments["view"])

            # FastAPI経由でUI状態を更新（WebSocketで通知される）
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.post(
                        f"{FASTAPI_BASE_URL}/mcp/change-view",
                        params={
                            "view": view_type.value,
                            "scenario_id": arguments.get("scenario_id"),
                            "rerun_file": arguments.get("rerun_file")
                        }
                    )
                    response.raise_for_status()
                    result = response.json()

                    return [TextContent(
                        type="text",
                        text=f"画面を {view_type.value} に切り替えました。\n現在の状態: {result['state']}"
                    )]
                except httpx.HTTPError as e:
                    logger.error(f"Failed to change view via FastAPI: {e}")
                    # フォールバック: ローカルで状態を変更
                    transition = ViewTransition(
                        target_view=view_type,
                        scenario_id=arguments.get("scenario_id"),
                        rerun_file=arguments.get("rerun_file")
                    )
                    new_state = await ui_state_manager.transition_to_view(transition)
                    return [TextContent(
                        type="text",
                        text=f"画面を {view_type.value} に切り替えました（ローカル）。\n現在の状態: {new_state.model_dump_json(indent=2)}"
                    )]

        elif name == "get_current_view":
            state = ui_state_manager.current_state
            return [TextContent(
                type="text",
                text=f"現在のUI状態:\n{state.model_dump_json(indent=2)}"
            )]

        elif name == "list_scenarios":
            scenarios = scenario_manager.list_scenarios()
            return [TextContent(
                type="text",
                text=f"シナリオリスト ({len(scenarios)}件):\n" +
                     "\n".join([f"- {s.id}: {s.name}" for s in scenarios])
            )]

        elif name == "get_scenario":
            scenario = scenario_manager.get_scenario(arguments["scenario_id"])
            if not scenario:
                return [TextContent(
                    type="text",
                    text=f"シナリオ {arguments['scenario_id']} が見つかりません。"
                )]
            return [TextContent(
                type="text",
                text=f"シナリオ詳細:\n{scenario.model_dump_json(indent=2)}"
            )]

        elif name == "create_scenario":
            from app.models.scenario import Scenario
            scenario = Scenario(**arguments)
            created = scenario_manager.create_scenario(scenario)
            return [TextContent(
                type="text",
                text=f"シナリオを作成しました:\n{created.model_dump_json(indent=2)}"
            )]

        elif name == "update_scenario":
            scenario_id = arguments.pop("scenario_id")
            updated = scenario_manager.update_scenario(scenario_id, **arguments)
            if not updated:
                return [TextContent(
                    type="text",
                    text=f"シナリオ {scenario_id} が見つかりません。"
                )]
            return [TextContent(
                type="text",
                text=f"シナリオを更新しました:\n{updated.model_dump_json(indent=2)}"
            )]

        elif name == "delete_scenario":
            success = scenario_manager.delete_scenario(arguments["scenario_id"])
            if success:
                return [TextContent(
                    type="text",
                    text=f"シナリオ {arguments['scenario_id']} を削除しました。"
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"シナリオ {arguments['scenario_id']} が見つかりません。"
                )]

        elif name == "generate_abstract_scenario":
            from app.models.scenario_trace import AbstractScenario
            abstract = scenario_writer.generate_abstract_scenario(arguments["prompt"])
            return [TextContent(
                type="text",
                text=f"抽象シナリオを生成しました:\n{abstract.model_dump_json(indent=2)}"
            )]

        elif name == "generate_logical_scenario":
            from app.models.scenario_trace import AbstractScenario, LogicalScenario
            abstract = AbstractScenario(**arguments["abstract_scenario"])
            logical = scenario_writer.generate_logical_scenario(abstract)
            return [TextContent(
                type="text",
                text=f"論理シナリオを生成しました:\n{logical.model_dump_json(indent=2)}"
            )]

        elif name == "generate_concrete_scenario":
            from app.models.scenario_trace import LogicalScenario
            logical = LogicalScenario(**arguments["logical_scenario"])
            carla_map = arguments.get("carla_map", "Town04")
            concrete, json_str = scenario_writer.generate_concrete_scenario(logical, carla_map)
            return [TextContent(
                type="text",
                text=f"具体シナリオを生成しました:\n\nシナリオ:\n{concrete.model_dump_json(indent=2)}\n\nJSONパラメータ:\n{json_str}"
            )]

        elif name == "launch_scenario_with_retry":
            result = scenario_writer.launch_with_retry(
                cpp_code=arguments["cpp_code"],
                config_json=arguments["config_json"],
                scenario_uuid=arguments["scenario_uuid"],
                max_retries=arguments.get("max_retries", 5)
            )
            if result["success"]:
                logs = result.get("logs", "No logs available")
                return [TextContent(
                    type="text",
                    text=f"ビルド・実行に成功しました（試行回数: {result['attempt']}）\n\n"
                         f"UUID: {result['uuid']}\n"
                         f"RRD file: {result.get('rrd_file', 'N/A')}\n"
                         f"MP4 file: {result.get('mp4_file', 'N/A')}\n\n"
                         f"ログ:\n{logs[:2000]}..."
                )]
            else:
                error_summary = "\n".join([
                    f"試行{e['attempt']}: {e['error']}\n  修正案: {e['fix']}\n  ログ抜粋: {e.get('logs', 'N/A')[:200]}..."
                    for e in result.get("errors", [])
                ])
                logs = result.get("logs", "No logs available")
                return [TextContent(
                    type="text",
                    text=f"ビルド・実行に失敗しました（最大試行回数: {result['attempt']}）\n\n"
                         f"エラー履歴:\n{error_summary}\n\n"
                         f"最終ログ:\n{logs[:1000]}..."
                )]

        elif name == "save_scenario_trace":
            from app.models.scenario_trace import ScenarioTrace
            trace = ScenarioTrace(**arguments["trace"])
            file_path = scenario_writer.save_trace(trace)
            return [TextContent(
                type="text",
                text=f"トレース情報を保存しました: {file_path}"
            )]

        elif name == "launch_carla":
            carla_manager = get_carla_manager()
            result = await carla_manager.launch_carla(
                port=arguments.get("port"),
                map_name=arguments.get("map_name")
            )
            return [TextContent(
                type="text",
                text=f"CARLA起動結果:\n{result}"
            )]

        elif name == "stop_carla":
            carla_manager = get_carla_manager()
            result = carla_manager.stop_carla()
            return [TextContent(
                type="text",
                text=f"CARLA停止結果:\n{result}"
            )]

        elif name == "get_carla_status":
            carla_manager = get_carla_manager()
            status = carla_manager.get_status()
            import json
            return [TextContent(
                type="text",
                text=f"CARLA状態:\n{json.dumps(status, indent=2, ensure_ascii=False)}"
            )]

        elif name == "save_carla_settings":
            carla_manager = get_carla_manager()
            updated = carla_manager.update_settings(arguments["settings"])
            return [TextContent(
                type="text",
                text=f"CARLA設定を保存しました:\n{updated.model_dump_json(indent=2)}"
            )]

        elif name == "get_carla_settings":
            carla_manager = get_carla_manager()
            settings = carla_manager.get_settings()
            return [TextContent(
                type="text",
                text=f"現在のCARLA設定:\n{settings.model_dump_json(indent=2)}"
            )]

        else:
            return [TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]

    except Exception as e:
        logger.error(f"Error calling tool {name}: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
