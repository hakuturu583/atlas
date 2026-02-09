---
command: view
description: UI画面を切り替えます
arguments:
  - name: target
    description: 遷移先の画面（home, scenario_list, scenario_editor, scenario_analysis, rerun_viewer, simulation）
    required: true
---

# View切り替えコマンド

UI画面を指定された画面に切り替えます。

## 使用例

```
/view scenario_list
/view rerun_viewer
/view scenario_analysis
```

## 実行

以下のコマンドを実行して画面を切り替えてください：

```bash
# MCPサーバーのchange_viewツールを呼び出す
# 実際の実装ではMCPツールを直接呼び出します
```

画面を {{target}} に切り替えています...
