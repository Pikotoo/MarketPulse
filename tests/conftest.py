"""
pytest 全局配置 — CI 环境自动跳过数据依赖测试

当 DATA_ROOT 不存在或无数据文件时，只运行 import/syntax 检查，
数据相关的功能测试自动跳过（避免 CI 中因缺数据而失败）。
"""

import pytest
import os
from pathlib import Path


def _has_market_data() -> bool:
    """检查是否有可用的市场数据"""
    data_root = os.environ.get("DATA_ROOT", "")

    if data_root:
        root = Path(data_root)
    else:
        # 默认路径
        candidates = [
            Path(r"H:\数据大全"),
            Path(__file__).parent.parent / "data_source",
        ]
        root = next((c for c in candidates if c.exists()), None)

    if root is None or not root.exists():
        return False

    # 检查是否有实际数据文件（.day 或 .parquet）
    day_files = list(root.glob("*.day")) + list(root.glob("38#*.day"))
    parquet_files = list(root.glob("*.parquet"))
    csv_files = list(root.glob("*.csv"))

    return len(day_files) > 0 or len(parquet_files) > 0 or len(csv_files) > 0


def pytest_collection_modifyitems(config, items):
    """CI/无数据环境：只跑 import 测试，跳过数据依赖测试"""
    if _has_market_data():
        return  # 有数据，全部测试正常运行

    skip_data = pytest.mark.skip(
        reason="市场数据不可用（CI 环境或未配置 DATA_ROOT）—— 仅运行 import 检查"
    )
    for item in items:
        if "test_import" not in item.name:
            item.add_marker(skip_data)
