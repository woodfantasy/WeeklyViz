import argparse
import json
import subprocess
from pathlib import Path
from copy import deepcopy
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]

parser = argparse.ArgumentParser(description="Render a collision-free gallery for every WeeklyViz theme.")
parser.add_argument(
    "--report",
    default=str(ROOT / "evals" / "fixtures" / "red-shiji-report-model.json"),
    help="Base report model used for every theme.",
)
parser.add_argument(
    "--output-dir",
    default=str(ROOT),
    help="Directory for generated models and reports.",
)
parser.add_argument(
    "--stamp",
    default=datetime.now().strftime("%m%d"),
    help="Filename stamp, for example 0611.",
)
args = parser.parse_args()

model_path = Path(args.report).resolve()
output_dir = Path(args.output_dir).resolve()
output_dir.mkdir(parents=True, exist_ok=True)

with open(model_path, "r", encoding="utf-8") as f:
    base_model = json.load(f)

def get_template_theme(template_id):
    p = ROOT / "assets" / "templates" / f"{template_id}.json"
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["theme"]

# Define mapping for all 14 templates with appropriate layouts and themes
variants = {
    "canghai": {
        "presentation": {
            "density": "compact",
            "layout": "operating-review",
            "layout_order": ["summary", "metrics", "charts", "okrs", "sections", "risks", "next_actions"],
            "section_layout": "cards",
            "source_display": "summary",
            "show_toc": True
        }
    },
    "cangshan": {
        "presentation": {
            "density": "compact",
            "layout": "dashboard",
            "layout_order": ["summary", "kpis", "charts", "okrs", "sections", "risks", "next_actions"],
            "section_layout": "cards",
            "source_display": "summary",
            "show_toc": True
        }
    },
    "dailan": {
        "presentation": {
            "density": "compact",
            "layout": "dashboard",
            "layout_order": ["summary", "kpis", "charts", "okrs", "sections", "risks", "next_actions"],
            "section_layout": "list",
            "source_display": "summary",
            "show_toc": True
        }
    },
    "hupo": {
        "presentation": {
            "density": "balanced",
            "layout": "newsletter",
            "layout_order": ["summary", "kpis", "charts", "okrs", "sections", "risks", "next_actions"],
            "section_layout": "list",
            "source_display": "summary",
            "show_toc": True
        }
    },
    "luoli": {
        "presentation": {
            "density": "compact",
            "layout": "dashboard",
            "layout_order": ["summary", "kpis", "charts", "okrs", "sections", "risks", "next_actions"],
            "section_layout": "cards",
            "source_display": "summary",
            "show_toc": True
        }
    },
    "moyi": {
        "presentation": {
            "density": "balanced",
            "layout": "newsletter",
            "layout_order": ["summary", "kpis", "charts", "okrs", "sections", "risks", "next_actions"],
            "section_layout": "list",
            "source_display": "summary",
            "show_toc": True
        }
    },
    "mushanzi": {
        "presentation": {
            "density": "balanced",
            "layout": "operating-review",
            "layout_order": ["summary", "metrics", "charts", "okrs", "sections", "risks", "next_actions"],
            "section_layout": "cards",
            "source_display": "summary",
            "show_toc": True
        }
    },
    "qianzi": {
        "presentation": {
            "density": "balanced",
            "layout": "newsletter",
            "layout_order": ["summary", "kpis", "charts", "okrs", "sections", "risks", "next_actions"],
            "section_layout": "cards",
            "source_display": "summary",
            "show_toc": True
        }
    },
    "qiuli": {
        "presentation": {
            "density": "balanced",
            "layout": "newsletter",
            "layout_order": ["summary", "kpis", "charts", "okrs", "sections", "risks", "next_actions"],
            "section_layout": "list",
            "source_display": "summary",
            "show_toc": True
        }
    },
    "songye": {
        "presentation": {
            "density": "compact",
            "layout": "kanban",
            "layout_order": ["summary", "kpis", "charts", "okrs", "sections", "risks", "next_actions"],
            "section_layout": "kanban",
            "source_display": "summary",
            "show_toc": True
        }
    },
    "wanying": {
        "presentation": {
            "density": "compact",
            "layout": "operating-review",
            "layout_order": ["summary", "metrics", "charts", "okrs", "sections", "risks", "next_actions"],
            "section_layout": "list",
            "source_display": "summary",
            "show_toc": True
        }
    },
    "yanzhi": {
        "presentation": {
            "density": "compact",
            "layout": "dashboard",
            "layout_order": ["summary", "kpis", "charts", "okrs", "sections", "risks", "next_actions"],
            "section_layout": "table",
            "source_display": "summary",
            "show_toc": True
        }
    },
    "yuanshan": {
        "presentation": {
            "density": "compact",
            "layout": "kanban",
            "layout_order": ["summary", "kpis", "charts", "okrs", "sections", "risks", "next_actions"],
            "section_layout": "kanban",
            "source_display": "summary",
            "show_toc": True
        }
    },
    "zhuqing": {
        "presentation": {
            "density": "compact",
            "layout": "kanban",
            "layout_order": ["summary", "kpis", "charts", "okrs", "sections", "risks", "next_actions"],
            "section_layout": "kanban",
            "source_display": "summary",
            "show_toc": True
        }
    }
}

for name, config in variants.items():
    model = deepcopy(base_model)
    model["presentation"] = config["presentation"]
    detail_first = config["presentation"]["layout"] == "operating-review"
    model["presentation"]["layout_order"] = [
        "summary",
        "kpis",
        "metrics" if detail_first else "progress",
        "progress" if detail_first else "metrics",
        "charts",
        "okrs",
        *(["requirements"] if detail_first else []),
        "sections",
        "risks",
        "next_actions",
    ]
    if not detail_first and model.get("kpis"):
        model["presentation"]["layout_order"].remove("metrics")
    model["template"] = name
    model["theme"] = get_template_theme(name)
    
    # Adjust section layout to match the presentation section_layout
    for section in model.get("sections", []):
        section["layout"] = config["presentation"]["section_layout"]
        
    layout_name = config["presentation"]["layout"]
    section_name = config["presentation"]["section_layout"]
    
    project = model_path.name.replace("-report-model.json", "")
    model_out = output_dir / f"{project}-{layout_name}-{args.stamp}-model.json"
    html_out = output_dir / f"{project}-{layout_name}-{args.stamp}-report.html"
    
    with open(model_out, "w", encoding="utf-8") as f:
        json.dump(model, f, ensure_ascii=False, indent=2)
        
    print(f"Rendering {name} variant (layout: {layout_name}, section: {section_name})...")
    result = subprocess.run([
        "python3", "scripts/weeklyviz.py", "render",
        "--report", str(model_out),
        "--output", str(html_out)
    ], cwd=ROOT, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error rendering {name}:")
        print(result.stderr)
        continue
        
    print(f"Rendered {html_out.name} successfully.")
    
    # Validate HTML
    val_result = subprocess.run([
        "node", "scripts/validate_html.mjs", str(html_out)
    ], cwd=ROOT, capture_output=True, text=True)
    
    if val_result.returncode != 0:
        print(f"Validation FAILED for {name}:")
        print(val_result.stderr)
        print(val_result.stdout)
    else:
        print(f"Validation PASSED for {name}")

print("Done rendering all 14 variants!")
