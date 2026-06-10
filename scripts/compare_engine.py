#!/usr/bin/env python3
"""Compare two WeeklyViz report models and identify key business changes."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class CompareError(Exception):
    """Exception raised for errors in comparison."""
    pass


def load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise CompareError(f"Failed to load JSON from {path}: {exc}")


def get_health_score(health: Optional[str]) -> int:
    # Lower score is healthier
    mapping = {
        "complete": 0,
        "正常": 1,
        "on-track": 1,
        "关注": 2,
        "watch": 2,
        "风险": 3,
        "risk": 3,
        "阻塞": 4,
        "blocked": 4
    }
    return mapping.get(str(health).lower(), 1)


def compare_reports(prev_input: Any, curr_input: Any) -> str:
    prev = load_json(prev_input) if isinstance(prev_input, Path) else prev_input
    curr = load_json(curr_input) if isinstance(curr_input, Path) else curr_input

    lines = []
    lines.append(f"# 周间对比复盘报告 ({prev.get('metadata', {}).get('period', {}).get('label', '上周')} vs {curr.get('metadata', {}).get('period', {}).get('label', '本周')})")
    lines.append("")

    # --- 1. 本周重大决策与状态变化摘要 (Diff Summary) ---
    lines.append("## 一、核心变化与风险提示")
    
    warnings = []
    achievements = []
    regressions = []
    
    # Track OKRs
    prev_okrs = {item["id"]: item for item in prev.get("okrs", []) if "id" in item}
    curr_okrs = {item["id"]: item for item in curr.get("okrs", []) if "id" in item}
    
    # A. OKR Status Regressions & Completed items
    for okr_id, curr_item in curr_okrs.items():
        label = curr_item.get("label", okr_id)
        if okr_id in prev_okrs:
            prev_item = prev_okrs[okr_id]
            prev_health = prev_item.get("health")
            curr_health = curr_item.get("health")
            
            # Health Regression
            if prev_health != curr_health:
                p_score = get_health_score(prev_health)
                c_score = get_health_score(curr_health)
                if c_score > p_score:
                    regressions.append(
                        f"- ⚠️ **状态退化**：`[{okr_id}]` {label} (健康度：`{prev_health}` ➡️ `{curr_health}`)"
                    )
            
            # Priority Change
            prev_pri = prev_item.get("priority")
            curr_pri = curr_item.get("priority")
            if prev_pri != curr_pri:
                warnings.append(
                    f"- 🔄 **优先级变更**：`[{okr_id}]` {label} (优先级：`{prev_pri}` ➡️ `{curr_pri}`)"
                )
                
            # Owner Change
            prev_owner = prev_item.get("owner")
            curr_owner = curr_item.get("owner")
            if prev_owner != curr_owner:
                warnings.append(
                    f"- 👤 **负责人变更**：`[{okr_id}]` {label} (负责人：`{prev_owner}` ➡️ `{curr_owner}`)"
                )
        else:
            # New OKR/Plan/Requirement
            t_type = curr_item.get("type", "requirement")
            achievements.append(
                f"- 🆕 **新增事项**：`[{okr_id}] ({t_type})` {label}"
            )

    # Deleted / Completed items
    for okr_id, prev_item in prev_okrs.items():
        label = prev_item.get("label", okr_id)
        if okr_id not in curr_okrs:
            achievements.append(
                f"- 🗑️ **移除/完成事项**：`[{okr_id}]` {label} (不再出现在本周列表中)"
            )

    # Write core observations
    if regressions:
        lines.append("### 风险与退化事项")
        lines.extend(regressions)
        lines.append("")
        
    if achievements or warnings:
        lines.append("### 新增与变更事项")
        lines.extend(achievements)
        lines.extend(warnings)
        lines.append("")

    if not regressions and not achievements and not warnings:
        lines.append("本周无重大项目或目标状态发生变化。\n")

    # --- 2. 核心指标数值波动 (Metrics Changes) ---
    lines.append("## 二、核心指标波动分析")
    
    prev_metrics = {item["id"]: item for item in prev.get("metrics", []) if "id" in item}
    curr_metrics = {item["id"]: item for item in curr.get("metrics", []) if "id" in item}
    
    metric_rows = []
    for m_id, curr_item in curr_metrics.items():
        name = curr_item.get("name", m_id)
        unit = curr_item.get("unit", "")
        curr_val = curr_item.get("value")
        
        if m_id in prev_metrics:
            prev_item = prev_metrics[m_id]
            prev_val = prev_item.get("value")
            
            # Compute change percentage if numeric
            try:
                cv = float(curr_val)
                pv = float(prev_val)
                if pv != 0:
                    pct = (cv - pv) / pv * 100
                    pct_str = f"{pct:+.1f}%"
                    
                    # Highlight large fluctuations (>10%)
                    if abs(pct) >= 10:
                        pct_str = f"💥 **{pct_str}**"
                else:
                    pct_str = "N/A"
            except (ValueError, TypeError):
                pct_str = "无法计算"
                cv = curr_val
                pv = prev_val
            
            # Format unit representation
            unit_suffix = "%" if unit == "percent" else f" {unit}"
            metric_rows.append(
                f"| {name} | {pv}{unit_suffix} | {cv}{unit_suffix} | {pct_str} |"
            )
        else:
            metric_rows.append(
                f"| {name} | (新指标) | {curr_val} | N/A |"
            )
            
    if metric_rows:
        lines.append("| 指标名称 | 上期值 | 本期值 | 环比变化 |")
        lines.append("| :--- | :--- | :--- | :--- |")
        lines.extend(metric_rows)
        lines.append("")
    else:
        lines.append("未定义或未找到核心数据指标对比。\n")

    # --- 3. OKR/Plan Target Gap Comparison ---
    lines.append("## 三、目标达成进度与偏差")
    
    progress_rows = []
    # Combine old progress and new metrics target progress
    for m_id, curr_item in curr_metrics.items():
        target_info = curr_item.get("target")
        if not target_info or not isinstance(target_info, dict):
            continue
        t_val = target_info.get("value")
        curr_val = curr_item.get("value")
        name = curr_item.get("name", m_id)
        
        try:
            cv = float(curr_val)
            tv = float(t_val)
            if tv != 0:
                pct = cv / tv * 100
                progress_rows.append(
                    f"- **{name}**：当前已完成 `{cv}` / 目标 `{tv}` (完成度：**{pct:.1f}%**)"
                )
        except (ValueError, TypeError):
            pass
            
    if progress_rows:
        lines.extend(progress_rows)
        lines.append("")
    else:
        lines.append("暂无指标型目标进度对比。\n")

    return "\n".join(lines)
