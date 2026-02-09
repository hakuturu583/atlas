# CARLA Scenarios

このディレクトリには、自動生成されたCARLAシナリオのPython実装が保存されます。

## ファイル命名規則

- **生成されたシナリオ**: `{logical_uuid}.py`
  - 論理シナリオのUUIDがファイル名になります
  - これらのファイルは`.gitignore`で除外されており、Gitで管理されません

## 実行方法

```bash
# パラメータファイルを指定して実行
uv run python scenarios/{logical_uuid}.py --params data/scenarios/params_{parameter_uuid}.json
```

## サンプル

サンプルファイルは `scenarios/examples/` ディレクトリにあります。

- `examples/example_scenario.py` - 基本的なシナリオの例
- `examples/README.md` - サンプルの説明

## シナリオの作成

シナリオの作成は `scripts/scenario_manager.py` を使用してください：

```python
from scripts.scenario_manager import ScenarioManager

manager = ScenarioManager()
abstract_uuid = manager.create_abstract_scenario(...)
logical_uuid = manager.create_logical_scenario(parent_abstract_uuid=abstract_uuid, ...)
parameter_uuid = manager.create_parameters(logical_uuid=logical_uuid, ...)
```

詳細は `scripts/README_scenario_manager.md` を参照してください。
