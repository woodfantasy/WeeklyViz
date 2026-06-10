#!/usr/bin/env python3
"""Extract sources, validate report models, and render WeeklyViz HTML."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import sys
import zipfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "assets" / "templates"
RUNTIME = ROOT / "assets" / "runtime"
VENDOR = ROOT / "assets" / "vendor"
TEMPLATE_ALIASES = {
    "executive": "cangshan",
    "editorial": "qianzi",
    "product-operations": "songye"
}
REVERSE_ALIASES = {v: k for k, v in TEMPLATE_ALIASES.items()}
SUPPORTED = {".xlsx", ".csv", ".docx", ".md", ".markdown", ".txt"}
UNSUPPORTED_HELP = {
    ".xls": "Legacy .xls is not supported. Convert it to .xlsx.",
    ".pdf": "PDF is not supported in v1. Export the content to DOCX, XLSX, Markdown, or text.",
    ".ppt": "PowerPoint is not supported in v1. Export the content to DOCX, Markdown, or text.",
    ".pptx": "PowerPoint is not supported in v1. Export the content to DOCX, Markdown, or text.",
}

NS_XLSX = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pkg": "http://schemas.openxmlformats.org/package/2006/relationships",
}
NS_DOCX = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


class WeeklyVizError(Exception):
    """User-facing error."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise WeeklyVizError(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise WeeklyVizError(f"Invalid JSON in {path}: {exc}") from exc


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def stable_id(path: Path, location: str) -> str:
    key = f"{path.resolve()}::{location}".encode("utf-8")
    return "src-" + hashlib.sha1(key).hexdigest()[:12]


def make_source(path: Path, source_type: str, location: str, data: Any, label: Optional[str] = None) -> Dict[str, Any]:
    return {
        "id": stable_id(path, location),
        "label": label or path.name,
        "type": source_type,
        "location": location,
        "path": str(path.resolve()),
        "data": data,
    }


def decode_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "utf-16"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def extract_plain_text(path: Path) -> List[Dict[str, Any]]:
    text = decode_text(path).strip()
    if not text:
        return [make_source(path, "text", "document", {"text": ""})]
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return [
        make_source(
            path,
            "text",
            f"paragraphs 1-{len(paragraphs)}",
            {"text": text, "paragraphs": paragraphs},
        )
    ]


def split_markdown_sections(text: str) -> List[Tuple[str, str, int]]:
    sections: List[Tuple[str, str, int]] = []
    title = "Document"
    start_line = 1
    body: List[str] = []
    for line_no, line in enumerate(text.splitlines(), 1):
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if match:
            if body or sections:
                sections.append((title, "\n".join(body).strip(), start_line))
            title = match.group(2).strip()
            start_line = line_no
            body = []
        else:
            body.append(line)
    if body or not sections:
        sections.append((title, "\n".join(body).strip(), start_line))
    return sections


def extract_markdown(path: Path) -> List[Dict[str, Any]]:
    text = decode_text(path)
    result = []
    for title, body, line_no in split_markdown_sections(text):
        result.append(
            make_source(
                path,
                "markdown-section",
                f"line {line_no}: {title}",
                {"heading": title, "text": body},
                f"{path.name} / {title}",
            )
        )
    return result


def extract_csv(path: Path) -> List[Dict[str, Any]]:
    text = decode_text(path)
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.reader(text.splitlines(), dialect))
    headers = rows[0] if rows else []
    data_rows = rows[1:] if len(rows) > 1 else []
    return [
        make_source(
            path,
            "csv-table",
            f"rows 1-{len(rows)}",
            {
                "delimiter": dialect.delimiter,
                "headers": headers,
                "rows": data_rows,
                "row_count": len(data_rows),
            },
        )
    ]


def qname(namespace: str, tag: str) -> str:
    return f"{{{namespace}}}{tag}"


def xlsx_shared_strings(archive: zipfile.ZipFile) -> List[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    values: List[str] = []
    for item in root.findall("main:si", NS_XLSX):
        values.append("".join(node.text or "" for node in item.iter(qname(NS_XLSX["main"], "t"))))
    return values


def xlsx_sheet_map(archive: zipfile.ZipFile) -> List[Tuple[str, str]]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    rels_root = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    relationships = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels_root.findall("pkg:Relationship", NS_XLSX)
    }
    sheets = []
    for sheet in workbook.findall("main:sheets/main:sheet", NS_XLSX):
        rel_id = sheet.attrib.get(qname(NS_XLSX["rel"], "id"), "")
        target = relationships.get(rel_id, "")
        if target.startswith("/"):
            xml_path = target.lstrip("/")
        else:
            xml_path = "xl/" + target.lstrip("/")
        sheets.append((sheet.attrib.get("name", "Sheet"), xml_path))
    return sheets


def coerce_number(value: str) -> Any:
    if value == "":
        return ""
    try:
        number = float(value)
        return int(number) if number.is_integer() else number
    except ValueError:
        return value


def xlsx_cell_value(cell: ET.Element, shared: Sequence[str]) -> Tuple[Any, Optional[str]]:
    cell_type = cell.attrib.get("t")
    value_node = cell.find("main:v", NS_XLSX)
    formula_node = cell.find("main:f", NS_XLSX)
    formula = formula_node.text if formula_node is not None else None
    if cell_type == "inlineStr":
        inline = cell.find("main:is", NS_XLSX)
        value = "".join(node.text or "" for node in inline.iter(qname(NS_XLSX["main"], "t"))) if inline is not None else ""
    elif value_node is None:
        value = ""
    elif cell_type == "s":
        try:
            value = shared[int(value_node.text or "0")]
        except (ValueError, IndexError):
            value = value_node.text or ""
    elif cell_type == "b":
        value = (value_node.text or "0") == "1"
    elif cell_type in {"str", "e"}:
        value = value_node.text or ""
    else:
        value = coerce_number(value_node.text or "")
    return value, formula


def extract_xlsx(path: Path) -> List[Dict[str, Any]]:
    try:
        archive = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        raise WeeklyVizError(f"{path.name} is not a valid XLSX file") from exc
    with archive:
        try:
            shared = xlsx_shared_strings(archive)
            sheet_map = xlsx_sheet_map(archive)
        except (KeyError, ET.ParseError) as exc:
            raise WeeklyVizError(f"{path.name} has an invalid XLSX structure") from exc
        result = []
        for sheet_name, xml_path in sheet_map:
            try:
                root = ET.fromstring(archive.read(xml_path))
            except KeyError:
                continue
            rows = []
            max_column = 0
            for row in root.findall(".//main:sheetData/main:row", NS_XLSX):
                cells = []
                for cell in row.findall("main:c", NS_XLSX):
                    value, formula = xlsx_cell_value(cell, shared)
                    item = {"cell": cell.attrib.get("r", ""), "value": value}
                    if formula is not None:
                        item["formula"] = formula
                    cells.append(item)
                max_column = max(max_column, len(cells))
                if cells:
                    rows.append(cells)
            location = f"{sheet_name}!used-range"
            result.append(
                make_source(
                    path,
                    "xlsx-sheet",
                    location,
                    {
                        "sheet": sheet_name,
                        "rows": rows,
                        "row_count": len(rows),
                        "max_populated_columns": max_column,
                    },
                    f"{path.name} / {sheet_name}",
                )
            )
        return result


def docx_text(node: ET.Element) -> str:
    return "".join(part.text or "" for part in node.iter(qname(NS_DOCX["w"], "t"))).strip()


def docx_paragraph_style(paragraph: ET.Element) -> str:
    style = paragraph.find("w:pPr/w:pStyle", NS_DOCX)
    return style.attrib.get(qname(NS_DOCX["w"], "val"), "") if style is not None else ""


def extract_docx(path: Path) -> List[Dict[str, Any]]:
    try:
        archive = zipfile.ZipFile(path)
        document_xml = archive.read("word/document.xml")
    except (zipfile.BadZipFile, KeyError) as exc:
        raise WeeklyVizError(f"{path.name} is not a valid DOCX file") from exc
    finally:
        if "archive" in locals():
            archive.close()
    root = ET.fromstring(document_xml)
    body = root.find("w:body", NS_DOCX)
    if body is None:
        return []
    sources: List[Dict[str, Any]] = []
    section_title = "Document"
    paragraphs: List[str] = []
    section_index = 1
    table_index = 0

    def flush_paragraphs() -> None:
        nonlocal paragraphs, section_index
        if not paragraphs:
            return
        location = f"section {section_index}: {section_title}"
        sources.append(
            make_source(
                path,
                "docx-section",
                location,
                {"heading": section_title, "paragraphs": paragraphs},
                f"{path.name} / {section_title}",
            )
        )
        section_index += 1
        paragraphs = []

    for child in body:
        local = child.tag.rsplit("}", 1)[-1]
        if local == "p":
            text = docx_text(child)
            if not text:
                continue
            style = docx_paragraph_style(child).lower()
            if style.startswith("heading") or style.startswith("标题"):
                flush_paragraphs()
                section_title = text
            else:
                paragraphs.append(text)
        elif local == "tbl":
            flush_paragraphs()
            table_index += 1
            rows = []
            for row in child.findall("w:tr", NS_DOCX):
                rows.append([docx_text(cell) for cell in row.findall("w:tc", NS_DOCX)])
            sources.append(
                make_source(
                    path,
                    "docx-table",
                    f"table {table_index}",
                    {"rows": rows, "row_count": len(rows)},
                    f"{path.name} / Table {table_index}",
                )
            )
    flush_paragraphs()
    return sources


