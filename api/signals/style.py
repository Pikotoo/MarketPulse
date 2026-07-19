"""
风格轮动指标 — 大盘/小盘 + 价值/成长相对强弱

指标:
  1. 大盘/小盘相对强度 — 上证50 vs 中证1000 动量差值
  2. 价值/成长相对强度 — 防御行业 vs 进攻行业动量差值
  3. 轮动速度 — 风格切换频率

输出:
  style: 当前占优风格 (large/small/balanced)
  value_growth: 价值/成长偏向
  rotation_speed: 轮动速度 0-100
"""

import sys
from pathlib import Path

_MP_ROOT = Path(__file__).parent.parent.parent
if str(_MP_ROOT) not in sys.path:
    sys.path.insert(0, str(_MP_ROOT))

import numpy as np
import pandas as pd
from datetime import date, timedelta
from typing import Optional

from api.signals.sector import _load_sector, _momentum, DEFENSIVE, OFFENSIVE


def _norm(v, lo, hi):
    if v is None: return 0.0
    if v <= lo: return 0.0
    if v >= hi: return 1.0
    return (v - lo) / (hi - lo)


def _score_size_rotation(as_of=None) -> dict:
    """大盘/小盘相对强度 — 用行业数据近似：大市值行业 vs 小市值行业"""
    try:
        # 大市值代表行业: 银行(990025) + 食品饮料(990008) + 非银金融(990026)
        # 小市值代表行业: 计算机(990022) + 传媒(990023) + 电子(990006)
        large_codes = ["990025", "990008", "990026"]
        small_codes = ["990022", "990023", "990006"]

        large_moms = []
        for c in large_codes:
            df = _load_sector(c)
            if df is not None:
                large_moms.append(_momentum(df, 60, as_of))

        small_moms = []
        for c in small_codes:
            df = _load_sector(c)
            if df is not None:
                small_moms.append(_momentum(df, 60, as_of))

        if not large_moms or not small_moms:
            return {"value": None, "sub_score": None}

        large_avg = np.mean(large_moms) * 100
        small_avg = np.mean(small_moms) * 100
        diff = round(large_avg - small_avg, 2)

        if diff > 5:
            style = "large_cap"  # 大盘占优
        elif diff < -5:
            style = "small_cap"  # 小盘占优
        else:
            style = "balanced"

        # 归一化到 0-1（大盘占优=1，小盘占优=0）
        s = _norm(diff, -10.0, 10.0)
        return {"value": diff, "unit": "%", "style": style,
                "large_avg_mom": round(large_avg, 2), "small_avg_mom": round(small_avg, 2),
                "score": round(s, 3)}
    except Exception:
        return {"value": None}


def _score_value_growth(as_of=None) -> dict:
    """价值/成长偏向 — 防御行业 vs 进攻行业动量差"""
    try:
        def_moms = []
        for c in DEFENSIVE:
            df = _load_sector(c)
            if df is not None:
                def_moms.append(_momentum(df, 60, as_of))

        off_moms = []
        for c in OFFENSIVE:
            df = _load_sector(c)
            if df is not None:
                off_moms.append(_momentum(df, 60, as_of))

        if not def_moms or not off_moms:
            return {"value": None}

        def_avg = np.mean(def_moms) * 100
        off_avg = np.mean(off_moms) * 100
        diff = round(def_avg - off_avg, 2)

        if diff > 3:
            bias = "value"  # 价值/防御占优
        elif diff < -3:
            bias = "growth"  # 成长/进攻占优
        else:
            bias = "balanced"

        s = _norm(diff, -8.0, 8.0)
        return {"value": diff, "unit": "%", "bias": bias,
                "defensive_avg_mom": round(def_avg, 2), "offensive_avg_mom": round(off_avg, 2),
                "score": round(s, 3)}
    except Exception:
        return {"value": None}


def _score_rotation_speed(as_of=None) -> dict:
    """轮动速度 — 过去一个月 Top3 行业更换频率"""
    try:
        from api.signals.crowding import _get_all_momentums
        now_date = pd.Timestamp(as_of) if as_of else pd.Timestamp.now()
        month_ago = now_date - pd.Timedelta(days=21)
        now = _get_all_momentums(now_date)
        old = _get_all_momentums(month_ago)

        if not now or not old:
            return {"value": None}

        now_top3 = set(m["code"] for m in now[:3])
        old_top3 = set(m["code"] for m in old[:3])
        changed = len(now_top3 - old_top3)

        # 0=无变化（慢速），3=全部更换（快速轮动）
        s = _norm(changed, 0.0, 3.0)
        return {"value": changed, "unit": "个（Top3更换数）",
                "score": round(s, 3)}
    except Exception:
        return {"value": None}


def _style_history(days: int) -> dict:
    """风格轮动历史序列（周频采样）"""
    days = min(days, 365)
    end = pd.Timestamp.now()
    cursor = end - pd.Timedelta(days=days)

    anchors = []
    while cursor <= end:
        if cursor.dayofweek < 5:
            anchors.append(cursor)
        cursor += pd.Timedelta(days=4)

    if len(anchors) > 50:
        step = max(1, len(anchors) // 40)
        anchors = anchors[::step]

    history = []
    for a in anchors:
        try:
            s1 = _score_size_rotation(as_of=a)
            s2 = _score_value_growth(as_of=a)
            history.append({
                "date": a.strftime("%Y-%m-%d"),
                "size_style": s1.get("style", "unknown"),
                "size_diff": s1.get("value"),
                "value_growth_bias": s2.get("bias", "unknown"),
                "vg_diff": s2.get("value"),
            })
        except Exception:
            continue

    return {
        "indicator": "style_rotation", "days": days, "samples": len(history),
        "as_of_date": date.today().isoformat(), "history": history,
    }


def get_style_rotation(days: int = 0) -> dict:
    """风格轮动指标"""
    if days > 0:
        return _style_history(days)

    s1 = _score_size_rotation()
    s2 = _score_value_growth()
    s3 = _score_rotation_speed()

    return {
        "indicator": "style_rotation",
        "size_style": s1.get("style", "unknown"),
        "size_diff": s1.get("value"),
        "value_growth_bias": s2.get("bias", "unknown"),
        "vg_diff": s2.get("value"),
        "rotation_speed": s3.get("value"),
        "sub_scores": {"size": s1, "value_growth": s2, "rotation_speed": s3},
        "as_of_date": date.today().isoformat(),
    }
