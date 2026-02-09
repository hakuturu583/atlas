#!/usr/bin/env python3
"""
FiftyOne統合スクリプト

CARLAシナリオの実行結果をFiftyOneデータセットに変換し、
ローカルのFiftyOne GUIで可視化・分析できるようにします。
動画からembeddingを計算する機能も含みます。
"""
import fiftyone as fo
import json
from pathlib import Path
import argparse
from typing import Optional, List, Dict, Any
import sys
import re
sys.path.insert(0, str(Path(__file__).parent.parent))
from app.services.embedding_service import EmbeddingService


class CarlaFiftyOneManager:
    """CARLA → FiftyOne データセット変換マネージャー"""

    def __init__(self, dataset_name: str = "carla-scenarios"):
        """
        Args:
            dataset_name: FiftyOneデータセット名
        """
        self.dataset_name = dataset_name

    def load_or_create_dataset(self) -> fo.Dataset:
        """データセットをロードまたは作成"""
        if fo.dataset_exists(self.dataset_name):
            print(f"✓ 既存のデータセットをロード: {self.dataset_name}")
            return fo.load_dataset(self.dataset_name)
        else:
            print(f"✓ 新しいデータセットを作成: {self.dataset_name}")
            return fo.Dataset(self.dataset_name, persistent=True)

    def _extract_pegasus_info(self, abstract_scenario: dict) -> Dict[str, Any]:
        """
        抽象シナリオからPEGASUS 6 Layer情報を抽出

        Args:
            abstract_scenario: 抽象シナリオの辞書

        Returns:
            PEGASUS情報を含む辞書（tags, fields）
        """
        tags = []
        fields = {}

        # Layer 1: Road-level
        if 'pegasus_layer1_road' in abstract_scenario and abstract_scenario['pegasus_layer1_road']:
            layer1 = abstract_scenario['pegasus_layer1_road']
            road_type = layer1.get('road_type')
            if road_type:
                tags.append(f"layer1_road_{road_type}")
                fields['pegasus_road_type'] = road_type

            topology = layer1.get('topology')
            if topology:
                tags.append(f"layer1_topology_{topology}")
                fields['pegasus_topology'] = topology

            num_lanes = layer1.get('num_lanes')
            if num_lanes:
                fields['pegasus_num_lanes'] = num_lanes

        # Layer 2: Traffic Infrastructure
        if 'pegasus_layer2_infrastructure' in abstract_scenario and abstract_scenario['pegasus_layer2_infrastructure']:
            layer2 = abstract_scenario['pegasus_layer2_infrastructure']

            # 信号機
            if 'traffic_lights' in layer2 and layer2['traffic_lights']:
                tags.append("layer2_traffic_light")

            # 交通標識
            if 'traffic_signs' in layer2:
                for sign in layer2['traffic_signs']:
                    sign_type = sign.get('sign_type')
                    if sign_type:
                        tags.append(f"layer2_sign_{sign_type}")

        # Layer 4: Moving Objects
        if 'pegasus_layer4_objects' in abstract_scenario and abstract_scenario['pegasus_layer4_objects']:
            layer4 = abstract_scenario['pegasus_layer4_objects']
            maneuvers = []

            for obj in layer4:
                maneuver = obj.get('maneuver')
                if maneuver and maneuver not in maneuvers:
                    maneuvers.append(maneuver)
                    tags.append(f"layer4_maneuver_{maneuver}")

            if maneuvers:
                fields['pegasus_maneuvers'] = maneuvers

        # Layer 5: Environment Conditions
        if 'pegasus_layer5_environment' in abstract_scenario and abstract_scenario['pegasus_layer5_environment']:
            layer5 = abstract_scenario['pegasus_layer5_environment']

            weather = layer5.get('weather')
            if weather:
                tags.append(f"layer5_weather_{weather}")
                fields['pegasus_weather'] = weather

            time_of_day = layer5.get('time_of_day')
            if time_of_day:
                tags.append(f"layer5_time_{time_of_day}")
                fields['pegasus_time_of_day'] = time_of_day

            road_surface = layer5.get('road_surface')
            if road_surface:
                fields['pegasus_road_surface'] = road_surface

        # Layer 6: Digital Information
        if 'pegasus_layer6_digital' in abstract_scenario and abstract_scenario['pegasus_layer6_digital']:
            layer6 = abstract_scenario['pegasus_layer6_digital']

            v2x_enabled = layer6.get('v2x_enabled', False)
            fields['pegasus_v2x_enabled'] = v2x_enabled
            if v2x_enabled:
                tags.append("layer6_v2x")

        # Criticality Level
        criticality = abstract_scenario.get('pegasus_criticality_level')
        if criticality:
            fields['pegasus_criticality'] = criticality
            tags.append(f"criticality_{criticality}")

        return {'tags': tags, 'fields': fields}

    def add_scenario(
        self,
        dataset: fo.Dataset,
        logical_uuid: str,
        parameter_uuid: str,
        mp4_file: Path,
        metadata: Optional[dict] = None,
        embedding_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        シナリオの実行結果をデータセットに追加

        Args:
            dataset: FiftyOneデータセット
            logical_uuid: 論理シナリオUUID
            parameter_uuid: パラメータUUID
            mp4_file: 動画ファイルのパス
            metadata: 追加のメタデータ
            embedding_data: 動画のembedding情報（オプション）
        """
        if not mp4_file.exists():
            print(f"Error: 動画ファイルが見つかりません: {mp4_file}")
            return

        # 論理シナリオを読み込み（抽象シナリオUUIDを取得）
        logical_file = Path(f"data/scenarios/logical_{logical_uuid}.json")
        abstract_uuid = None
        if logical_file.exists():
            with open(logical_file) as f:
                logical_data = json.load(f)
                abstract_uuid = logical_data.get('parent_abstract_uuid')

        # 抽象シナリオを読み込み（PEGASUS情報取得）
        pegasus_info = {'tags': [], 'fields': {}}
        if abstract_uuid:
            abstract_file = Path(f"data/scenarios/abstract_{abstract_uuid}.json")
            if abstract_file.exists():
                with open(abstract_file) as f:
                    abstract_data = json.load(f)
                    pegasus_info = self._extract_pegasus_info(abstract_data)
                    print(f"  └─ PEGASUS情報を抽出: {len(pegasus_info['tags'])}個のタグ, {len(pegasus_info['fields'])}個のフィールド")

        # パラメータファイルを読み込み
        params_file = Path(f"data/scenarios/logical_{logical_uuid}_parameters.json")
        if params_file.exists():
            with open(params_file) as f:
                params_data = json.load(f)
                params = params_data['parameters'].get(parameter_uuid, {})
        else:
            params = {}

        # サンプルを作成
        sample = fo.Sample(filepath=str(mp4_file.absolute()))

        # メタデータを追加
        sample["logical_uuid"] = logical_uuid
        sample["parameter_uuid"] = parameter_uuid
        if abstract_uuid:
            sample["abstract_uuid"] = abstract_uuid

        # PEGASUS情報を追加
        if pegasus_info['tags']:
            sample.tags = pegasus_info['tags']

        for field_name, field_value in pegasus_info['fields'].items():
            sample[field_name] = field_value

        if params:
            sampled = params.get('sampled_values', {})

            # 車両パラメータ
            if 'ego_vehicle' in sampled:
                sample["initial_speed"] = sampled['ego_vehicle'].get('initial_speed', 0.0)
                sample["distance_to_light"] = sampled['ego_vehicle'].get('distance_to_light', 0.0)

            # シナリオパラメータ
            if 'scenario' in sampled:
                sample["duration"] = sampled['scenario'].get('duration', 0.0)

            # CARLAコンフィグ
            carla_config = params.get('carla_config', {})
            sample["carla_map"] = carla_config.get('map', 'unknown')
            sample["vehicle_type"] = carla_config.get('vehicle_type', 'unknown')

        # 追加のメタデータ
        if metadata:
            for key, value in metadata.items():
                sample[key] = value

        # Embeddingを追加（オプション）
        if embedding_data:
            # embedding_dataは compute_embedding の戻り値
            # data[0]['embedding'] にベクトルが含まれる
            if 'data' in embedding_data and len(embedding_data['data']) > 0:
                embedding_vector = embedding_data['data'][0]['embedding']
                sample["embedding"] = embedding_vector
                sample["embedding_dim"] = len(embedding_vector)
                print(f"  └─ Embedding追加 (dim: {len(embedding_vector)})")

        # データセットに追加
        dataset.add_sample(sample)
        print(f"✓ シナリオをデータセットに追加: {mp4_file.name}")

    def batch_add_scenarios(
        self,
        dataset: fo.Dataset,
        scenarios: List[Dict[str, str]],
        compute_embeddings: bool = True,
        nim_port: int = 8001
    ) -> None:
        """
        複数のシナリオをバッチで追加（embedding計算含む）

        Args:
            dataset: FiftyOneデータセット
            scenarios: シナリオ情報のリスト
                       [{"logical_uuid": "...", "parameter_uuid": "..."}, ...]
            compute_embeddings: embeddingを計算するか
            nim_port: NIMコンテナのポート番号
        """
        if not compute_embeddings:
            # Embeddingなしで追加
            for scenario in scenarios:
                mp4_file = Path(f"data/videos/{scenario['logical_uuid']}_{scenario['parameter_uuid']}.mp4")
                self.add_scenario(
                    dataset=dataset,
                    logical_uuid=scenario['logical_uuid'],
                    parameter_uuid=scenario['parameter_uuid'],
                    mp4_file=mp4_file
                )
            return

        # Embeddingあり: NIMコンテナを起動
        print("\n=== バッチ処理開始（embedding計算あり）===")
        print(f"シナリオ数: {len(scenarios)}")

        embedding_service = EmbeddingService(host_port=nim_port)

        try:
            # NIMコンテナを起動
            print("\n[1/3] NIM Cosmos Embed1コンテナを起動中...")
            embedding_service.start_container()
            print("✓ NIM起動完了")

            # 各シナリオを処理
            print(f"\n[2/3] {len(scenarios)}個の動画からembeddingを計算中...")
            for i, scenario in enumerate(scenarios, 1):
                logical_uuid = scenario['logical_uuid']
                parameter_uuid = scenario['parameter_uuid']
                mp4_file = Path(f"data/videos/{logical_uuid}_{parameter_uuid}.mp4")

                print(f"\n  [{i}/{len(scenarios)}] {mp4_file.name}")

                if not mp4_file.exists():
                    print(f"    ⚠ スキップ: ファイルが存在しません")
                    continue

                try:
                    # Embedding計算
                    print("    → Embedding計算中...")
                    embedding_data = embedding_service.compute_embedding(mp4_file)

                    # 保存
                    print("    → Embedding保存中...")
                    saved_paths = embedding_service.save_embedding(
                        embedding_data,
                        scenario_uuid=f"{logical_uuid}_{parameter_uuid}"
                    )
                    print(f"    ✓ 保存完了: {saved_paths['json']}")

                    # FiftyOneに追加
                    print("    → FiftyOneデータセットに追加中...")
                    self.add_scenario(
                        dataset=dataset,
                        logical_uuid=logical_uuid,
                        parameter_uuid=parameter_uuid,
                        mp4_file=mp4_file,
                        embedding_data=embedding_data
                    )

                except Exception as e:
                    print(f"    ✗ エラー: {e}")
                    # エラーがあってもembeddingなしで追加
                    self.add_scenario(
                        dataset=dataset,
                        logical_uuid=logical_uuid,
                        parameter_uuid=parameter_uuid,
                        mp4_file=mp4_file
                    )

            print(f"\n[3/3] NIMコンテナをシャットダウン中...")
            embedding_service.stop_container()
            print("✓ NIMシャットダウン完了（VRAM解放）")

        except Exception as e:
            print(f"\n✗ バッチ処理エラー: {e}")
            # 必ずコンテナを停止
            try:
                embedding_service.stop_container()
                print("✓ NIMシャットダウン完了（クリーンアップ）")
            except:
                pass
            raise

        print("\n=== バッチ処理完了 ===")

    def launch_app(self, dataset: fo.Dataset, port: int = 5151) -> None:
        """
        FiftyOne GUIをローカルで起動

        Args:
            dataset: FiftyOneデータセット
            port: GUIのポート番号
        """
        # remote=True: ブラウザを自動的に開かない
        session = fo.launch_app(dataset, port=port, remote=True)
        print(f"\n✓ FiftyOne GUI起動: http://localhost:{port}")
        print("  ブラウザでアクセスしてください")
        print("  Ctrl+Cで終了します...")
        session.wait()


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="CARLA→FiftyOne統合")
    parser.add_argument(
        'command',
        choices=['add', 'batch-add', 'launch', 'list', 'clear'],
        help='コマンド (add: シナリオ追加, batch-add: バッチ追加+embedding, launch: GUI起動, list: 一覧, clear: 削除)'
    )
    parser.add_argument('--logical-uuid', help='論理シナリオUUID (addで必須)')
    parser.add_argument('--parameter-uuid', help='パラメータUUID (addで必須)')
    parser.add_argument('--dataset-name', default='carla-scenarios', help='データセット名')
    parser.add_argument('--port', type=int, default=5151, help='GUIポート番号')
    parser.add_argument('--nim-port', type=int, default=8001, help='NIMコンテナのポート番号')
    parser.add_argument('--no-embeddings', action='store_true', help='embeddingを計算しない')
    parser.add_argument('--all-videos', action='store_true', help='data/videos/内のすべての動画を追加')
    args = parser.parse_args()

    manager = CarlaFiftyOneManager(dataset_name=args.dataset_name)

    if args.command == 'add':
        # シナリオを追加
        if not args.logical_uuid or not args.parameter_uuid:
            print("Error: --logical-uuid と --parameter-uuid が必要です")
            return 1

        # MP4ファイルのパスを構築
        mp4_file = Path(f"data/videos/{args.logical_uuid}_{args.parameter_uuid}.mp4")

        dataset = manager.load_or_create_dataset()
        manager.add_scenario(
            dataset=dataset,
            logical_uuid=args.logical_uuid,
            parameter_uuid=args.parameter_uuid,
            mp4_file=mp4_file
        )
        dataset.save()
        print(f"✓ データセット保存完了")

    elif args.command == 'batch-add':
        # バッチでシナリオを追加
        dataset = manager.load_or_create_dataset()

        scenarios = []

        if args.all_videos:
            # data/videos/内のすべての動画を検索
            videos_dir = Path("data/videos")
            if not videos_dir.exists():
                print("Error: data/videos/ ディレクトリが見つかりません")
                return 1

            # UUID正規表現パターン
            uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'

            for mp4_file in videos_dir.glob("*.mp4"):
                # ファイル名から logical_uuid と parameter_uuid を抽出
                # 形式: {logical_uuid}_{parameter_uuid}.mp4
                stem = mp4_file.stem
                uuids = re.findall(uuid_pattern, stem)

                if len(uuids) >= 2:
                    logical_uuid = uuids[0]
                    parameter_uuid = uuids[1]

                    scenarios.append({
                        'logical_uuid': logical_uuid,
                        'parameter_uuid': parameter_uuid
                    })
                    print(f"  検出: {mp4_file.name}")
                else:
                    print(f"  スキップ（UUID不正）: {mp4_file.name}")

            if not scenarios:
                print("Error: data/videos/内に動画ファイルが見つかりません")
                return 1

            print(f"\n合計 {len(scenarios)} 個の動画を検出しました")

        else:
            # 個別指定
            if not args.logical_uuid or not args.parameter_uuid:
                print("Error: --logical-uuid と --parameter-uuid が必要です（または --all-videos を使用）")
                return 1

            scenarios = [{
                'logical_uuid': args.logical_uuid,
                'parameter_uuid': args.parameter_uuid
            }]

        # バッチ処理実行
        compute_embeddings = not args.no_embeddings
        manager.batch_add_scenarios(
            dataset=dataset,
            scenarios=scenarios,
            compute_embeddings=compute_embeddings,
            nim_port=args.nim_port
        )

        dataset.save()
        print(f"\n✓ データセット保存完了")
        print(f"✓ 合計 {len(scenarios)} 個のシナリオを追加しました")

    elif args.command == 'launch':
        # GUIを起動
        dataset = manager.load_or_create_dataset()
        print(f"✓ データセット情報:")
        print(f"  サンプル数: {len(dataset)}")
        print(f"  フィールド: {list(dataset.get_field_schema().keys())}")

        if len(dataset) == 0:
            print("\nℹ️  データセットは空です。シナリオを追加するには 'batch-add' コマンドを使用してください")

        manager.launch_app(dataset, port=args.port)

    elif args.command == 'list':
        # データセット一覧
        datasets = fo.list_datasets()
        print("\n=== FiftyOneデータセット一覧 ===")
        if not datasets:
            print("  データセットがありません")
        else:
            for ds_name in datasets:
                ds = fo.load_dataset(ds_name)
                print(f"\n  {ds_name}:")
                print(f"    サンプル数: {len(ds)}")
                print(f"    フィールド: {list(ds.get_field_schema().keys())}")

    elif args.command == 'clear':
        # データセット削除
        if fo.dataset_exists(args.dataset_name):
            fo.delete_dataset(args.dataset_name)
            print(f"✓ データセット削除完了: {args.dataset_name}")
        else:
            print(f"Warning: データセットが存在しません: {args.dataset_name}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
