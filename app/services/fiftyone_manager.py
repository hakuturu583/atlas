"""FiftyOne dataset management service."""

import fiftyone as fo
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class FiftyOneManager:
    """FiftyOneデータセットの管理とAPI制御"""

    def __init__(self, dataset_name: str = "carla-scenarios"):
        self.dataset_name = dataset_name
        self._dataset: Optional[fo.Dataset] = None

    def get_dataset(self) -> Optional[fo.Dataset]:
        """データセットを取得（存在しない場合はNone）"""
        try:
            if self._dataset is None:
                if fo.dataset_exists(self.dataset_name):
                    self._dataset = fo.load_dataset(self.dataset_name)
                    logger.info(f"Dataset loaded: {self.dataset_name}")
                else:
                    logger.warning(f"Dataset does not exist: {self.dataset_name}")
                    return None
            return self._dataset
        except Exception as e:
            logger.error(f"Failed to load dataset: {e}")
            return None

    def get_stats(self) -> Dict[str, Any]:
        """データセットの統計情報を取得"""
        dataset = self.get_dataset()
        if dataset is None:
            return {"success": False, "error": "Dataset not found"}

        try:
            stats = {
                "name": dataset.name,
                "sample_count": len(dataset),
                "fields": list(dataset.get_field_schema().keys()),
                "tags": dataset.distinct("tags"),
            }

            # マップ別の集計
            if "carla_map" in stats["fields"]:
                map_counts = {}
                for map_name in dataset.distinct("carla_map"):
                    map_counts[map_name] = len(dataset.match(fo.ViewField("carla_map") == map_name))
                stats["map_distribution"] = map_counts

            logger.info(f"Dataset stats: {stats['sample_count']} samples")

            return {
                "success": True,
                "stats": stats
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"success": False, "error": str(e)}

    def list_samples(self, limit: int = 10) -> Dict[str, Any]:
        """サンプル一覧を取得"""
        dataset = self.get_dataset()
        if dataset is None:
            return {"success": False, "error": "Dataset not found"}

        try:
            samples = []
            for sample in dataset.limit(limit):
                sample_info = {
                    "id": sample.id,
                    "filepath": sample.filepath,
                    "logical_uuid": sample.get("logical_uuid", ""),
                    "parameter_uuid": sample.get("parameter_uuid", ""),
                    "carla_map": sample.get("carla_map", ""),
                    "initial_speed": sample.get("initial_speed", 0),
                    "tags": sample.tags
                }
                samples.append(sample_info)

            return {
                "success": True,
                "samples": samples,
                "count": len(samples)
            }
        except Exception as e:
            logger.error(f"Failed to list samples: {e}")
            return {"success": False, "error": str(e)}


# グローバルインスタンス
fiftyone_manager = FiftyOneManager()
