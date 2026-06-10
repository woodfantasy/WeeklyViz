import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("weeklyviz_cli", ROOT / "scripts" / "weeklyviz.py")
weeklyviz = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(weeklyviz)


def write_minimal_xlsx(path: Path) -> None:
    content_types = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>"""
    root_rels = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""
    workbook = """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="Metrics" sheetId="1" r:id="rId1"/></sheets>
</workbook>"""
    workbook_rels = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>"""
    sheet = """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row r="1"><c r="A1" t="inlineStr"><is><t>日期</t></is></c><c r="B1" t="inlineStr"><is><t>请求量</t></is></c></row>
    <row r="2"><c r="A2" t="inlineStr"><is><t>01-14</t></is></c><c r="B2"><v>4321</v></c></row>
  </sheetData>
</worksheet>"""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/worksheets/sheet1.xml", sheet)


def write_minimal_docx(path: Path) -> None:
    content_types = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""
    document = """<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>本周进展</w:t></w:r></w:p>
    <w:p><w:r><w:t>完成缓存策略灰度验证。</w:t></w:r></w:p>
    <w:tbl><w:tr><w:tc><w:p><w:r><w:t>项目</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>状态</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
  </w:body>
</w:document>"""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("word/document.xml", document)


class WeeklyVizTests(unittest.TestCase):
    def test_extract_supported_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            csv_path = base / "metrics.csv"
            csv_path.write_text("日期,请求量\n01-14,4321\n", encoding="utf-8")
            md_path = base / "update.md"
            md_path.write_text("# 进展\n完成测试发布。\n\n# 风险\n性能仍需验证。\n", encoding="utf-8")
            text_path = base / "notes.txt"
            text_path.write_text("第一段。\n\n第二段。", encoding="utf-8")
            xlsx_path = base / "metrics.xlsx"
            docx_path = base / "update.docx"
            write_minimal_xlsx(xlsx_path)
            write_minimal_docx(docx_path)

            sources = []
            for path in (csv_path, md_path, text_path, xlsx_path, docx_path):
                sources.extend(weeklyviz.extract_file(path))

            types = {source["type"] for source in sources}
            self.assertIn("csv-table", types)
            self.assertIn("markdown-section", types)
            self.assertIn("text", types)
            self.assertIn("xlsx-sheet", types)
            self.assertIn("docx-section", types)
            self.assertIn("docx-table", types)
            self.assertTrue(all(source["id"].startswith("src-") for source in sources))

    def test_golden_model_validates(self):
        model = weeklyviz.read_json(ROOT / "evals" / "fixtures" / "report-model.json")
        errors, warnings = weeklyviz.validate_model(model)
        self.assertEqual([], errors)
        self.assertEqual([], warnings)
        self.assertIs(model["metadata"].get("synthetic"), True)
        self.assertIn("Synthetic", model["metadata"].get("source_label", ""))
        self.assertTrue(all("虚构" in source.get("note", "") for source in model["sources"]))

    def test_golden_html_embeds_synthetic_model(self):
        output = (ROOT / "evals" / "weeklyviz-golden.html").read_text(encoding="utf-8")
        embedded = output.split('id="report-model">', 1)[1].split("</script>", 1)[0]
        model = json.loads(embedded)
        self.assertIs(model["metadata"].get("synthetic"), True)
        self.assertEqual("weeklyviz-synthetic-demo", model["metadata"]["report_id"])

    def test_invalid_donut_is_rejected(self):
        model = weeklyviz.read_json(ROOT / "evals" / "fixtures" / "report-model.json")
        model["charts"][1]["labels"] = ["A"]
        model["charts"][1]["series"][0]["values"] = [100]
        errors, _warnings = weeklyviz.validate_model(model)
        self.assertTrue(any("2-6 categories" in error for error in errors))

    def test_invalid_presentation_is_rejected(self):
        model = weeklyviz.read_json(ROOT / "evals" / "fixtures" / "report-model.json")
        model["presentation"]["density"] = "ultra-dense"
        errors, _warnings = weeklyviz.validate_model(model)
        self.assertTrue(any("presentation.density" in error for error in errors))

    def test_render_all_templates(self):
        model = weeklyviz.read_json(ROOT / "evals" / "fixtures" / "report-model.json")
        css = (ROOT / "assets" / "runtime" / "report.css").read_text(encoding="utf-8")
        runtime = (ROOT / "assets" / "runtime" / "report.js").read_text(encoding="utf-8")
        echarts = (ROOT / "assets" / "vendor" / "echarts.min.js").read_text(encoding="utf-8")
        for template_id, parent_style in (("cangshan", "executive"), ("qianzi", "editorial"), ("songye", "product-operations")):
            with self.subTest(template=template_id):
                template = weeklyviz.read_json(ROOT / "assets" / "templates" / f"{template_id}.json")
                model["template"] = template_id
                output = weeklyviz.render_html(model, template, css, runtime, echarts)
                self.assertIn("<!doctype html>", output)
                self.assertIn(f'data-template="{parent_style}"', output)
                self.assertIn(f'data-template-id="{template_id}"', output)
                self.assertIn('id="report-model"', output)
                self.assertIn("data-export-buffer", output)
                self.assertIn('class="report-index"', output)
                self.assertIn('data-action="toggle-sources"', output)
                self.assertIn('data-action="print"', output)
                self.assertIn('data-density="compact"', output)
                self.assertIn('class="source-marker"', output)
                self.assertIn('class="work-next"', output)
                self.assertIn('contenteditable="false"', output)
                self.assertNotIn('src="http', output)
                embedded = output.split('id="report-model">', 1)[1].split("</script>", 1)[0]
                self.assertEqual(template_id, json.loads(embedded)["template"])

    def test_invalid_layout_is_rejected(self):
        model = weeklyviz.read_json(ROOT / "evals" / "fixtures" / "report-model.json")
        model["presentation"]["layout"] = "invalid-layout"
        errors, _warnings = weeklyviz.validate_model(model)
        self.assertTrue(any("presentation.layout" in error for error in errors))

    def test_invalid_layout_order_is_rejected(self):
        model = weeklyviz.read_json(ROOT / "evals" / "fixtures" / "report-model.json")
        model["presentation"]["layout_order"] = "not-an-array"
        errors, _warnings = weeklyviz.validate_model(model)
        self.assertTrue(any("presentation.layout_order" in error for error in errors))

    def test_render_table_and_kanban_section_layouts(self):
        model = weeklyviz.read_json(ROOT / "evals" / "fixtures" / "report-model.json")
        model["sections"][0]["layout"] = "table"
        css = (ROOT / "assets" / "runtime" / "report.css").read_text(encoding="utf-8")
        runtime = (ROOT / "assets" / "runtime" / "report.js").read_text(encoding="utf-8")
        echarts = (ROOT / "assets" / "vendor" / "echarts.min.js").read_text(encoding="utf-8")
        template = weeklyviz.read_json(ROOT / "assets" / "templates" / "qianzi.json")
        output = weeklyviz.render_html(model, template, css, runtime, echarts)
        self.assertIn("work-table-wrap", output)

        model["sections"][0]["layout"] = "kanban"
        output = weeklyviz.render_html(model, template, css, runtime, echarts)
        self.assertIn("work-kanban-board", output)

    def test_operating_review_and_scopes(self):
        # 1. Test lag warnings
        model = {
            "metadata": {
                "report_id": "test-report",
                "title": "Test Report",
                "period": {"label": "2026.06.01 - 06.07", "start": "2026-06-01", "end": "2026-06-07"}
            },
            "template": "qianzi",
            "summary": {
                "headline": "Test Headline",
                "body": "Test Body"
            },
            "sources": [
                {
                    "id": "src-1",
                    "label": "Source 1",
                    "type": "xlsx-sheet",
                    "location": "sheet1.xlsx",
                    "wiki_token": "highly_sensitive_secret_token_123"
                }
            ],
            "metrics": [
                {
                    "id": "dau",
                    "name": "小红书DAU",
                    "value": 15,
                    "unit": "integer",
                    "scope": ["小红书"],
                    "time_grain": "week",
                    "aggregation": "none",
                    "source_refs": ["src-1"],
                    "target": {
                        "value": 100,
                        "period": "2026-Q2"
                    }
                }
            ],
            "okrs": [
                {
                    "id": "o1",
                    "type": "objective",
                    "label": "Test Obj",
                    "health": "正常",
                    "current": 10,
                    "target": 100,
                    "due": "2026-Q2",
                    "source_refs": ["src-1"],
                    "owner": "孙浩宸"
                },
                {
                    "id": "r1",
                    "type": "requirement",
                    "label": "Test Req",
                    "health": "正常",
                    "source_refs": ["src-1"],
                    "owner": "孙浩宸"
                }
            ]
        }
        errors, warnings = weeklyviz.validate_model(model)
        self.assertEqual([], errors)
        # Lag warnings should fire because Q2 is 90%+ elapsed in June and current progress is only 10%-15%
        self.assertTrue(any("lagging" in w for w in warnings))

        # 2. Test sanitization
        # Internal scope
        int_model = weeklyviz.sanitize_model_for_scope(model, "internal")
        self.assertNotIn("wiki_token", int_model["sources"][0]) # Token should be scrubbed unconditionally
        self.assertEqual("孙浩宸", int_model["okrs"][0]["owner"])

        # Leadership scope
        lead_model = weeklyviz.sanitize_model_for_scope(model, "leadership")
        self.assertEqual("孙*", lead_model["okrs"][0]["owner"]) # Name masked
        # Requirement okr items should be stripped in leadership scope
        self.assertFalse(any(o["type"] == "requirement" for o in lead_model["okrs"]))

        # External scope
        ext_model = weeklyviz.sanitize_model_for_scope(model, "external")
        self.assertEqual("孙*", ext_model["okrs"][0]["owner"]) # Name masked
        self.assertFalse(any(o["type"] == "requirement" for o in ext_model["okrs"])) # Requirement items stripped
        # Sensitive metrics should be masked
        self.assertEqual("已脱敏", ext_model["metrics"][0]["value"])
        # Source details should be stripped
        self.assertEqual({}, ext_model["sources"][0]["data"])


if __name__ == "__main__":
    unittest.main()
