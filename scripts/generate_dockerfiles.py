#!/usr/bin/env python3
"""
Dockerfile自動生成スクリプト

Hydra設定ファイル + Jinja2テンプレートからDockerfileを生成
"""

import sys
import os
from pathlib import Path
from typing import Optional

from hydra import compose, initialize_config_dir
from hydra.core.global_hydra import GlobalHydra
from jinja2 import Template
from omegaconf import OmegaConf


def generate_dockerfile(
    config_name: str,
    config_dir: Path,
    template_path: Path,
    output_dir: Path,
) -> Path:
    """
    設定ファイルからDockerfileを生成

    Args:
        config_name: 設定ファイル名（拡張子なし）
        config_dir: 設定ディレクトリ
        template_path: Jinja2テンプレートパス
        output_dir: 出力ディレクトリ

    Returns:
        生成されたDockerfileのパス
    """
    # Hydra初期化（既存のインスタンスをクリア）
    GlobalHydra.instance().clear()

    with initialize_config_dir(
        config_dir=str(config_dir.absolute()), version_base="1.3"
    ):
        # 設定を読み込み
        cfg = compose(config_name=config_name)
        cfg_dict = OmegaConf.to_container(cfg, resolve=True)

    # Jinja2テンプレートを読み込み
    with open(template_path) as f:
        template = Template(f.read())

    # Dockerfileを生成
    dockerfile_content = template.render(**cfg_dict)

    # 出力
    output_path = output_dir / f"Dockerfile.{cfg_dict['name']}"
    with open(output_path, "w") as f:
        f.write(dockerfile_content)

    return output_path


def main():
    # プロジェクトルート
    project_root = Path(__file__).parent.parent
    config_dir = project_root / "configs" / "vla"
    template_path = project_root / "templates" / "Dockerfile.jinja2"
    output_dir = project_root / "docker"

    # 出力ディレクトリを作成
    output_dir.mkdir(exist_ok=True)

    # 生成するモデル
    models = ["base", "dummy", "alpamayo"]

    if len(sys.argv) > 1:
        # コマンドライン引数で指定
        models = sys.argv[1:]

    print("=" * 60)
    print("Generating Dockerfiles from templates")
    print("=" * 60)
    print(f"Config dir: {config_dir}")
    print(f"Template: {template_path}")
    print(f"Output dir: {output_dir}")
    print(f"Models: {', '.join(models)}")
    print("=" * 60)
    print()

    generated_files = []

    for model in models:
        try:
            print(f"Generating Dockerfile for '{model}'...")
            output_path = generate_dockerfile(
                config_name=model,
                config_dir=config_dir,
                template_path=template_path,
                output_dir=output_dir,
            )
            print(f"  ✓ Generated: {output_path}")
            generated_files.append(output_path)

        except Exception as e:
            print(f"  ✗ Error generating '{model}': {e}")
            import traceback

            traceback.print_exc()

    print()
    print("=" * 60)
    print(f"✓ Generated {len(generated_files)} Dockerfile(s)")
    print("=" * 60)
    print()
    print("Generated files:")
    for path in generated_files:
        print(f"  - {path}")
    print()


if __name__ == "__main__":
    main()
