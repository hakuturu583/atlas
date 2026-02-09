---
name: scenario-manager
description: This skill should be used when the user asks to "list scenarios", "delete scenario", "edit scenario", "manage scenarios", "show scenario details", "シナリオ一覧", "シナリオ削除", "シナリオ管理". Supports scenario CRUD operations and management tasks.
---

# シナリオ管理スキル

このスキルは、CARLAシナリオの管理を支援します。

## 機能

### シナリオ一覧の表示

MCPサーバーの `list_scenarios` ツールを使用して、すべてのシナリオを表示します。

### シナリオの作成

MCPサーバーの `create_scenario` ツールを使用して、新しいシナリオを作成します。

必要な情報：
- シナリオID
- 名前
- 説明
- CARLA設定（オプション）
- 車両リスト（オプション）
- 歩行者リスト（オプション）
- 天候設定（オプション）

### シナリオの編集

MCPサーバーの `update_scenario` ツールを使用して、既存のシナリオを更新します。

### シナリオの削除

MCPサーバーの `delete_scenario` ツールを使用して、シナリオを削除します。

## 使用例

```
/scenario-manager
> シナリオ一覧を表示

/scenario-manager
> 新しいシナリオを作成

/scenario-manager
> シナリオ「test_scenario_01」を編集
```
