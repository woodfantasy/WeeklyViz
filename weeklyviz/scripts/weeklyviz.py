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
    if template not in {"executive", "editorial", "product-operations"}:
        errors.append("template must be executive, editorial, or product-operations")

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
            "section_layout": {"cards", "grid", "list"},
            "source_display": {"summary", "expanded"},
        }
        for key, allowed in allowed_presentation.items():
            if key in presentation and presentation[key] not in allowed:
                errors.append(f"presentation.{key} must be one of {', '.join(sorted(allowed))}")
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
        if section.get("layout") not in {None, "cards", "grid", "list"}:
            errors.append(f"sections[{index}].layout must be cards, grid, or list")
        if not isinstance(section.get("items", []), list):
            errors.append(f"sections[{index}].items must be an array")

    if not model.get("kpis") and not model.get("charts") and not model.get("progress"):
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
        items = []
        layout = section.get("layout", default_layout)
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
        rendered.append(
            f"""
            <section class="report-section work-section layout-{escape(layout)}" id="work-{escape(section.get('id', section_index))}" aria-labelledby="section-{escape(section.get('id', section_index))}">
              <div class="section-heading"><span>{section_index + 4:02d}</span>{editable('h2', f'sections.{section_index}.title', section.get('title', ''), '', f'id="section-{escape(section.get("id", section_index))}"')}</div>
              {editable('p', f'sections.{section_index}.summary', section.get('summary', ''), 'section-summary')}
              <div class="work-list">{"".join(items)}</div>
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


def render_toc(model: Dict[str, Any]) -> str:
    entries = [("summary-heading", "摘要")]
    if model.get("kpis"):
        entries.append(("kpis", "指标"))
    if model.get("progress"):
        entries.append(("progress", "目标"))
    if model.get("charts"):
        entries.append(("charts", "趋势"))
    entries.extend(
        (f"work-{section.get('id', index)}", section.get("title", f"业务进展 {index + 1}"))
        for index, section in enumerate(model.get("sections", []))
    )
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
    presentation_defaults = {
        "density": "compact" if report.get("template") in {"executive", "product-operations"} else "balanced",
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
    template_id = report.get("template", template["id"])
    title = report["metadata"].get("title", "Weekly Report")
    period = report["metadata"].get("period", {}).get("label", "")
    source_label = report["metadata"].get("source_label", "Structured sources")
    section_count = len(report.get("sections", []))
    risk_number = f"{section_count + 4:02d}"
    next_number = f"{section_count + 5:02d}" if report.get("risks") else risk_number
    toc = render_toc(report) if report["presentation"].get("show_toc", True) else ""
    body = f"""
      <div class="report-chrome"><span>WEEKLYVIZ_REPORT / {escape(template_id).upper()}</span><span class="chrome-dots" aria-hidden="true"><i></i><i></i><i></i></span></div>
      <header class="report-hero">
        <div class="hero-orbit" aria-hidden="true"></div>
        <div class="hero-meta">
          <span>WEEKLYVIZ / {escape(template["label"]).upper()}</span>
          <span>{escape(period)}</span>
        </div>
        {editable('h1', 'metadata.title', title)}
        {editable('p', 'metadata.subtitle', report['metadata'].get('subtitle', '工作进展可视化周报'), 'hero-subtitle')}
        <div class="hero-facts">
          <span>周期 <strong>{escape(period)}</strong></span>
          <span>来源 <strong>{escape(source_label)}</strong></span>
          <span>状态 <strong>LIVE REPORT</strong></span>
        </div>
      </header>
      {toc}
      <main id="report-main">
        <section class="summary-band" aria-labelledby="summary-heading">
          <div><span class="section-kicker">EXECUTIVE SUMMARY</span>{editable('h2', 'summary.headline', summary.get('headline', ''), '', 'id="summary-heading"')}</div>
          <div class="summary-copy">{editable('p', 'summary.body', summary.get('body', ''))}<ul>{highlights}</ul></div>
        </section>
        {render_kpis(report, source_map)}
        {render_progress(report, source_map)}
        {render_charts(report, source_map)}
        {render_sections(report, source_map)}
        {render_action_section(report, 'risks', '风险与阻塞', risk_number, source_map)}
        {render_action_section(report, 'next_actions', '下周优先事项', next_number, source_map)}
        {render_sources(report)}
      </main>
      <footer class="report-footer"><span>WEEKLYVIZ / TRACEABLE REPORT</span><span>{escape(period)}</span></footer>
    """
    return f"""<!doctype html>
<html lang="{escape(report['metadata'].get('locale', 'zh-CN'))}" data-template="{escape(template_id)}" data-density="{escape(report['presentation']['density'])}" data-section-layout="{escape(report['presentation']['section_layout'])}">
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
      <div class="toolbar-brand"><span class="brand-mark">WV</span><span>WeeklyViz</span></div>
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


def command_render(report: str, output: str, template_override: Optional[str]) -> int:
    model = read_json(Path(report))
    if template_override:
        model["template"] = template_override
    errors, warnings = validate_model(model)
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    if errors:
        raise WeeklyVizError("Report validation failed:\n- " + "\n- ".join(errors))
    template_id = model.get("template", "editorial")
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract_parser = subparsers.add_parser("extract", help="Extract supported source files")
    extract_parser.add_argument("--input", nargs="+", required=True, help="Input files")
    extract_parser.add_argument("--output", required=True, help="Output source-bundle JSON")

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
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "extract":
            return command_extract(args.input, args.output)
        if args.command == "validate":
            return command_validate(args.report)
        if args.command == "render":
            return command_render(args.report, args.output, args.template)
        parser.error("Unknown command")
    except WeeklyVizError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