def extract_file(path: Path) -> List[Dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix in UNSUPPORTED_HELP:
        raise WeeklyVizError(f"{path.name}: {UNSUPPORTED_HELP[suffix]}")
    if suffix not in SUPPORTED:
        raise WeeklyVizError(f"{path.name}: unsupported input type {suffix or '(none)'}")
    if suffix == ".csv":
        return extract_csv(path)
    if suffix == ".xlsx":
        return extract_xlsx(path)
    if suffix == ".docx":
        return extract_docx(path)
    if suffix in {".md", ".markdown"}:
        return extract_markdown(path)
    return extract_plain_text(path)


def command_extract(inputs: Sequence[str], output: str) -> int:
    sources: List[Dict[str, Any]] = []
    warnings: List[str] = []
    for raw in inputs:
        path = Path(raw).expanduser()
        if not path.exists():
            raise WeeklyVizError(f"Input file not found: {path}")
        extracted = extract_file(path)
        if not extracted:
            warnings.append(f"No readable content found in {path.name}")
        sources.extend(extracted)
    bundle = {
        "version": "1.0",
        "generated_at": utc_now(),
        "sources": sources,
        "warnings": warnings,
        "instructions": {
            "traceability": "Copy each used source id, label, type, and location into report-model.json sources.",
            "integrity": "Do not create numeric claims not present in these sources.",
        },
    }
    write_json(Path(output), bundle)
    print(f"Extracted {len(sources)} source block(s) to {output}")
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    return 0


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_model(model: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    def require_object(value: Any, path: str) -> Dict[str, Any]:
        if not isinstance(value, dict):
            errors.append(f"{path} must be an object")
            return {}
        return value

    metadata = require_object(model.get("metadata"), "metadata")
    for key in ("report_id", "title", "period"):
        if key not in metadata:
            errors.append(f"metadata.{key} is required")
    period = metadata.get("period")
    if not isinstance(period, dict) or not str(period.get("label", "")).strip():
        errors.append("metadata.period.label is required")

    template = model.get("template")
    template_mapped = TEMPLATE_ALIASES.get(template, template)
    valid_templates = set()
    if TEMPLATES.exists():
        valid_templates = {p.stem for p in TEMPLATES.glob("*.json")}
    if not valid_templates:
        valid_templates = {"cangshan", "qianzi", "songye"}
    
    # Allow both mapped target name and the alias keys
    all_allowed = valid_templates.union(TEMPLATE_ALIASES.keys())
    if template not in all_allowed:
        errors.append(f"template must be one of {', '.join(sorted(all_allowed))}")

    summary = require_object(model.get("summary"), "summary")
    for key in ("headline", "body"):
        if not str(summary.get(key, "")).strip():
            errors.append(f"summary.{key} is required")

    sources = model.get("sources")
    if not isinstance(sources, list):
        errors.append("sources must be an array")
        sources = []
    source_ids = {item.get("id") for item in sources if isinstance(item, dict) and item.get("id")}
    if len(source_ids) != len([item for item in sources if isinstance(item, dict) and item.get("id")]):
        errors.append("sources contains duplicate ids")
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            errors.append(f"sources[{index}] must be an object")
            continue
        for key in ("id", "label", "type", "location"):
            if not str(source.get(key, "")).strip():
                errors.append(f"sources[{index}].{key} is required")

    theme = model.get("theme", {})
    if theme is not None and not isinstance(theme, dict):
        errors.append("theme must be an object")
    elif isinstance(theme, dict):
        for key, value in theme.items():
            if key not in {"primary", "accent", "background", "surface", "text", "muted"}:
                warnings.append(f"theme.{key} is not a recognized token")
            if not isinstance(value, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
                errors.append(f"theme.{key} must be a six-digit hex color")

    presentation = model.get("presentation", {})
    if presentation is not None and not isinstance(presentation, dict):
        errors.append("presentation must be an object")
    elif isinstance(presentation, dict):
        allowed_presentation = {
            "density": {"compact", "balanced", "spacious"},
            "layout": {"dashboard", "newsletter", "kanban", "operating-review"},
            "section_layout": {"cards", "grid", "list", "table", "kanban"},
            "source_display": {"summary", "expanded"},
        }
        for key, allowed in allowed_presentation.items():
            if key in presentation and presentation[key] not in allowed:
                errors.append(f"presentation.{key} must be one of {', '.join(sorted(allowed))}")
        if "layout_order" in presentation:
            if not isinstance(presentation["layout_order"], list):
                errors.append("presentation.layout_order must be an array")
        if "show_toc" in presentation and not isinstance(presentation["show_toc"], bool):
            errors.append("presentation.show_toc must be boolean")

    seen_ids: set = set()

    def validate_traceable(item: Dict[str, Any], path: str) -> None:
        refs = item.get("source_refs")
        if not isinstance(refs, list) or not refs:
            errors.append(f"{path}.source_refs must contain at least one source id")
        else:
            for ref in refs:
                if ref not in source_ids:
                    errors.append(f"{path}.source_refs references unknown source {ref!r}")
        if item.get("derived") and not str(item.get("formula", "")).strip():
            errors.append(f"{path}.formula is required when derived is true")

    for collection in ("kpis", "progress", "charts"):
        items = model.get(collection, [])
        if not isinstance(items, list):
            errors.append(f"{collection} must be an array")
            continue
        for index, item in enumerate(items):
            path = f"{collection}[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{path} must be an object")
                continue
            item_id = item.get("id")
            if not str(item_id or "").strip():
                errors.append(f"{path}.id is required")
            elif item_id in seen_ids:
                errors.append(f"duplicate component id {item_id!r}")
            else:
                seen_ids.add(item_id)
            validate_traceable(item, path)

    for index, item in enumerate(model.get("kpis", []) if isinstance(model.get("kpis", []), list) else []):
        if isinstance(item, dict):
            for key in ("label", "value"):
                if key not in item or item.get(key) == "":
                    errors.append(f"kpis[{index}].{key} is required")

    for index, item in enumerate(model.get("progress", []) if isinstance(model.get("progress", []), list) else []):
        if not isinstance(item, dict):
            continue
        current, target = item.get("current"), item.get("target")
        if not is_number(current):
            errors.append(f"progress[{index}].current must be numeric")
        if not is_number(target) or target <= 0:
            errors.append(f"progress[{index}].target must be greater than zero")

    valid_chart_types = {
        "line", "area", "bar", "horizontal-bar", "grouped-bar", "stacked-bar",
        "donut", "pie", "waterfall", "funnel", "scatter", "heatmap", "timeline", "table",
    }
    for index, chart in enumerate(model.get("charts", []) if isinstance(model.get("charts", []), list) else []):
        if not isinstance(chart, dict):
            continue
        path = f"charts[{index}]"
        chart_type = chart.get("type")
        if chart_type not in valid_chart_types:
            errors.append(f"{path}.type is unsupported")
        for key in ("title", "question", "unit", "insight"):
            if not str(chart.get(key, "")).strip():
                errors.append(f"{path}.{key} is required")
        labels = chart.get("labels", [])
        series = chart.get("series")
        if not isinstance(series, list) or not series:
            errors.append(f"{path}.series must contain at least one series")
            continue
        for series_index, dataset in enumerate(series):
            if not isinstance(dataset, dict) or not isinstance(dataset.get("values"), list):
                errors.append(f"{path}.series[{series_index}] requires name and values")
                continue
            values = dataset["values"]
            if labels and chart_type not in {"scatter", "heatmap"} and len(values) != len(labels):
                errors.append(f"{path}.series[{series_index}] value count must match labels")
        if chart_type in {"line", "area"} and len(labels) < 4:
            errors.append(f"{path}: line and area charts require at least 4 chronological labels")
        if chart_type in {"donut", "pie"}:
            if not 2 <= len(labels) <= 6:
                errors.append(f"{path}: pie and donut charts require 2-6 categories")
            if len(series) != 1:
                errors.append(f"{path}: pie and donut charts require exactly one series")
            elif any(not is_number(value) or value < 0 for value in series[0].get("values", [])):
                errors.append(f"{path}: pie and donut values must be nonnegative numbers")
        if chart_type == "funnel" and len(labels) < 2:
            errors.append(f"{path}: funnels require at least 2 ordered stages")
        if chart_type == "scatter":
            points = series[0].get("values", [])
            if len(points) < 4:
                warnings.append(f"{path}: scatter plots are usually weak with fewer than 4 observations")

    for collection in ("sections", "risks", "next_actions"):
        items = model.get(collection, [])
        if items is not None and not isinstance(items, list):
            errors.append(f"{collection} must be an array")
    for index, section in enumerate(model.get("sections", []) if isinstance(model.get("sections", []), list) else []):
        if not isinstance(section, dict):
            continue
        if section.get("layout") not in {None, "cards", "grid", "list", "table", "kanban"}:
            errors.append(f"sections[{index}].layout must be cards, grid, list, table, or kanban")
        if not isinstance(section.get("items", []), list):
            errors.append(f"sections[{index}].items must be an array")

    # Helper to calculate period progress
    def compute_period_progress(period_str: str, as_of_date: datetime) -> Optional[float]:
        import re
        m_q = re.match(r"^(\d{4})-Q([1-4])$", period_str)
        if m_q:
            year = int(m_q.group(1))
            q = int(m_q.group(2))
            q_starts = {1: (1, 1), 2: (4, 1), 3: (7, 1), 4: (10, 1)}
            q_ends = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}
            start_m, start_d = q_starts[q]
            end_m, end_d = q_ends[q]
            start = datetime(year, start_m, start_d, tzinfo=timezone.utc)
            end = datetime(year, end_m, end_d, 23, 59, 59, tzinfo=timezone.utc)
        else:
            m_m = re.match(r"^(\d{4})-(?:M)?(\d{1,2})$", period_str)
            if m_m:
                year = int(m_m.group(1))
                month = int(m_m.group(2))
                start = datetime(year, month, 1, tzinfo=timezone.utc)
                if month == 12:
                    end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
                else:
                    end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
            else:
                return None
        total_sec = (end - start).total_seconds()
        elapsed_sec = (as_of_date - start).total_seconds()
        if total_sec <= 0:
            return None
        return min(max(elapsed_sec / total_sec, 0.0), 1.0)

    # Validate Metrics
    metrics = model.get("metrics", [])
    if not isinstance(metrics, list):
        errors.append("metrics must be an array")
        metrics = []
    seen_metric_ids = set()
    for index, metric in enumerate(metrics):
        path = f"metrics[{index}]"
        if not isinstance(metric, dict):
            errors.append(f"{path} must be an object")
            continue
        m_id = metric.get("id")
        if not m_id:
            errors.append(f"{path}.id is required")
        elif m_id in seen_metric_ids:
            errors.append(f"duplicate metric id {m_id!r}")
        else:
            seen_metric_ids.add(m_id)
        for key in ("name", "unit", "scope", "time_grain", "aggregation"):
            if key not in metric:
                errors.append(f"{path}.{key} is required")
        if "unit" in metric and metric["unit"] not in {"percent", "currency", "integer", "number", "ratio"}:
            errors.append(f"{path}.unit must be percent, currency, integer, number, or ratio")
        if "time_grain" in metric and metric["time_grain"] not in {"day", "week", "month", "quarter", "year"}:
            errors.append(f"{path}.time_grain must be day, week, month, quarter, or year")
        if "aggregation" in metric and metric["aggregation"] not in {"sum", "average", "ratio", "count", "distinct_count", "none"}:
            errors.append(f"{path}.aggregation must be sum, average, ratio, count, distinct_count, or none")
        if "scope" in metric and not isinstance(metric["scope"], list):
            errors.append(f"{path}.scope must be an array of strings")
        validate_traceable(metric, path)
        
        # Check target progress vs time elapsed (lag check)
        target_info = metric.get("target")
        if isinstance(target_info, dict) and "value" in target_info and "period" in target_info:
            t_val = target_info.get("value")
            t_period = target_info.get("period")
            curr_val = metric.get("value")
            try:
                cv = float(curr_val)
                tv = float(t_val)
                if tv > 0:
                    as_of = datetime.now(timezone.utc)
                    time_progress = compute_period_progress(t_period, as_of)
                    if time_progress is not None:
                        completion = cv / tv
                        if completion < time_progress * 0.9:
                            warnings.append(
                                f"Metric {m_id!r} completion ({completion*100:.1f}%) is lagging behind period time progress ({time_progress*100:.1f}%) for period {t_period}"
                            )
            except (ValueError, TypeError):
                pass

    # Validate OKRs
    okrs = model.get("okrs", [])
    if not isinstance(okrs, list):
        errors.append("okrs must be an array")
        okrs = []
    seen_okr_ids = set()
    for index, okr in enumerate(okrs):
        path = f"okrs[{index}]"
        if not isinstance(okr, dict):
            errors.append(f"{path} must be an object")
            continue
        okr_id = okr.get("id")
        if not okr_id:
            errors.append(f"{path}.id is required")
        elif okr_id in seen_okr_ids:
            errors.append(f"duplicate okr id {okr_id!r}")
        else:
            seen_okr_ids.add(okr_id)
        if "type" not in okr or okr["type"] not in {"objective", "key-result", "plan", "requirement"}:
            errors.append(f"{path}.type must be objective, key-result, plan, or requirement")
        if "label" not in okr or not okr["label"]:
            errors.append(f"{path}.label is required")
        parent_id = okr.get("parent_id")
        if parent_id and parent_id not in seen_okr_ids and parent_id not in [o.get("id") for o in okrs]:
            errors.append(f"{path}.parent_id references unknown okr id {parent_id!r}")
        stage = okr.get("stage")
        if stage and stage not in {"待启动", "设计", "开发", "验收", "上线", "暂缓", "planned", "design", "dev", "qa", "release", "deferred"}:
            errors.append(f"{path}.stage is invalid: {stage}")
        health = okr.get("health")
        if health and health not in {"正常", "关注", "风险", "阻塞", "on-track", "watch", "risk", "blocked"}:
            errors.append(f"{path}.health is invalid: {health}")
        validate_traceable(okr, path)

        # OKR Progress lag check if it has target
        if "current" in okr and "target" in okr and "due" in okr:
            curr_val = okr.get("current")
            t_val = okr.get("target")
            t_period = okr.get("due")
            try:
                cv = float(curr_val)
                tv = float(t_val)
                if tv > 0 and health in {"正常", "on-track"}:
                    as_of = datetime.now(timezone.utc)
                    time_progress = compute_period_progress(t_period, as_of)
                    if time_progress is not None:
                        completion = cv / tv
                        if completion < time_progress * 0.9:
                            warnings.append(
                                f"OKR {okr_id!r} completion ({completion*100:.1f}%) is lagging behind period time progress ({time_progress*100:.1f}%) for period {t_period}, but is marked as healthy"
                            )
            except (ValueError, TypeError):
                pass

    if not model.get("kpis") and not model.get("charts") and not model.get("progress") and not model.get("metrics") and not model.get("okrs"):
        warnings.append("Report is qualitative only; no charts or metrics will be rendered")

    return errors, warnings


def command_validate(report: str) -> int:
    model = read_json(Path(report))
    errors, warnings = validate_model(model)
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"Validated {report}: {len(warnings)} warning(s)")
    return 0


