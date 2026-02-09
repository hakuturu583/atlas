"""CARLA設定のデータモデル"""

from pydantic import BaseModel, Field
from typing import Optional


class CarlaSettings(BaseModel):
    """CARLA起動設定（CarlaUnreal.sh用）"""

    carla_path: str = Field(
        default="/opt/carla",
        description="CARLAインストールディレクトリのパス"
    )

    executable_name: str = Field(
        default="CarlaUnreal.sh",
        description="CARLA実行シェルスクリプト名（Linux: CarlaUnreal.sh, Windows: CarlaUE4.exe）"
    )

    default_port: int = Field(
        default=2000,
        ge=1024,
        le=65535,
        description="デフォルトのCARLAポート番号"
    )

    default_map: str = Field(
        default="Town10HD",
        description="デフォルトで読み込むマップ名"
    )

    quality_level: str = Field(
        default="Low",
        description="グラフィック品質（Low/Medium/Epic）"
    )

    additional_args: str = Field(
        default="-RenderOffScreen -nosound -nullrhi",
        description="追加の起動引数"
    )

    timeout: int = Field(
        default=60,
        ge=5,
        le=300,
        description="起動タイムアウト（秒）"
    )

    auto_start: bool = Field(
        default=False,
        description="システム起動時にCARLAを自動起動"
    )

    def get_executable_path(self) -> str:
        """CARLA実行ファイルのフルパスを取得"""
        import os
        return os.path.join(self.carla_path, self.executable_name)

    def get_launch_command(self, port: Optional[int] = None, map_name: Optional[str] = None) -> list[str]:
        """起動コマンドを生成"""
        cmd = [self.get_executable_path()]

        # ポート指定（-carla-rpc-port）
        cmd.append(f"-carla-rpc-port={port or self.default_port}")

        # マップ指定（-carla-world）
        if map_name or self.default_map:
            cmd.append(f"-carla-world={map_name or self.default_map}")

        # 品質設定
        if self.quality_level:
            cmd.append(f"-quality-level={self.quality_level}")

        # 追加引数
        if self.additional_args:
            cmd.extend(self.additional_args.split())

        return cmd
