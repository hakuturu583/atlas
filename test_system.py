#!/usr/bin/env python3
"""システム動作テスト"""

import asyncio
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from app.services.scenario_manager import scenario_manager
from app.services.ui_state_manager import ui_state_manager
from app.models.ui_state import ViewType, ViewTransition


async def test_scenario_manager():
    """シナリオマネージャーのテスト"""
    print("=" * 60)
    print("シナリオマネージャーのテスト")
    print("=" * 60)

    # シナリオ一覧
    scenarios = scenario_manager.list_scenarios()
    print(f"\n✓ シナリオ数: {len(scenarios)}")

    for scenario in scenarios:
        print(f"  - {scenario.id}: {scenario.name}")

    # シナリオ詳細取得
    if scenarios:
        first_scenario = scenario_manager.get_scenario(scenarios[0].id)
        print(f"\n✓ シナリオ詳細取得成功: {first_scenario.name}")
        print(f"  説明: {first_scenario.description}")
        print(f"  車両数: {len(first_scenario.vehicles)}")
        print(f"  歩行者数: {len(first_scenario.pedestrians)}")


async def test_ui_state_manager():
    """UI状態マネージャーのテスト"""
    print("\n" + "=" * 60)
    print("UI状態マネージャーのテスト")
    print("=" * 60)

    # 初期状態
    state = ui_state_manager.current_state
    print(f"\n✓ 初期状態: {state.current_view}")

    # 状態変更通知のテスト
    notifications = []

    async def state_listener(new_state):
        notifications.append(new_state.current_view)

    ui_state_manager.subscribe(state_listener)

    # 画面遷移
    print("\n✓ 画面遷移テスト:")

    for view in [ViewType.SCENARIO_LIST, ViewType.RERUN_VIEWER, ViewType.HOME]:
        transition = ViewTransition(target_view=view)
        new_state = await ui_state_manager.transition_to_view(transition)
        await asyncio.sleep(0.1)  # 通知処理を待つ
        print(f"  → {view.value}: OK")

    # 通知のテスト
    print(f"\n✓ 通知受信数: {len(notifications)}")
    print(f"  受信した画面: {', '.join(notifications)}")

    ui_state_manager.unsubscribe(state_listener)


async def main():
    """メインテスト実行"""
    print("\n🚀 ATLASシステムテスト開始\n")

    try:
        await test_scenario_manager()
        await test_ui_state_manager()

        print("\n" + "=" * 60)
        print("✅ すべてのテストが成功しました！")
        print("=" * 60)
        print("\n次のステップ:")
        print("1. FastAPIサーバーを起動: ./run_dev.sh")
        print("2. ブラウザで http://localhost:8000 を開く")
        print("3. Claude Codeでプラグインを有効化")
        print("4. change_view(view='scenario_list') などのツールを試す")
        print()

    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