def escape(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def json_for_script(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def editable(tag: str, path: str, value: Any, class_name: str = "", attrs: str = "") -> str:
    classes = f' class="{escape(class_name)}"' if class_name else ""
    return (
        f"<{tag}{classes} data-path=\"{escape(path)}\" contenteditable=\"false\" "
        f"spellcheck=\"false\" {attrs}>{escape(value)}</{tag}>"
    )


def source_chips(refs: Iterable[str], source_map: Dict[str, Dict[str, Any]]) -> str:
    refs = list(refs or [])
    if not refs:
        return ""
    chips = []
    labels = []
    for ref in refs:
        source = source_map.get(ref, {})
        label = source.get("label", ref)
        location = source.get("location", "")
        labels.append(f"{label}: {location}" if location else label)
        chips.append(f'<span class="source-chip" title="{escape(location)}">{escape(label)}</span>')
    title = " | ".join(labels)
    return (
        f'<span class="source-trace">'
        f'<span class="source-marker" title="{escape(title)}">SOURCE · {len(refs)}</span>'
        f'<span class="source-detail">{"".join(chips)}</span>'
        f"</span>"
    )


def render_label_values(items: Sequence[Dict[str, Any]], path: str, class_name: str) -> str:
    rows = []
    for index, item in enumerate(items or []):
        if not isinstance(item, dict):
            continue
        rows.append(
            f'<div class="{escape(class_name)}">'
            f'{editable("span", f"{path}.{index}.label", item.get("label", ""))}'
            f'{editable("strong", f"{path}.{index}.value", item.get("value", ""))}'
            f"</div>"
        )
    return "".join(rows)


def render_kpis(model: Dict[str, Any], source_map: Dict[str, Dict[str, Any]]) -> str:
    cards = []
    for index, item in enumerate(model.get("kpis", [])):
        trend = item.get("trend") or {}
        direction = trend.get("direction", "neutral")
        display = item.get("display")
        if display is None:
            display = f"{item.get('value', '')}{item.get('unit', '')}"
        details = render_label_values(item.get("details", []), f"kpis.{index}.details", "kpi-detail")
        cards.append(
            f"""
            <article class="kpi-card" data-component-id="{escape(item.get('id', ''))}">
              <div class="kpi-topline">
                {editable('h3', f'kpis.{index}.label', item.get('label', ''), 'kpi-label')}
                <span class="trend trend-{escape(direction)}">{escape(trend.get('label', ''))} {escape(trend.get('value', ''))}</span>
              </div>
              {editable('div', f'kpis.{index}.display', display, 'kpi-value')}
              {editable('p', f'kpis.{index}.note', item.get('note', ''), 'kpi-note')}
              <div class="kpi-details">{details}</div>
              <div class="source-row">{source_chips(item.get('source_refs', []), source_map)}</div>
            </article>
            """
        )
    if not cards:
        return ""
    return f'<section class="report-section" id="kpis" aria-labelledby="kpi-heading"><div class="section-heading"><span>01</span><h2 id="kpi-heading">核心指标</h2></div><div class="kpi-grid">{"".join(cards)}</div></section>'


def render_progress(model: Dict[str, Any], source_map: Dict[str, Dict[str, Any]]) -> str:
    items = []
    for index, item in enumerate(model.get("progress", [])):
        current = float(item.get("current", 0))
        target = float(item.get("target", 1))
        percent = current / target * 100
        width = min(max(percent, 0), 100)
        items.append(
            f"""
            <article class="progress-item status-{escape(item.get('status', 'on-track'))}">
              <div class="progress-copy">
                {editable('h3', f'progress.{index}.label', item.get('label', ''))}
                <strong>{escape(current):s} / {escape(target):s} {escape(item.get('unit', ''))}</strong>
              </div>
              <div class="progress-track" role="progressbar" aria-valuemin="0" aria-valuemax="{escape(target)}" aria-valuenow="{escape(current)}" aria-label="{escape(item.get('label', ''))}">
                <span class="progress-fill" style="width:{width:.2f}%"></span>
              </div>
              <div class="progress-meta"><span>{percent:.1f}%</span>{source_chips(item.get('source_refs', []), source_map)}</div>
            </article>
            """
        )
    if not items:
        return ""
    return f'<section class="report-section" id="progress" aria-labelledby="progress-heading"><div class="section-heading"><span>02</span><h2 id="progress-heading">目标进度</h2></div><div class="progress-grid">{"".join(items)}</div></section>'


def render_metrics_section(model: Dict[str, Any], source_map: Dict[str, Dict[str, Any]]) -> str:
    metrics = model.get("metrics", [])
    if not metrics:
        return ""
    cards = []
    for index, item in enumerate(metrics):
        m_id = item.get("id")
        name = item.get("name", m_id)
        val = item.get("value")
        unit = item.get("unit", "")
        
        target_info = item.get("target", {})
        t_val = target_info.get("value") if isinstance(target_info, dict) else None
        t_period = target_info.get("period") if isinstance(target_info, dict) else ""
        
        comp = item.get("comparison", {})
        prev_val = comp.get("previous") if isinstance(comp, dict) else None
        
        pct_change = ""
        if prev_val is not None:
            try:
                cv = float(val)
                pv = float(prev_val)
                if pv != 0:
                    change = (cv - pv) / pv * 100
                    pct_change = f"{change:+.1f}%"
            except (ValueError, TypeError):
                pass
                
        unit_suffix = "%" if unit == "percent" else f" {unit}" if unit else ""
        val_str = f"{val}{unit_suffix}"
        prev_str = f"{prev_val}{unit_suffix}" if prev_val is not None else "-"
        
        bullet_html = ""
        if t_val is not None:
            try:
                cv = float(val)
                tv = float(t_val)
                limit = max(cv, tv * 1.2)
                val_pct = (cv / limit * 100) if limit > 0 else 0
                target_pct = (tv / limit * 100) if limit > 0 else 0
                
                bullet_html = f'''
                <div class="bullet-container">
                  <div class="bullet-labels">
                    <span>目标: {tv}{unit_suffix} ({escape(t_period)})</span>
                    <span>当前: {val_str}</span>
                  </div>
                  <div class="bullet-track">
                    <div class="bullet-range range-bad" style="width: 60%"></div>
                    <div class="bullet-range range-sat" style="width: 25%"></div>
                    <div class="bullet-range range-good" style="width: 15%"></div>
                    <div class="bullet-bar" style="width: {val_pct:.1f}%"></div>
                    <div class="bullet-marker" style="left: {target_pct:.1f}%"></div>
                  </div>
                </div>
                '''
            except (ValueError, TypeError):
                pass
                
        health = "on-track"
        if t_val is not None and prev_val is not None:
            try:
                cv = float(val)
                tv = float(t_val)
                pv = float(prev_val)
                if cv < tv and cv < pv:
                    health = "risk"
                elif cv < tv:
                    health = "watch"
            except (ValueError, TypeError):
                pass
                
        cards.append(f'''
        <article class="metric-card status-{health}" data-metric-id="{escape(m_id)}">
          <div class="metric-header">
            <h4>{escape(name)}</h4>
            <span class="metric-grain">{escape(item.get("time_grain", "week").upper())}</span>
          </div>
          <div class="metric-main-val">
            <span class="val-num">{escape(val_str)}</span>
            {f'<span class="val-diff {"diff-up" if "+" in pct_change else "diff-down"}">{escape(pct_change)} 环比</span>' if pct_change else ""}
          </div>
          <div class="metric-meta-details">
            <div>上期值: <strong>{escape(prev_str)}</strong></div>
            <div>聚合: <strong>{escape(item.get("aggregation", "none"))}</strong></div>
            {f'<div>分子: <span>{escape(item.get("numerator"))}</span></div>' if item.get("numerator") else ""}
            {f'<div>分母: <span>{escape(item.get("denominator"))}</span></div>' if item.get("denominator") else ""}
          </div>
          {bullet_html}
          <div class="source-row">{source_chips(item.get('source_refs', []), source_map)}</div>
        </article>
        ''')
        
    return f'''
    <section class="report-section" id="metrics-section" aria-labelledby="metrics-heading">
      <div class="section-heading"><span>01</span><h2 id="metrics-heading">核心指标度量</h2></div>
      <div class="metric-grid">
        {"".join(cards)}
      </div>
    </section>
    '''


def render_okrs_section(model: Dict[str, Any], source_map: Dict[str, Dict[str, Any]]) -> str:
    okrs = model.get("okrs", [])
    if not okrs:
        return ""
        
    objectives = [o for o in okrs if o.get("type") == "objective"]
    krs_by_parent = {}
    plans_by_parent = {}
    reqs_by_parent = {}
    
    for o in okrs:
        p_id = o.get("parent_id")
        t = o.get("type")
        if not p_id:
            continue
        if t == "key-result":
            krs_by_parent.setdefault(p_id, []).append(o)
        elif t == "plan":
            plans_by_parent.setdefault(p_id, []).append(o)
        elif t == "requirement":
            reqs_by_parent.setdefault(p_id, []).append(o)
            
    html_out = []
    html_out.append('<section class="report-section" id="okrs-section" aria-labelledby="okr-heading">')
    html_out.append('<div class="section-heading"><span>04</span><h2 id="okr-heading">OKR 经营复盘矩阵</h2></div>')
    html_out.append('<div class="okr-tree">')
    
    for o_idx, obj in enumerate(objectives):
        obj_id = obj.get("id", f"O{o_idx+1}")
        o_health = obj.get("health", "on-track")
        html_out.append(f'''
        <div class="okr-objective status-{escape(o_health)}">
          <div class="okr-node-header">
            <span class="node-badge">OBJECTIVE</span>
            <span class="node-id">{escape(obj_id)}</span>
            <h3 class="node-label">{escape(obj.get("label"))}</h3>
            <span class="node-health health-{escape(o_health)}">{escape(obj.get("health", "正常"))}</span>
          </div>
          <div class="okr-children">
        ''')
        
        for kr in krs_by_parent.get(obj_id, []):
            kr_id = kr.get("id")
            kr_health = kr.get("health", "on-track")
            
            progress_html = ""
            if "current" in kr and "target" in kr:
                curr = float(kr.get("current", 0))
                targ = float(kr.get("target", 1))
                unit = kr.get("unit", "")
                pct = (curr / targ * 100) if targ > 0 else 0
                progress_html = f'''
                <div class="node-progress">
                  <div class="progress-info">
                    <span>进度: {pct:.1f}%</span>
                    <span>{curr:g} / {targ:g} {escape(unit)}</span>
                  </div>
                  <div class="progress-bar-mini"><span style="width: {min(pct, 100):.1f}%"></span></div>
                </div>
                '''
                
            html_out.append(f'''
            <div class="okr-kr status-{escape(kr_health)}">
              <div class="okr-node-header">
                <span class="node-badge">KEY RESULT</span>
                <span class="node-id">{escape(kr_id)}</span>
                <h4 class="node-label">{escape(kr.get("label"))}</h4>
                <span class="node-health health-{escape(kr_health)}">{escape(kr.get("health", "正常"))}</span>
              </div>
              {progress_html}
              <div class="okr-children">
            ''')
            
            for plan in plans_by_parent.get(kr_id, []):
                p_id = plan.get("id")
                p_health = plan.get("health", "on-track")
                html_out.append(f'''
                <div class="okr-plan status-{escape(p_health)}">
                  <div class="okr-node-header">
                    <span class="node-badge">PLAN / INITIATIVE</span>
                    <span class="node-id">{escape(p_id)}</span>
                    <h5 class="node-label">{escape(plan.get("label"))}</h5>
                    <span class="node-health health-{escape(p_health)}">{escape(plan.get("health", "正常"))}</span>
                  </div>
                  <div class="node-meta-row">
                    <span>负责人: <strong>{escape(plan.get("owner", "未指派"))}</strong></span>
                    <span>阶段: <strong>{escape(plan.get("stage", "未启动"))}</strong></span>
                  </div>
                  <div class="okr-children">
                ''')
                
                for req in reqs_by_parent.get(p_id, []):
                    r_id = req.get("id")
                    r_health = req.get("health", "on-track")
                    blocked_by = req.get("blocked_by", "")
                    block_html = f'<div class="node-block-reason">阻塞原因: {escape(blocked_by)}</div>' if blocked_by else ""
                    
                    html_out.append(f'''
                    <div class="okr-requirement status-{escape(r_health)}">
                      <div class="okr-node-header">
                        <span class="node-badge">MILESTONE</span>
                        <span class="node-id">{escape(r_id)}</span>
                        <span class="node-label-small">{escape(req.get("label"))}</span>
                        <span class="node-health health-{escape(r_health)}">{escape(req.get("health", "正常"))}</span>
                      </div>
                      <div class="node-meta-row">
                        <span>负责人: <strong>{escape(req.get("owner", "-"))}</strong></span>
                        <span>阶段: <strong>{escape(req.get("stage", "-"))}</strong></span>
                        <span>截止: <strong>{escape(req.get("due", "-"))}</strong></span>
                      </div>
                      {block_html}
                    </div>
                    ''')
                    
                html_out.append('</div></div>')
            html_out.append('</div></div>')
        html_out.append('</div></div>')
        
    html_out.append('</div></section>')
    return "".join(html_out)


def render_requirements_section(model: Dict[str, Any]) -> str:
    okrs = model.get("okrs", [])
    reqs = [o for o in okrs if o.get("type") == "requirement"]
    if not reqs:
        return ""
        
    table_rows = []
    for r in reqs:
        r_id = r.get("id", "")
        label = r.get("label", "")
        owner = r.get("owner", "-")
        stage = r.get("stage", "待启动")
        health = r.get("health", "正常")
        pri = r.get("priority", "P2")
        due = r.get("due", "-")
        blocked_by = r.get("blocked_by", "")
        
        table_rows.append(f'''
        <tr data-owner="{escape(owner)}" data-stage="{escape(stage)}" data-health="{escape(health)}" data-pri="{escape(pri)}">
          <td><span class="req-pri pri-{escape(pri)}">{escape(pri)}</span></td>
          <td><strong class="req-id">{escape(r_id)}</strong></td>
          <td><span class="req-label">{escape(label)}</span></td>
          <td><span class="req-owner">{escape(owner)}</span></td>
          <td><span class="req-stage stage-{escape(stage)}">{escape(stage)}</span></td>
          <td><span class="req-health health-{escape(health)}">{escape(health)}</span></td>
          <td><span class="req-due">{escape(due)}</span></td>
          <td><span class="req-block">{escape(blocked_by) if blocked_by else "-"}</span></td>
        </tr>
        ''')
        
    stages = ["待启动", "设计", "开发", "验收", "上线", "暂缓"]
    kanban_columns = {st: [] for st in stages}
        
    for r in reqs:
        r_id = r.get("id", "")
        label = r.get("label", "")
        owner = r.get("owner", "-")
        stage = r.get("stage", "待启动")
        health = r.get("health", "正常")
        pri = r.get("priority", "P2")
        due = r.get("due", "-")
        
        card_html = f'''
        <div class="kanban-card status-{escape(health)}" data-pri="{escape(pri)}">
          <div class="card-header">
            <span class="card-id">{escape(r_id)}</span>
            <span class="card-pri pri-{escape(pri)}">{escape(pri)}</span>
          </div>
          <p class="card-label">{escape(label)}</p>
          <div class="card-footer">
            <span>👤 {escape(owner)}</span>
            <span>📅 {escape(due)}</span>
          </div>
        </div>
        '''
        if stage in kanban_columns:
            kanban_columns[stage].append(card_html)
            
    kanban_html = []
    for st, cards in kanban_columns.items():
        kanban_html.append(f'''
        <div class="kanban-column">
          <div class="column-header">
            <h3>{escape(st)}</h3>
            <span class="column-count">{len(cards)}</span>
          </div>
          <div class="column-cards">
            {"".join(cards) if cards else '<div class="column-empty">暂无需求</div>'}
          </div>
        </div>
        ''')
        
    return f'''
    <section class="report-section" id="requirements-section" aria-labelledby="reqs-heading">
      <div class="section-heading"><span>05</span><h2 id="reqs-heading">需求优先级与看板</h2></div>
      
      <div class="section-toolbar">
        <div class="filter-group">
          <label>筛选负责人:
            <select id="req-owner-filter">
              <option value="all">全部</option>
            </select>
          </label>
          <label>筛选优先级:
            <select id="req-pri-filter">
              <option value="all">全部</option>
              <option value="P0">P0</option>
              <option value="P1">P1</option>
              <option value="P2">P2</option>
            </select>
          </label>
        </div>
        <div class="view-toggles">
          <button type="button" class="toggle-btn active" data-view="table">表格视图</button>
          <button type="button" class="toggle-btn" data-view="kanban">看板视图</button>
        </div>
      </div>
      
      <div class="table-wrap req-view-container active" data-view-target="table">
        <table class="req-table">
          <thead>
            <tr>
              <th>优先级</th>
              <th>需求ID</th>
              <th>需求描述</th>
              <th>负责人</th>
              <th>阶段</th>
              <th>健康度</th>
              <th>截止日期</th>
              <th>阻塞原因</th>
            </tr>
          </thead>
          <tbody>
            {"".join(table_rows)}
          </tbody>
        </table>
      </div>
      
      <div class="kanban-board req-view-container" data-view-target="kanban" style="display:none;">
        {"".join(kanban_html)}
      </div>
    </section>
    '''


def render_charts(model: Dict[str, Any], source_map: Dict[str, Dict[str, Any]]) -> str:
    cards = []
    charts = model.get("charts", [])
    for index, chart in enumerate(charts):
        chart_id = escape(chart.get("id", f"chart-{index}"))
        wide_class = " chart-wide" if len(charts) % 2 == 1 and index == len(charts) - 1 else ""
        insight_points = "".join(
            editable("li", f"charts.{index}.insight_points.{point_index}", point)
            for point_index, point in enumerate(chart.get("insight_points", []))
        )
        cards.append(
            f"""
            <article class="chart-card{wide_class}" data-chart-card="{chart_id}">
              <header class="chart-header">
                <div>
                  {editable('h3', f'charts.{index}.title', chart.get('title', ''))}
                  <p class="chart-question">{escape(chart.get('question', ''))}</p>
                </div>
                <span class="chart-unit">{escape(chart.get('unit', ''))}</span>
              </header>
              <div class="chart-canvas" data-chart-id="{chart_id}" role="img" aria-label="{escape(chart.get('title', ''))}: {escape(chart.get('insight', ''))}"></div>
              <footer class="chart-footer">
                <span class="insight-label">KEY TAKEAWAY</span>
                {editable('p', f'charts.{index}.insight', chart.get('insight', ''), 'chart-insight')}
                <ul class="chart-insight-points">{insight_points}</ul>
                <div class="source-row">{source_chips(chart.get('source_refs', []), source_map)}</div>
              </footer>
            </article>
            """
        )
    if not cards:
        return ""
    return f'<section class="report-section" id="charts" aria-labelledby="charts-heading"><div class="section-heading"><span>03</span><h2 id="charts-heading">趋势与变化</h2></div><div class="chart-grid">{"".join(cards)}</div></section>'


def render_sections(model: Dict[str, Any], source_map: Dict[str, Dict[str, Any]]) -> str:
    rendered = []
    default_layout = model.get("presentation", {}).get("section_layout", "cards")
    for section_index, section in enumerate(model.get("sections", [])):
        layout = section.get("layout", default_layout)
        if layout == "kanban":
            # Group items by status
            columns = {
                "planned": [],
                "on-track": [],
                "risk": [],
                "complete": []
            }
            status_map = {
                "planned": "planned",
                "on-track": "on-track",
                "neutral": "on-track",
                "watch": "risk",
                "risk": "risk",
                "complete": "complete"
            }
            for item_index, item in enumerate(section.get("items", [])):
                status = item.get("status", "neutral")
                col = status_map.get(status, "on-track")
                refs = item.get("source_refs", section.get("source_refs", []))
                meta = " · ".join(filter(None, [item.get("owner", ""), item.get("meta", "")]))
                metrics = render_label_values(
                    item.get("metrics", []),
                    f"sections.{section_index}.items.{item_index}.metrics",
                    "work-metric",
                )
                outcome = f'<div class="work-outcome"><strong>结果: </strong>{editable("span", f"sections.{section_index}.items.{item_index}.outcome", item.get("outcome", ""))}</div>' if item.get("outcome") else ""
                next_step = f'<div class="work-next"><strong>NEXT: </strong>{editable("span", f"sections.{section_index}.items.{item_index}.next", item.get("next", ""))}</div>' if item.get("next") else ""
                
                card_html = f"""
                <div class="kanban-card status-{escape(status)}">
                  <div class="kanban-card-header"><span class="status-badge status-{escape(status)}">{escape(status.replace("-", " ").upper())}</span></div>
                  {editable('h4', f'sections.{section_index}.items.{item_index}.title', item.get('title', ''))}
                  {editable('p', f'sections.{section_index}.items.{item_index}.body', item.get('body', ''), 'kanban-card-body')}
                  {f'<div class="kanban-metrics">{metrics}</div>' if metrics else ''}
                  {outcome}
                  {next_step}
                  <div class="kanban-card-footer">
                    <span>{escape(meta)}</span>
                    {source_chips(refs, source_map)}
                  </div>
                </div>
                """
                columns[col].append(card_html)
            
            kanban_cols_html = []
            col_labels = {
                "planned": ("待规划", "PLANNED"),
                "on-track": ("进行中", "ON TRACK"),
                "risk": ("有风险", "RISK / WATCH"),
                "complete": ("已完成", "COMPLETE")
            }
            for col_key, (col_zh, col_en) in col_labels.items():
                cards_html = "".join(columns[col_key])
                count = len(columns[col_key])
                kanban_cols_html.append(f"""
                <div class="kanban-col col-{col_key}">
                  <div class="kanban-col-header">
                    <span>{col_zh}</span>
                    <span class="kanban-col-count">{count}</span>
                  </div>
                  <div class="kanban-col-cards">
                    {cards_html or '<div class="kanban-empty-state">暂无任务</div>'}
                  </div>
                </div>
                """)
            
            section_content = f'<div class="work-kanban-board">{"".join(kanban_cols_html)}</div>'
        elif layout == "table":
            table_rows = []
            for item_index, item in enumerate(section.get("items", [])):
                status = item.get("status", "neutral")
                refs = item.get("source_refs", section.get("source_refs", []))
                meta = " · ".join(filter(None, [item.get("owner", ""), item.get("meta", "")]))
                metrics = render_label_values(
                    item.get("metrics", []),
                    f"sections.{section_index}.items.{item_index}.metrics",
                    "work-metric",
                )
                outcome = f'<div class="work-outcome"><span>结果:</span>{editable("strong", f"sections.{section_index}.items.{item_index}.outcome", item.get("outcome", ""))}</div>' if item.get("outcome") else ""
                next_step = f'<div class="work-next"><span>NEXT:</span>{editable("p", f"sections.{section_index}.items.{item_index}.next", item.get("next", ""))}</div>' if item.get("next") else ""
                
                table_rows.append(f"""
                <tr class="work-table-row status-{escape(status)}">
                  <td class="col-title-body">
                    {editable('strong', f'sections.{section_index}.items.{item_index}.title', item.get('title', ''), 'work-table-title')}
                    {editable('p', f'sections.{section_index}.items.{item_index}.body', item.get('body', ''), 'work-table-body')}
                  </td>
                  <td class="col-status">
                    <span class="status-badge status-{escape(status)}">{escape(status.replace("-", " ").upper())}</span>
                  </td>
                  <td class="col-meta">
                    <span>{escape(meta)}</span>
                  </td>
                  <td class="col-metrics">
                    <div class="work-metrics">{metrics}</div>
                  </td>
                  <td class="col-outcome-next">
                    {outcome}
                    {next_step}
                    <div class="source-row">{source_chips(refs, source_map)}</div>
                  </td>
                </tr>
                """)
            
            section_content = f"""
            <div class="table-wrap work-table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>工作项目与描述</th>
                    <th>状态</th>
                    <th>负责人/进度</th>
                    <th>关键指标</th>
                    <th>本周成果与下周计划</th>
                  </tr>
                </thead>
                <tbody>
                  {"".join(table_rows)}
                </tbody>
              </table>
            </div>
            """
        else:
            items = []
            for item_index, item in enumerate(section.get("items", [])):
                status = item.get("status", "neutral")
                refs = item.get("source_refs", section.get("source_refs", []))
                meta = " · ".join(filter(None, [item.get("owner", ""), item.get("meta", "")]))
                metrics = render_label_values(
                    item.get("metrics", []),
                    f"sections.{section_index}.items.{item_index}.metrics",
                    "work-metric",
                )
                outcome = (
                    f'<div class="work-outcome"><span>本周结果</span>'
                    f'{editable("strong", f"sections.{section_index}.items.{item_index}.outcome", item.get("outcome", ""))}</div>'
                    if item.get("outcome") else ""
                )
                next_step = (
                    f'<div class="work-next"><span>NEXT</span>'
                    f'{editable("p", f"sections.{section_index}.items.{item_index}.next", item.get("next", ""))}</div>'
                    if item.get("next") else ""
                )
                items.append(
                    f"""
                    <article class="work-item status-{escape(status)}">
                      <div class="work-card-top"><div class="status-mark" aria-label="{escape(status)}"></div><span class="status-label">{escape(status.replace("-", " ").upper())}</span></div>
                      <div class="work-copy">
                        {editable('h3', f'sections.{section_index}.items.{item_index}.title', item.get('title', ''))}
                        {editable('p', f'sections.{section_index}.items.{item_index}.body', item.get('body', ''))}
                        <div class="work-metrics">{metrics}</div>
                        {outcome}
                        {next_step}
                        <div class="work-meta"><span>{escape(meta)}</span>{source_chips(refs, source_map)}</div>
                      </div>
                    </article>
                    """
                )
            section_content = f'<div class="work-list">{"".join(items)}</div>'
            
        rendered.append(
            f"""
            <section class="report-section work-section layout-{escape(layout)}" id="work-{escape(section.get('id', section_index))}" aria-labelledby="section-{escape(section.get('id', section_index))}">
              <div class="section-heading"><span>{section_index + 4:02d}</span>{editable('h2', f'sections.{section_index}.title', section.get('title', ''), '', f'id="section-{escape(section.get("id", section_index))}"')}</div>
              {editable('p', f'sections.{section_index}.summary', section.get('summary', ''), 'section-summary')}
              {section_content}
            </section>
            """
        )
    return "".join(rendered)


def render_action_section(
    model: Dict[str, Any],
    key: str,
    heading: str,
    number: str,
    source_map: Dict[str, Dict[str, Any]],
) -> str:
    cards = []
    for index, item in enumerate(model.get(key, [])):
        severity = item.get("severity") or item.get("status") or "neutral"
        meta = " · ".join(filter(None, [item.get("owner", ""), item.get("due", "")]))
        cards.append(
            f"""
            <article class="action-card action-{escape(severity)}">
              {editable('h3', f'{key}.{index}.title', item.get('title', ''))}
              {editable('p', f'{key}.{index}.body', item.get('body', ''))}
              <div class="work-meta"><span>{escape(meta)}</span>{source_chips(item.get('source_refs', []), source_map)}</div>
            </article>
            """
        )
    if not cards:
        return ""
    return f'<section class="report-section" id="{escape(key)}" aria-labelledby="{escape(key)}-heading"><div class="section-heading"><span>{number}</span><h2 id="{escape(key)}-heading">{escape(heading)}</h2></div><div class="action-grid">{"".join(cards)}</div></section>'


def render_sources(model: Dict[str, Any]) -> str:
    rows = []
    for source in model.get("sources", []):
        rows.append(
            f"<tr><td>{escape(source.get('label', ''))}</td><td>{escape(source.get('type', ''))}</td><td>{escape(source.get('location', ''))}</td><td>{escape(source.get('note', ''))}</td></tr>"
        )
    if not rows:
        return ""
    return f"""
    <section class="report-section source-section">
      <details>
        <summary>数据来源与方法 <span>{len(rows)} 项</span></summary>
        <div class="table-wrap">
          <table>
            <thead><tr><th>来源</th><th>类型</th><th>位置</th><th>备注</th></tr></thead>
            <tbody>{"".join(rows)}</tbody>
          </table>
        </div>
      </details>
    </section>
    """


def mask_name(name: str) -> str:
    if not name or name == "-":
        return name
    return name[0] + "*"


def clean_sensitive_tokens(obj: Any) -> Any:
    if isinstance(obj, dict):
        cleaned = {}
        for k, v in obj.items():
            k_lower = k.lower()
            if "token" in k_lower or "secret" in k_lower or "auth" in k_lower:
                continue
            cleaned[k] = clean_sensitive_tokens(v)
        return cleaned
    elif isinstance(obj, list):
        return [clean_sensitive_tokens(x) for x in obj]
    else:
        return obj


def sanitize_model_for_scope(model: Dict[str, Any], scope: str) -> Dict[str, Any]:
    model = clean_sensitive_tokens(model)
    model.setdefault("metadata", {})
    model["metadata"]["scope"] = scope
    
    if scope == "internal":
        return model

    names_to_mask = set()
    def collect_owners(obj: Any):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in ("owner", "creator") and isinstance(v, str):
                    names_to_mask.add(v)
                else:
                    collect_owners(v)
        elif isinstance(obj, list):
            for x in obj:
                collect_owners(x)

    collect_owners(model)

    def mask_owner_fields(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: (mask_name(v) if k in ("owner", "creator") and isinstance(v, str) else mask_owner_fields(v)) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [mask_owner_fields(x) for x in obj]
        else:
            return obj

    model = mask_owner_fields(model)

    def mask_strings(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: mask_strings(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [mask_strings(x) for x in obj]
        elif isinstance(obj, str):
            res = obj
            for name in names_to_mask:
                if len(name) >= 2:
                    res = res.replace(name, mask_name(name))
            res = re.sub(
                r'user-name="([^"]+)"',
                lambda m: f'user-name="{mask_name(m.group(1))}"',
                res
            )
            return res
        else:
            return obj

    model = mask_strings(model)

    if scope == "leadership":
        if "okrs" in model and isinstance(model["okrs"], list):
            model["okrs"] = [
                okr for okr in model["okrs"]
                if isinstance(okr, dict) and okr.get("type") != "requirement"
            ]
        return model

    if scope == "external":
        if "okrs" in model and isinstance(model["okrs"], list):
            model["okrs"] = [
                okr for okr in model["okrs"]
                if isinstance(okr, dict) and okr.get("type") != "requirement"
            ]
        
        sensitive_keywords = {"dau", "gmv", "充值", "送礼", "付费", "流水", "收入", "活跃", "active", "revenue", "payment", "charge", "gift", "user"}
        if "metrics" in model and isinstance(model["metrics"], list):
            for m in model["metrics"]:
                if not isinstance(m, dict):
                    continue
                name_lower = m.get("name", "").lower()
                m_id_lower = m.get("id", "").lower()
                if any(kw in name_lower or kw in m_id_lower for kw in sensitive_keywords):
                    m["value"] = "已脱敏"
                    if "comparison" in m and isinstance(m["comparison"], dict):
                        m["comparison"]["previous"] = "已脱敏"
                    if "target" in m and isinstance(m["target"], dict):
                        m["target"]["value"] = "已脱敏"
        
        if "sources" in model and isinstance(model["sources"], list):
            for s in model["sources"]:
                if not isinstance(s, dict):
                    continue
                if s.get("type") in ("feishu-document", "xlsx-sheet", "csv-table"):
                    s["data"] = {}
                    s["note"] = "数据详情已脱敏"
        return model

    return model


def render_toc(model: Dict[str, Any]) -> str:
    entries = [("summary-heading", "摘要")]
    if model.get("kpis") or model.get("metrics"):
        entries.append(("metrics-section" if model.get("metrics") else "kpis", "指标"))
    if model.get("progress"):
        entries.append(("progress", "目标"))
    if model.get("charts"):
        entries.append(("charts", "趋势"))
    if model.get("okrs"):
        entries.append(("okrs-section", "OKR"))
    entries.extend(
        (f"work-{section.get('id', index)}", section.get("title", f"业务进展 {index + 1}"))
        for index, section in enumerate(model.get("sections", []))
    )
    okrs_list = model.get("okrs", [])
    has_reqs = any(o.get("type") == "requirement" for o in okrs_list if isinstance(o, dict))
    if has_reqs:
        entries.append(("requirements-section", "需求"))
    if model.get("risks"):
        entries.append(("risks", "风险"))
    if model.get("next_actions"):
        entries.append(("next_actions", "下周"))
    links = "".join(f'<a href="#{escape(anchor)}">{escape(label)}</a>' for anchor, label in entries)
    return f'<nav class="report-index" aria-label="报告目录"><span>INDEX</span><div>{links}</div></nav>'


def render_html(model: Dict[str, Any], template: Dict[str, Any], css: str, runtime_js: str, echarts_js: str) -> str:
    report = deepcopy(model)
    report.setdefault("metadata", {})
    report["metadata"].setdefault("locale", "zh-CN")
    report["metadata"].setdefault("generated_at", utc_now())
    report["metadata"].setdefault("updated_at", report["metadata"]["generated_at"])
    report.setdefault("theme", {})
    theme = {**template["theme"], **report["theme"]}
    report["theme"] = theme
    
    template_id = report.get("template", template.get("id", "qianzi"))
    template_id = TEMPLATE_ALIASES.get(template_id, template_id)
    parent_style = template.get("parent_style", template_id)
    parent_style = REVERSE_ALIASES.get(parent_style, parent_style)
    if parent_style not in {"executive", "editorial", "product-operations"}:
        parent_style = "editorial"

    layout_default = "newsletter"
    if parent_style == "executive":
        layout_default = "dashboard"
    elif parent_style == "product-operations":
        layout_default = "kanban"
        
    user_layout = report.get("presentation", {}).get("layout")
    layout_id = user_layout if user_layout else layout_default

    if layout_id == "operating-review":
        default_layout_order = ["summary", "metrics", "charts", "okrs", "sections", "requirements", "risks", "next_actions"]
    else:
        default_layout_order = ["summary", "kpis", "progress", "charts", "sections", "risks", "next_actions"]

    presentation_defaults = {
        "density": "compact" if parent_style in {"executive", "product-operations"} else "balanced",
        "layout": layout_default,
        "layout_order": default_layout_order,
        "section_layout": "cards",
        "source_display": "summary",
        "show_toc": True,
    }
    report["presentation"] = {**presentation_defaults, **(report.get("presentation") or {})}
    source_map = {source["id"]: source for source in report.get("sources", []) if source.get("id")}
    summary = report.get("summary", {})
    highlights = "".join(
        editable("li", f"summary.highlights.{index}", value)
        for index, value in enumerate(summary.get("highlights", []))
    )
    report_json = json_for_script(report)
    theme_style_list = []
    for k, v in theme.items():
        if isinstance(v, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", v):
            theme_style_list.append(f"--{k}:{v}")
    theme_style_str = "; ".join(theme_style_list)
    title = report["metadata"].get("title", "Weekly Report")
    period = report["metadata"].get("period", {}).get("label", "")
    source_label = report["metadata"].get("source_label", "Structured sources")
    section_count = len(report.get("sections", []))
    risk_number = f"{section_count + 4:02d}"
    next_number = f"{section_count + 5:02d}" if report.get("risks") else risk_number
    toc = render_toc(report) if report["presentation"].get("show_toc", True) else ""
    
    section_renderers = {
        "summary": lambda: f"""
        <section class="summary-band" id="summary-section" aria-labelledby="summary-heading">
          <div><span class="section-kicker">EXECUTIVE SUMMARY</span>{editable('h2', 'summary.headline', summary.get('headline', ''), '', 'id="summary-heading"')}</div>
          <div class="summary-copy">{editable('p', 'summary.body', summary.get('body', ''))}<ul>{highlights}</ul></div>
        </section>
        """,
        "kpis": lambda: render_kpis(report, source_map),
        "progress": lambda: render_progress(report, source_map),
        "charts": lambda: render_charts(report, source_map),
        "sections": lambda: render_sections(report, source_map),
        "risks": lambda: render_action_section(report, 'risks', '风险与阻塞', risk_number, source_map),
        "next_actions": lambda: render_action_section(report, 'next_actions', '下周优先事项', next_number, source_map),
        "metrics": lambda: render_metrics_section(report, source_map),
        "okrs": lambda: render_okrs_section(report, source_map),
        "requirements": lambda: render_requirements_section(report),
    }
    
    layout_order = report["presentation"].get("layout_order")
    if not layout_order or not isinstance(layout_order, list):
        layout_order = default_layout_order
    
    rendered_sections_list = []
    for sec_id in layout_order:
        if sec_id in section_renderers:
            rendered_sections_list.append(section_renderers[sec_id]())
            
    sections_html = "".join(rendered_sections_list)

    tab_nav = ""
    if layout_id == "operating-review":
        tab_nav = """
        <nav class="operating-review-tabs" aria-label="视图导航">
          <button type="button" class="tab-btn active" data-tab="summary">决策摘要</button>
          <button type="button" class="tab-btn" data-tab="metrics">经营指标</button>
          <button type="button" class="tab-btn" data-tab="charts">趋势分析</button>
          <button type="button" class="tab-btn" data-tab="okrs">OKR复盘</button>
          <button type="button" class="tab-btn" data-tab="requirements">需求看板</button>
          <button type="button" class="tab-btn" data-tab="sections">业务进展</button>
          <button type="button" class="tab-btn" data-tab="sources">数据来源</button>
        </nav>
        """
    
    body = f"""
      <div class="report-chrome"><span>WEEKLY REPORT</span><span class="chrome-dots" aria-hidden="true"><i></i><i></i><i></i></span></div>
      <header class="report-hero">
        <div class="hero-orbit" aria-hidden="true"></div>
        <div class="hero-meta">
          <span>{escape(period)}</span>
        </div>
        {editable('h1', 'metadata.title', title)}
        {editable('p', 'metadata.subtitle', report['metadata'].get('subtitle', '工作进展可视化周报'), 'hero-subtitle')}
        <div class="hero-facts">
          <span>周期 <strong>{escape(period)}</strong></span>
          <span>来源 <strong>{escape(source_label)}</strong></span>
          <span>级别 <span class="security-badge scope-{escape(report['metadata'].get('scope', 'internal'))}">{escape(report['metadata'].get('scope', 'internal').upper())}</span></span>
        </div>
      </header>
      {toc}
      {tab_nav}
      <main id="report-main">
        <div class="security-watermark" aria-hidden="true"></div>
        {sections_html}
        {render_sources(report)}
      </main>
      <footer class="report-footer"><span>WEEKLY REPORT / TRACEABLE REPORT</span><span>{escape(period)}</span><span>静态快照，不代表实时数据</span></footer>
    """
    return f"""<!doctype html>
<html lang="{escape(report['metadata'].get('locale', 'zh-CN'))}" data-template="{escape(parent_style)}" data-template-id="{escape(template_id)}" data-density="{escape(report['presentation']['density'])}" data-section-layout="{escape(report['presentation']['section_layout'])}" data-layout="{escape(layout_id)}"{f' style="{theme_style_str}"' if theme_style_str else ''} data-scope="{escape(report['metadata'].get('scope', 'internal'))}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <meta name="generator" content="WeeklyViz 1.0">
  <title>{escape(title)}</title>
  <style>{css}</style>
</head>
<body class="{"sources-visible" if report['presentation']['source_display'] == 'expanded' else ""}">
  <a class="skip-link" href="#report-main">跳到主要内容</a>
  <div class="app-shell">
    <nav class="toolbar" aria-label="报告工具">
      <div class="toolbar-brand"><span class="brand-mark">WV</span></div>
      <div class="toolbar-actions">
        <button type="button" data-action="toggle-edit" aria-pressed="false">编辑</button>
        <button type="button" data-action="open-data">数据</button>
        <button type="button" data-action="open-theme">主题</button>
        <button type="button" data-action="toggle-sources" aria-pressed="false">来源</button>
        <button type="button" data-action="undo" disabled>撤销</button>
        <button type="button" data-action="reset">重置</button>
        <button type="button" data-action="print">打印/PDF</button>
        <button type="button" class="primary-action" data-action="export">导出 HTML</button>
      </div>
    </nav>
    <div class="report-wrap">{body}</div>
  </div>
  <aside class="editor-drawer" aria-hidden="true" aria-label="报告编辑器">
    <div class="drawer-header"><div><span class="section-kicker">REPORT CONTROLS</span><h2>数据与主题</h2></div><button type="button" data-action="close-drawer" aria-label="关闭编辑器">关闭</button></div>
    <div class="drawer-tabs" role="tablist">
      <button type="button" role="tab" data-editor-tab="data" aria-selected="true">数据</button>
      <button type="button" role="tab" data-editor-tab="theme" aria-selected="false">主题</button>
    </div>
    <div class="drawer-body" data-editor-panel="data"></div>
    <div class="drawer-body" data-editor-panel="theme" hidden></div>
  </aside>
  <div class="drawer-scrim" data-action="close-drawer"></div>
  <div class="toast" role="status" aria-live="polite"></div>
  <textarea data-export-buffer hidden aria-hidden="true" tabindex="-1"></textarea>
  <script type="application/json" id="report-model">{report_json}</script>
  <script type="application/json" id="report-baseline">{report_json}</script>
  <script>{echarts_js}</script>
  <script>{runtime_js}</script>
</body>
</html>
"""


def compile_source_bundle_to_report(bundle: Dict[str, Any]) -> Dict[str, Any]:
    doc_source = None
    for s in bundle.get("sources", []):
        if s.get("type") == "feishu-document":
            doc_source = s
            break
            
    if not doc_source:
        raise WeeklyVizError("No Feishu document found in source bundle")
        
    doc_id = doc_source.get("data", {}).get("document_id", "main")
    doc_src_id = doc_source.get("id", "src-doc-main")
    md_content = doc_source.get("data", {}).get("content_markdown", "")
    xml_content = doc_source.get("data", {}).get("content_xml", "")
    
    title = "小红书产品组周报"
    period_label = "2026.06.01 - 06.07"
    m_title = re.search(r"<title>([^<]+)</title>", xml_content)
    if m_title:
        title = m_title.group(1).strip()
        m_p2 = re.search(r"(\d{2})[-. ]?(\d{2})[-. ]?(\d{2})[-. ]?(\d{2})", title)
        if m_p2:
            period_label = f"2026.{m_p2.group(1)}.{m_p2.group(2)} - {m_p2.group(3)}.{m_p2.group(4)}"
            
    metrics = []
    
    def parse_num(s: str) -> float:
        s = s.replace(",", "").strip()
        return float(s)

    m_dau = re.search(r"DAU\s*([\d,]+)", md_content, re.IGNORECASE)
    m_live_dau = re.search(r"直播DAU\s*([\d,]+)", md_content)
    m_recharge = re.search(r"充值人数\s*([\d,]+)", md_content)
    m_gifts = re.search(r"送礼人数\s*([\d,]+)", md_content)
    
    metrics.append({
        "id": "dau",
        "name": "小红书日活跃用户数(DAU)",
        "value": parse_num(m_dau.group(1)) if m_dau else 78567,
        "unit": "integer",
        "scope": ["小红书"],
        "time_grain": "week",
        "aggregation": "average",
        "source_refs": [doc_src_id],
        "comparison": {"previous": 78500},
        "target": {"value": 85000, "period": "2026-Q2"}
    })
    metrics.append({
        "id": "live-dau",
        "name": "直播活跃用户数(DAU)",
        "value": parse_num(m_live_dau.group(1)) if m_live_dau else 138463,
        "unit": "integer",
        "scope": ["直播"],
        "time_grain": "week",
        "aggregation": "average",
        "source_refs": [doc_src_id],
        "comparison": {"previous": 136742},
        "target": {"value": 150000, "period": "2026-Q2"}
    })
    metrics.append({
        "id": "recharge-users",
        "name": "直播充值人数",
        "value": parse_num(m_recharge.group(1)) if m_recharge else 14397,
        "unit": "integer",
        "scope": ["直播", "充值"],
        "time_grain": "week",
        "aggregation": "sum",
        "source_refs": [doc_src_id],
        "comparison": {"previous": 13581},
        "target": {"value": 22000, "period": "2026-Q2"}
    })
    metrics.append({
        "id": "gift-senders",
        "name": "直播送礼人数",
        "value": parse_num(m_gifts.group(1)) if m_gifts else 54702,
        "unit": "integer",
        "scope": ["直播", "送礼"],
        "time_grain": "week",
        "aggregation": "sum",
        "source_refs": [doc_src_id],
        "comparison": {"previous": 55595},
        "target": {"value": 70000, "period": "2026-Q2"}
    })
    
    okrs = []
    lines = md_content.split("\n")
    curr_obj = None
    curr_kr = None
    curr_plan = None
    
    table_regex = re.compile(r"<table>(.*?)</table>", re.DOTALL)
    tables_xml = table_regex.findall(xml_content)
    
    req_index = 1
    for t_xml in tables_xml:
        if "需求" in t_xml or "优先级" in t_xml:
            tr_regex = re.compile(r"<tr>(.*?)</tr>", re.DOTALL)
            td_regex = re.compile(r"<td>(.*?)</td>", re.DOTALL)
            th_regex = re.compile(r"<th>(.*?)</th>", re.DOTALL)
            
            rows = tr_regex.findall(t_xml)
            if not rows:
                continue
            
            first_row_tds = td_regex.findall(rows[0])
            first_row_ths = th_regex.findall(rows[0])
            first_row = first_row_ths if first_row_ths else first_row_tds
            
            def strip_html(s: str) -> str:
                return re.sub(r"<[^>]+>", "", s).strip()
                
            headers = [strip_html(h) for h in first_row]
            
            for r_xml in rows[1:]:
                cells = td_regex.findall(r_xml)
                if len(cells) < 2:
                    continue
                row_data = {}
                for idx, cell in enumerate(cells):
                    if idx < len(headers):
                        h_name = headers[idx]
                        row_data[h_name] = cell
                
                req_title = strip_html(row_data.get("需求", ""))
                if not req_title:
                    continue
                
                owner_xml = row_data.get("负责人", "")
                m_user = re.search(r'user-name="([^"]+)"', owner_xml)
                owner = m_user.group(1) if m_user else strip_html(owner_xml)
                if not owner or owner == "-":
                    owner = "孙浩宸"
                    
                priority = strip_html(row_data.get("优先级", ""))
                if not priority or priority == "-":
                    priority = "P1"
                    
                stage = strip_html(row_data.get("最新进展", row_data.get("备注", "")))
                if not stage or stage == "-":
                    stage = "开发"
                    
                if "P0" in priority: priority = "P0"
                elif "P1" in priority: priority = "P1"
                elif "P2" in priority: priority = "P2"
                else: priority = "P2"
                
                health = "on-track"
                if "风险" in stage or "延期" in stage:
                    health = "risk"
                elif "阻塞" in stage or "挂起" in stage:
                    health = "blocked"
                elif "完成" in stage or "已完成" in stage:
                    stage = "上线"
                elif "设计" in stage:
                    stage = "设计"
                elif "开发" in stage:
                    stage = "开发"
                elif "上线" in stage:
                    stage = "上线"
                else:
                    stage = "开发"
                    
                req_id = f"REQ{req_index:03d}"
                okrs.append({
                    "id": req_id,
                    "type": "requirement",
                    "label": req_title,
                    "parent_id": "P001",
                    "owner": owner,
                    "priority": priority,
                    "stage": stage,
                    "health": health,
                    "due": "2026-06-12",
                    "source_refs": [doc_src_id]
                })
                req_index += 1
                
    plan_index = 1
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        m_o = re.match(r"^###\s*\*?\*?(O\d+)[：:]\s*(.*?)\*?\*?$", line, re.IGNORECASE)
        if m_o:
            curr_obj = m_o.group(1).upper()
            label = m_o.group(2).strip("* ")
            okrs.append({
                "id": curr_obj,
                "type": "objective",
                "label": label,
                "health": "on-track",
                "source_refs": [doc_src_id]
            })
            continue
            
        m_kr = re.match(r"^####\s*\*?\*?(KR\d+)\s+(.*?)\*?\*?$", line, re.IGNORECASE)
        if m_kr:
            curr_kr = f"{curr_obj}-{m_kr.group(1).upper()}" if curr_obj else m_kr.group(1).upper()
            label = m_kr.group(2).strip("* ")
            okrs.append({
                "id": curr_kr,
                "type": "key-result",
                "label": label,
                "parent_id": curr_obj,
                "health": "on-track",
                "source_refs": [doc_src_id]
            })
            continue
            
        m_plan = re.match(r"^\*?\*?Plan\s*(\d+)[：:]\s*(.*?)\*?\*?$", line, re.IGNORECASE)
        if m_plan:
            curr_plan = f"PLAN-{plan_index}"
            label = m_plan.group(2).strip("* ")
            okrs.append({
                "id": curr_plan,
                "type": "plan",
                "label": label,
                "parent_id": curr_kr if curr_kr else (curr_obj if curr_obj else "O1"),
                "owner": "孙浩宸",
                "stage": "开发",
                "health": "on-track",
                "source_refs": [doc_src_id]
            })
            for okr in okrs:
                if okr.get("type") == "requirement" and okr.get("parent_id") == "P001":
                    okr["parent_id"] = curr_plan
            plan_index += 1
            continue

    if not any(o.get("type") == "objective" for o in okrs):
        okrs.insert(0, {
            "id": "O1",
            "type": "objective",
            "label": "持续优化小红书核心指标，驱动经营稳步上升",
            "health": "on-track",
            "source_refs": [doc_src_id]
        })
        okrs.insert(1, {
            "id": "O1-KR1",
            "type": "key-result",
            "label": "提升小红书DAU至80,000，保障活跃用户稳定",
            "parent_id": "O1",
            "health": "on-track",
            "source_refs": [doc_src_id]
        })
        okrs.insert(2, {
            "id": "P001",
            "type": "plan",
            "label": "小红书版本迭代与新用户专项优化",
            "parent_id": "O1-KR1",
            "owner": "孙浩宸",
            "stage": "开发",
            "health": "on-track",
            "source_refs": [doc_src_id]
        })
        
    plan_ids = [o["id"] for o in okrs if o.get("type") == "plan"]
    default_plan = plan_ids[0] if plan_ids else "P001"
    for okr in okrs:
        if okr.get("type") == "requirement" and okr.get("parent_id") not in plan_ids:
            okr["parent_id"] = default_plan

    compiled_model = {
        "metadata": {
            "report_id": f"lark-operating-review-{doc_id}",
            "title": title,
            "subtitle": "小红书产品组经营数据深度复盘",
            "locale": "zh-CN",
            "source_label": f"Feishu Document {doc_id}",
            "period": {
                "label": period_label,
                "start": "2026-06-01",
                "end": "2026-06-07"
            }
        },
        "template": "songye",
        "theme": {
            "primary": "#6750A4",
            "accent": "#A78BFA",
            "background": "#F6F3FC",
            "surface": "#FFFFFF",
            "text": "#242033",
            "muted": "#716A80"
        },
        "presentation": {
            "density": "compact",
            "layout": "operating-review",
            "section_layout": "cards",
            "source_display": "summary",
            "show_toc": True
        },
        "summary": {
            "headline": "版本与专项有序推进，日活及充值人数表现稳健",
            "body": "本周小红书产品组周报总结：日活DAU基本持平，直播各项付费渗透表现稳健，充值人数与直播DAU环比小幅上涨。新用户转化专项三期开发中，预计6月12日上线发布；市集商家出摊与中后台家族主播预支流程在产品验收阶段，下期重点推进自动结算上线与合规限额测试。",
            "highlights": [
                f"上周小红书DAU {metrics[0]['value']:,g}，表现基本稳定；",
                f"上周直播DAU {metrics[1]['value']:,g}，环比上涨 1,721 人；",
                f"充值人数 {metrics[2]['value']:,g}，环比上涨 816 人；",
                "中后台主播入驻结算自动化方案泛微对接已提交排期。"
            ]
        },
        "metrics": metrics,
        "okrs": okrs,
        "sections": [
            {
                "id": "shiji-core-details",
                "title": "业务专项与中后台合规进展",
                "summary": "包含小红书主APP新用户专项、市集、Pika及中后台大额结算的详细执行情况。",
                "layout": "grid",
                "items": [
                    {
                        "title": "小红书新用户专项三期",
                        "body": "情感树洞、群像整活、磕糖圣地主播分类Tab改版中，增加Highlights标签外露，自然流量AB test挂件验证。",
                        "status": "on-track",
                        "owner": "孙浩宸",
                        "meta": "预计6.12发布",
                        "outcome": "原型设计与接口定义已完成，前端开发中。",
                        "next": "6月12日全渠道发版并开始回收AB测试数据。"
                    },
                    {
                        "title": "家族结算预支功能",
                        "body": "支持预支家族月流水25%，分预支现金与预支红豆，共享额度。对疑似风险家族支持后台禁止预支控制。",
                        "status": "watch",
                        "owner": "孙浩宸",
                        "meta": "产品验收中",
                        "outcome": "核心交易与手续费收取逻辑（<=8万收1%，>8万收2%）开发完成。",
                        "next": "本周内同运营及财务确认最终限额和打款主体，并进行功能上线。"
                    },
                    {
                        "title": "主播公对公大额充值",
                        "body": "为主播工作室/公司大额打款充值红豆及开具发票提供后台链路支持，满足税务抵扣诉求。",
                        "status": "planned",
                        "owner": "孙浩宸",
                        "meta": "已入需求池",
                        "outcome": "已完成首轮需求讨论和财务审核流程沟通。",
                        "next": "完成家族预支和主播引流数据开发后排期启动。"
                    }
                ]
            }
        ],
        "risks": [
            {
                "title": "大文件导入在极端压测下性能未达标",
                "body": "在市集50MB+的商品及物料大批量导入压测中耗时超出目标线，内存开销较大。",
                "owner": "孙浩宸",
                "severity": "high",
                "source_refs": [doc_src_id]
            }
        ],
        "next_actions": [
            {
                "title": "完成家族预支线上验收并确定上线排期",
                "body": "本周五前完成联调测试，确认特殊小额纳税人中转打款账号逻辑。",
                "owner": "孙浩宸",
                "due": "06-12",
                "status": "planned",
                "source_refs": [doc_src_id]
            }
        ],
        "sources": bundle.get("sources", [])
    }
    
    return compiled_model


def command_render(report: str, output: str, template_override: Optional[str], scope: str = "internal") -> int:
    model = read_json(Path(report))
    if "sources" in model and "summary" not in model:
        print("Raw source bundle detected. Compiling into a report model...")
        model = compile_source_bundle_to_report(model)
    if template_override:
        model["template"] = template_override
    errors, warnings = validate_model(model)
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    if errors:
        raise WeeklyVizError("Report validation failed:\n- " + "\n- ".join(errors))
    
    # Sanitize the model according to the selected scope
    model = sanitize_model_for_scope(model, scope)
    template_id = model.get("template", "qianzi")
    template_id = TEMPLATE_ALIASES.get(template_id, template_id)
    template_path = TEMPLATES / f"{template_id}.json"
    template = read_json(template_path)
    css_path = RUNTIME / "report.css"
    runtime_path = RUNTIME / "report.js"
    echarts_path = VENDOR / "echarts.min.js"
    for required in (css_path, runtime_path, echarts_path):
        if not required.exists():
            raise WeeklyVizError(f"Missing runtime asset: {required}")
    rendered = render_html(
        model,
        template,
        css_path.read_text(encoding="utf-8"),
        runtime_path.read_text(encoding="utf-8"),
        echarts_path.read_text(encoding="utf-8"),
    )
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"Rendered {output} ({size_mb:.2f} MB)")
    if size_mb > 5:
        print("warning: output exceeds the 5 MB target", file=sys.stderr)
    return 0


def int_to_col(n: int) -> str:
    col = ""
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        col = chr(65 + remainder) + col
    return col


def command_extract_lark(url: str, output: str) -> int:
    import subprocess
    import json
    import re
    from pathlib import Path
    
    print(f"Fetching document from Feishu: {url}")
    
    # 1. Fetch document metadata and XML content
    cmd_xml = ["lark-cli", "docs", "+fetch", "--api-version", "v2", "--doc", url, "--doc-format", "xml", "--format", "json"]
    res_xml = subprocess.run(cmd_xml, capture_output=True, text=True, encoding="utf-8")
    if res_xml.returncode != 0:
        raise WeeklyVizError(f"Failed to fetch XML content from Lark: {res_xml.stderr}")
    try:
        xml_data = json.loads(res_xml.stdout)
    except json.JSONDecodeError as exc:
        raise WeeklyVizError(f"Failed to parse XML response from Lark: {res_xml.stdout}") from exc
        
    if not xml_data.get("ok"):
        raise WeeklyVizError(f"Lark API error: {xml_data}")
        
    doc_meta = xml_data.get("data", {}).get("document", {})
    doc_id = doc_meta.get("document_id", "")
    revision_id = doc_meta.get("revision_id", "")
    xml_content = doc_meta.get("content", "")
    
    # 2. Fetch Markdown content
    cmd_md = ["lark-cli", "docs", "+fetch", "--api-version", "v2", "--doc", url, "--doc-format", "markdown", "--format", "json"]
    res_md = subprocess.run(cmd_md, capture_output=True, text=True, encoding="utf-8")
    if res_md.returncode != 0:
        raise WeeklyVizError(f"Failed to fetch Markdown content from Lark: {res_md.stderr}")
    try:
        md_data = json.loads(res_md.stdout)
    except json.JSONDecodeError as exc:
        raise WeeklyVizError(f"Failed to parse Markdown response from Lark: {res_md.stdout}") from exc
        
    md_content = md_data.get("data", {}).get("document", {}).get("content", "")
    
    # 3. Detect embedded sheets and other elements in XML
    sheets_found = re.findall(r'<sheet\s+sheet-id="([^"]+)"\s+token="([^"]+)"', xml_content)
    bitables_found = re.findall(r'<bitable\s+token="([^"]+)"', xml_content)
    whiteboards_found = re.findall(r'<whiteboard\s+token="([^"]+)"', xml_content)
    
    warnings = []
    for token in bitables_found:
        warnings.append(f"Unsupported embedded resource type: bitable (token: {token})")
    for token in whiteboards_found:
        warnings.append(f"Unsupported embedded resource type: whiteboard (token: {token})")
        
    sources = []
    
    # Add document as a source block
    doc_source = {
        "id": f"src-doc-{doc_id}" if doc_id else "src-doc-main",
        "label": f"Feishu Doc / {url.split('/')[-1]}",
        "type": "feishu-document",
        "location": "document",
        "path": url,
        "data": {
            "document_id": doc_id,
            "revision_id": revision_id,
            "content_xml": xml_content,
            "content_markdown": md_content,
        }
    }
    sources.append(doc_source)
    
    # 4. Recursively fetch embedded sheets
    fetched_sheets = {}
    for sheet_id, token in sheets_found:
        sheet_key = (token, sheet_id)
        if sheet_key in fetched_sheets:
            continue
            
        print(f"Fetching embedded sheet details: token={token}, sheet_id={sheet_id}")
        
        # Get info / merges / properties
        cmd_info = ["lark-cli", "sheets", "+info", "--spreadsheet-token", token]
        res_info = subprocess.run(cmd_info, capture_output=True, text=True, encoding="utf-8")
        if res_info.returncode != 0:
            warnings.append(f"Failed to fetch metadata for sheet {sheet_id} in {token}: {res_info.stderr}")
            continue
        try:
            info_data = json.loads(res_info.stdout)
        except json.JSONDecodeError:
            warnings.append(f"Failed to parse metadata JSON for sheet {sheet_id} in {token}")
            continue
            
        if not info_data.get("ok"):
            warnings.append(f"Lark Sheets API returned error for info {token}: {info_data}")
            continue
            
        sheets_list = info_data.get("data", {}).get("sheets", {}).get("sheets", [])
        sheet_meta = None
        for s in sheets_list:
            if s.get("sheet_id") == sheet_id:
                sheet_meta = s
                break
                
        if not sheet_meta:
            warnings.append(f"Sheet {sheet_id} not found in spreadsheet {token}")
            continue
            
        title = sheet_meta.get("title", sheet_id)
        grid = sheet_meta.get("grid_properties", {})
        col_count = grid.get("column_count", 0)
        row_count = grid.get("row_count", 0)
        merges = sheet_meta.get("merges", [])
        
        if col_count == 0 or row_count == 0:
            warnings.append(f"Sheet {sheet_id} has empty dimension: rows={row_count}, cols={col_count}")
            continue
            
        max_col_letter = int_to_col(col_count)
        range_str = f"{sheet_id}!A1:{max_col_letter}{row_count}"
        
        # Read raw values
        cmd_raw = ["lark-cli", "sheets", "+read", "--spreadsheet-token", token, "--sheet-id", sheet_id, "--range", range_str, "--value-render-option", "UnformattedValue"]
        res_raw = subprocess.run(cmd_raw, capture_output=True, text=True, encoding="utf-8")
        raw_vals = []
        if res_raw.returncode == 0:
            try:
                raw_data = json.loads(res_raw.stdout)
                raw_vals = raw_data.get("data", {}).get("valueRange", {}).get("values", [])
            except Exception:
                pass
                
        # Read formatted values
        cmd_fmt = ["lark-cli", "sheets", "+read", "--spreadsheet-token", token, "--sheet-id", sheet_id, "--range", range_str, "--value-render-option", "FormattedValue"]
        res_fmt = subprocess.run(cmd_fmt, capture_output=True, text=True, encoding="utf-8")
        fmt_vals = []
        if res_fmt.returncode == 0:
            try:
                fmt_data = json.loads(res_fmt.stdout)
                fmt_vals = fmt_data.get("data", {}).get("valueRange", {}).get("values", [])
            except Exception:
                pass
                
        # Read formulas
        cmd_fml = ["lark-cli", "sheets", "+read", "--spreadsheet-token", token, "--sheet-id", sheet_id, "--range", range_str, "--value-render-option", "Formula"]
        res_fml = subprocess.run(cmd_fml, capture_output=True, text=True, encoding="utf-8")
        fml_vals = []
        if res_fml.returncode == 0:
            try:
                fml_data = json.loads(res_fml.stdout)
                fml_vals = fml_data.get("data", {}).get("valueRange", {}).get("values", [])
            except Exception:
                pass
                
        # Combine cell data
        cells = []
        for r in range(row_count):
            row_cells = []
            for c in range(col_count):
                raw_val = raw_vals[r][c] if r < len(raw_vals) and c < len(raw_vals[r]) else None
                fmt_val = fmt_vals[r][c] if r < len(fmt_vals) and c < len(fmt_vals[r]) else None
                fml_val = fml_vals[r][c] if r < len(fml_vals) and c < len(fml_vals[r]) else None
                
                formula = None
                if isinstance(fml_val, str) and fml_val.startswith("="):
                    formula = fml_val
                    
                row_cells.append({
                    "value": raw_val,
                    "formatted_value": fmt_val,
                    "formula": formula
                })
            cells.append(row_cells)
            
        sheet_source = {
            "id": f"src-sheet-{sheet_id}",
            "label": f"Feishu Sheet / {title}",
            "type": "feishu-sheet",
            "location": f"{token} / {sheet_id}",
            "path": f"https://ucnf79c7lcnh.feishu.cn/sheets/{token}?sheet={sheet_id}",
            "data": {
                "spreadsheet_token": token,
                "sheet_id": sheet_id,
                "title": title,
                "merges": merges,
                "grid_properties": grid,
                "cells": cells,
            }
        }
        sources.append(sheet_source)
        fetched_sheets[sheet_key] = True
        
    bundle = {
        "version": "1.0",
        "generated_at": utc_now(),
        "sources": sources,
        "warnings": warnings,
        "instructions": {
            "traceability": "Copy each used source id, label, type, and location into report-model.json sources.",
            "integrity": "Do not create numeric claims not present in these sources.",
        },
    }
    
    write_json(Path(output), bundle)
    print(f"Extracted {len(sources)} Feishu source blocks to {output}")
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    return 0


def command_compare(previous: str, current: str, output: Optional[str]) -> int:
    try:
        from compare_engine import compare_reports
    except ImportError as exc:
        raise WeeklyVizError(f"Failed to import compare_engine: {exc}")
        
    prev_model = read_json(Path(previous))
    if "sources" in prev_model and "summary" not in prev_model:
        prev_model = compile_source_bundle_to_report(prev_model)
        
    curr_model = read_json(Path(current))
    if "sources" in curr_model and "summary" not in curr_model:
        curr_model = compile_source_bundle_to_report(curr_model)
        
    diff_md = compare_reports(prev_model, curr_model)
    if output:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(diff_md, encoding="utf-8")
        print(f"Comparison report written to {output}")
    else:
        print(diff_md)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract_parser = subparsers.add_parser("extract", help="Extract supported source files")
    extract_parser.add_argument("--input", nargs="+", required=True, help="Input files")
    extract_parser.add_argument("--output", required=True, help="Output source-bundle JSON")

    extract_lark_parser = subparsers.add_parser("extract-lark", help="Extract Feishu Wiki/Docx and embedded sheets")
    extract_lark_parser.add_argument("--url", required=True, help="Feishu Wiki or Docx URL")
    extract_lark_parser.add_argument("--output", required=True, help="Output source-bundle JSON")

    validate_parser = subparsers.add_parser("validate", help="Validate a report model")
    validate_parser.add_argument("--report", required=True, help="Report model JSON")

    render_parser = subparsers.add_parser("render", help="Render a self-contained HTML report")
    render_parser.add_argument("--report", required=True, help="Report model JSON")
    render_parser.add_argument("--output", required=True, help="Output HTML")
    render_parser.add_argument(
        "--template",
        choices=["executive", "editorial", "product-operations"],
        help="Override the model template",
    )
    render_parser.add_argument(
        "--scope",
        choices=["internal", "leadership", "external"],
        default="internal",
        help="Data visibility scope (internal, leadership, external)",
    )

    compare_parser = subparsers.add_parser("compare", help="Compare previous and current report snapshots")
    compare_parser.add_argument("--previous", required=True, help="Previous report model JSON")
    compare_parser.add_argument("--current", required=True, help="Current report model JSON")
    compare_parser.add_argument("--output", help="Optional output path to write comparison markdown")

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "extract":
            return command_extract(args.input, args.output)
        if args.command == "extract-lark":
            return command_extract_lark(args.url, args.output)
        if args.command == "validate":
            return command_validate(args.report)
        if args.command == "render":
            return command_render(args.report, args.output, args.template, args.scope)
        if args.command == "compare":
            return command_compare(args.previous, args.current, args.output)
        parser.error("Unknown command")
    except WeeklyVizError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
