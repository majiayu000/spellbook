#!/usr/bin/env python3
"""
小红书配图生成脚本
使用 Atlas Cloud Nano Banana API 生成图片
"""

import os
import sys
import json
import time
import argparse
import requests
from pathlib import Path
from typing import Dict, Optional, Tuple

DEFAULT_API_BASE = "https://api.atlascloud.ai/v1"
ENV_FILE_ENV_VAR = "XHS_ENV_FILE"


class ConfigError(RuntimeError):
    """Raised when required API configuration is missing or invalid."""


def load_env_file(env_path: str) -> Dict[str, str]:
    """从.env文件加载配置"""
    config_path = Path(env_path).expanduser()
    if not config_path.is_file():
        raise ConfigError(f"配置文件不存在: {config_path}")

    config = {}
    with open(config_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                # 去除行内注释 (# 后面的内容)
                if " #" in value:
                    value = value.split(" #")[0]
                # 去除可能的引号和空白
                value = value.strip().strip('"').strip("'")
                config[key.strip()] = value
    return config


def resolve_config(env_file: Optional[str] = None) -> Tuple[str, str]:
    """获取API配置"""
    # 优先从环境变量获取
    api_key = os.environ.get("ATLAS_API_KEY") or os.environ.get("LLM_API_KEY")
    api_base = os.environ.get("ATLAS_API_BASE") or os.environ.get("LLM_API_BASE")

    # 只在显式指定时读取.env文件，避免从作者本机路径或隐式文件读取凭据
    explicit_env_file = env_file or os.environ.get(ENV_FILE_ENV_VAR)
    env_config = load_env_file(explicit_env_file) if explicit_env_file else {}
    if env_config and (not api_key or not api_base):
        api_key = api_key or env_config.get("ATLAS_API_KEY") or env_config.get("LLM_API_KEY")
        api_base = api_base or env_config.get("ATLAS_API_BASE") or env_config.get("LLM_API_BASE")

    if not api_key:
        raise ConfigError(
            "未找到 API Key，请设置 ATLAS_API_KEY/LLM_API_KEY，"
            "或通过 --env-file/XHS_ENV_FILE 显式指定配置文件"
        )

    if not api_base:
        api_base = DEFAULT_API_BASE

    return api_key, api_base


def get_config(env_file: Optional[str] = None) -> Tuple[str, str]:
    """获取API配置，CLI入口使用清晰错误信息退出。"""
    try:
        return resolve_config(env_file)
    except ConfigError as exc:
        sys.stderr.write(f"错误: {exc}\n")
        sys.exit(1)


def generate_image(
    prompt: str,
    aspect_ratio: str = "3:4",
    num_images: int = 1,
    output_dir: str = None,
    model: str = "google/nano-banana/text-to-image",
    env_file: Optional[str] = None
):
    """
    生成图片

    Args:
        prompt: 图片描述prompt
        aspect_ratio: 图片比例 (3:4, 1:1, 4:3, 16:9, 9:16)
        num_images: 生成数量
        output_dir: 输出目录
        model: 模型名称
        env_file: 显式指定的.env配置文件路径
    """
    api_key, api_base = get_config(env_file)

    # Atlas Cloud 图片生成 endpoint
    # 将 /v1 替换为完整的图片生成路径
    base_url = api_base.rstrip("/")
    if base_url.endswith("/v1"):
        base_url = base_url[:-3]  # 移除 /v1
    endpoint = f"{base_url}/api/v1/model/generateImage"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    print(f"正在生成图片...")
    print(f"模型: {model}")
    print(f"比例: {aspect_ratio}")
    print(f"Prompt: {prompt[:100]}...")

    saved_files = []

    for i in range(num_images):
        payload = {
            "model": model,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "output_format": "png",
            "enable_sync_mode": True  # 同步模式，等待完成
        }

        try:
            response = requests.post(endpoint, headers=headers, json=payload, timeout=120)

            if response.status_code != 200:
                print(f"API错误 ({response.status_code}): {response.text}", file=sys.stderr)
                continue

            result = response.json()

            # Atlas Cloud 响应格式: {"code": 200, "data": {"outputs": [...]}}
            data = result.get("data", result)  # 兼容两种格式

            # 获取图片URL
            outputs = data.get("outputs", [])
            if not outputs:
                # 尝试从其他字段获取
                if data.get("urls"):
                    outputs = list(data["urls"].values())
                elif result.get("outputs"):
                    outputs = result["outputs"]

            if not outputs:
                print(f"警告: 第{i+1}张图片未返回结果", file=sys.stderr)
                continue

            # 保存图片
            output_path = Path(output_dir) if output_dir else Path.cwd() / "images"
            output_path.mkdir(parents=True, exist_ok=True)

            for j, img_url in enumerate(outputs):
                if img_url.startswith("data:"):
                    # Base64 编码的图片
                    import base64
                    # 格式: data:image/png;base64,xxxxx
                    header, data = img_url.split(",", 1)
                    img_data = base64.b64decode(data)
                else:
                    # URL 图片
                    img_response = requests.get(img_url, timeout=60)
                    img_data = img_response.content

                filename = f"xhs_image_{int(time.time())}_{i+1}_{j+1}.png"
                filepath = output_path / filename

                with open(filepath, "wb") as f:
                    f.write(img_data)

                saved_files.append(str(filepath))
                print(f"已保存: {filepath}")

        except requests.exceptions.Timeout:
            print(f"超时: 第{i+1}张图片生成超时", file=sys.stderr)
            continue
        except requests.exceptions.RequestException as e:
            print(f"网络错误: {e}", file=sys.stderr)
            continue
        except Exception as e:
            print(f"错误: {e}", file=sys.stderr)
            continue

    if saved_files:
        # 输出JSON结果供Claude读取
        print(json.dumps({
            "success": True,
            "files": saved_files,
            "count": len(saved_files)
        }))
        return saved_files
    else:
        print(json.dumps({
            "success": False,
            "error": "未能生成任何图片"
        }))
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="小红书配图生成器 (Atlas Cloud)")
    parser.add_argument("prompt", help="图片描述prompt")
    parser.add_argument("--ratio", "-r", default="3:4",
                        choices=["3:4", "4:3", "1:1", "16:9", "9:16", "2:3", "3:2", "4:5", "5:4"],
                        help="图片比例 (默认: 3:4 竖版)")
    parser.add_argument("--num", "-n", type=int, default=1,
                        help="生成数量 (默认: 1)")
    parser.add_argument("--output", "-o", help="输出目录")
    parser.add_argument("--model", "-m", default="google/nano-banana/text-to-image",
                        choices=[
                            "google/nano-banana/text-to-image",
                            "google/nano-banana-pro/text-to-image"
                        ],
                        help="模型 (默认: nano-banana)")
    parser.add_argument("--env-file", help="显式指定 .env 配置文件；也可设置 XHS_ENV_FILE")

    args = parser.parse_args()
    generate_image(args.prompt, args.ratio, args.num, args.output, args.model, args.env_file)


if __name__ == "__main__":
    main()
