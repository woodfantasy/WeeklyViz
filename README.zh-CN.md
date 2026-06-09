[English](README.md) | 中文 | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md) | [Português](README.pt.md) | [Français](README.fr.md)

<p align="center">
  <img src="weeklyviz/assets/logo.svg" width="128" height="128" alt="WeeklyViz Logo">
</p>

<h1 align="center">WeeklyViz</h1>

<p align="center">
  <strong>专业离线 HTML 工作周报生成器 & Agent 技能</strong>
</p>

<p align="center">
  <a href=""><img src="https://img.shields.io/badge/version-0.1-blue.svg" alt="版本"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="协议"></a>
  <a href=""><img src="https://img.shields.io/badge/platform-Codex_/_Claude_Code-purple.svg" alt="平台"></a>
</p>

<p align="center">
  一键将原始工作记录、电子表格及文档，转化为<strong>专业、自适应、可编辑、可追溯的离线 HTML 周报</strong>。
</p>

一个基于 [Agent Skills](https://agentskills.io) 规范构建的 Claude Skill 与独立命令行工具。它将结构化数据提取与杂志级设计系统深度融合，把零散的工作更新、KPI 键值和图表编排为管理层精装简报。旨在帮助开发者、产品经理和运营团队消灭“混乱复制粘贴”的周报模式，交付极具视觉表现力和说服力的工作汇报。

---

## ✨ 核心能力

| 能力 | 描述 |
|------|------|
| 📊 **多源数据提取** | 自动解析并提取 `.xlsx`, `.csv`, `.docx`, `.md`, `.markdown` 和 `.txt` 文件中的原始指标、表格、段落文字和进展列表。 |
| 🛡️ **严格 Schema 校验** | 引入强类型的 JSON Schema (`report.schema.json`)，在渲染前强制校验数据类型、时序合理性、部分与整体比例关系以及状态标签等约束。 |
| 🎨 **社论级设计系统** | 内置三款高审美主题（`Executive` 经营看板, `Editorial` 社论字体, `Product Operations` 研发网格），响应式布局，零外部网络请求（纯离线可用）。 |
| 🔗 **数据源可追溯性** | 自动将每个 KPI、进度条、图表和列表项映射到源文件名称与行数，通过稳定的 Hash ID 实现对每一条业务数据的穿透式追溯。 |
| ✏️ **交互式行内编辑** | 渲染的 HTML 报告完全可交互：支持文本和数字行内编辑、直接修改图表数据集、微调主题色，并支持单文件数据重载和一键 Print/PDF 导出。 |
| 📈 **Apache ECharts 本地渲染** | 内置本地 ECharts 运行时（`echarts.min.js`），支持折线图、面积图、柱状图、漏斗图、热力图、瀑布图和饼图的纯离线绘制。 |
| 🔍 **自动化 QA 质量检查** | 搭载无头 HTML 结构与无障碍校验脚本（`validate_html.mjs`），强制检测键盘焦点、语义化 HTML5 标记以及离线加载健全性。 |

---

## 🚀 快速开始

### 1. 安装 Skill

<details>
<summary><b>Claude Code</b></summary>

将项目中的 `weeklyviz/` 文件夹放入你项目根目录的 `.claude/skills/` 路径下：

```bash
# 克隆到项目的 Skill 目录中
git clone https://github.com/woodfantasy/WeeklyViz.git .claude/skills/weeklyviz
```

Claude Code 将自动检测并加载该 Skill。
</details>

<details>
<summary><b>Cursor</b></summary>

将 `weeklyviz/` 文件夹放入你项目根目录的 `.cursor/skills/` 下：

```bash
git clone https://github.com/woodfantasy/WeeklyViz.git .cursor/skills/weeklyviz
```

Cursor Agent 模式将自动读取 `SKILL.md` 里的核心指令。
</details>

<details>
<summary><b>Codex / OpenClaw</b></summary>

针对 Codex，将文件夹放入 Agent 指令目录：
```bash
git clone https://github.com/woodfantasy/WeeklyViz.git agents/skills/weeklyviz
```

针对 OpenClaw，直接向 Agent 发送技能地址进行学习：
```
请学习这个技能：https://github.com/woodfantasy/WeeklyViz
```
</details>

### 2. 基础开发流

#### 第一步：提取源数据
将你本周的所有电子表格、Markdown 更新或者备忘录汇总到一个文件夹中，运行提取命令：

```bash
python3 weeklyviz/scripts/weeklyviz.py extract \
  --input path/to/metrics.xlsx path/to/updates.md \
  --output source-bundle.json
```
这将解析文件并将它们映射到 `source-bundle.json` 中唯一的源 Hash ID。

#### 第二步：编写报告模型
编写排版规划，参照 [report.schema.json](weeklyviz/references/report.schema.json) 构建 `report-model.json`。每个核心 KPI、进度条和图表都必须带上 `source_refs` 指向 `source-bundle.json` 中的数据源。

#### 第三步：校验并渲染 HTML
校验报告数据模型并编译最终的离线 HTML 报告：

```bash
# 校验数据模型是否符合结构规范与限制
python3 weeklyviz/scripts/weeklyviz.py validate --report report-model.json

# 渲染 HTML 报告
python3 weeklyviz/scripts/weeklyviz.py render --report report-model.json --output weekly-report.html

# 校验生成的 HTML 报告的无障碍与结构合规性
node weeklyviz/scripts/validate_html.mjs weekly-report.html
```

---

## 📁 项目结构

```
WeeklyViz/
├── README.md                      # 英文文档
├── README.zh-CN.md                # 中文文档
├── .gitignore                     # Git 忽略文件
└── weeklyviz/                     # Skill 包核心目录
    ├── SKILL.md                   # 核心技能指令 (Skill 大脑)
    ├── agents/
    │   └── openai.yaml            # OpenAI 自定义 Agent 配置文件
    ├── scripts/
    │   ├── weeklyviz.py           # 核心 CLI (提取, 校验, 渲染)
    │   └── validate_html.mjs      # HTML 结构与 A11y 校验器
    ├── references/
    │   ├── report.schema.json     # 报告数据模型的 JSON Schema
    │   ├── chart-selection.md     # 图表选型与规约指南
    │   ├── design-system.md       # 设计系统 Token 与布局规范
    │   ├── visual-composition.md  # 视觉密度与节奏排版指南
    │   └── qa-checklist.md        # 质量控制检查清单
    ├── assets/
    │   ├── logo.svg               # 矢量品牌 Logo
    │   ├── runtime/
    │   │   ├── report.css         # 报告样式表
    │   │   └── report.js          # 行内编辑器交互脚本
    │   ├── templates/
    │   │   ├── executive.json     # 经营看板模板
    │   │   ├── editorial.json     # 社论风大字报模板
    │   │   └── product-operations.json # 研发网格明细模板
    │   └── vendor/
    │       └── echarts.min.js     # Apache ECharts 运行时 (锁定 v5)
    ├── tests/
    │   └── test_weeklyviz.py      # Python 单元测试集
    └── evals/
        ├── evals.json             # 评测元数据
        ├── README.md              # 评测数据方针
        ├── fixtures/
        │   └── report-model.json  # 虚构报告测试数据
        └── weeklyviz-golden.html  # 编译的合成 Golden HTML
```

---

## 🔬 命令参考与独立开发工具

通过命令行工具 `weeklyviz.py` 管理本地开发工作流：

```bash
# 查看所有可用命令和帮助
python3 weeklyviz/scripts/weeklyviz.py --help
```

### 数据提取 (`extract`)
- 提取 `.txt` 文件中的段落、`.md` 文件中的标题和段落分区、`.csv` 和 `.docx` 中的表格、以及 `.xlsx` 中的工作表和计算公式。
- 自动生成 `generated_at`（提取时间）、`sources` 数组以及针对不支持格式（如旧版 `.xls`、PDF 或 演示文稿 `.ppt`）的警告。

### 校验数据模型 (`validate`)
- 检查 `metadata` 中是否包含 `report_id`, `title` 和 `period`。
- 校验图表硬性规约约束：
  - 折线图/面积图必须提供至少 4 个时间维度的类别。
  - 饼图/环形图类别需在 2-6 个之间，仅支持单系列，且数值不得为负。
  - 漏斗图必须按业务转化环节保持递进顺序。
- 强制校验每一个汇报数值都必须声明合法的数据源 ID 引用。

### 编译渲染 (`render`)
- 将主题 Tokens、交互式编辑器 JS、样式 CSS、ECharts 库与 JSON 模型数据融为一体，输出单个自适应的 HTML 文件。
- 生成的 HTML 无任何外部网络依赖，支持断网环境及本地完美展现。

---

## 🏗️ 设计系统与主题

WeeklyViz 提供三款面向不同汇报对象的精美版式（详情见 [design-system.md](weeklyviz/references/design-system.md)）：

*   **Executive (`executive.json`)**: 深邃暗色主标题与灰白背景，字号小，适合汇报给管理层的高密度信息看板。
*   **Editorial (`editorial.json`)**: 宽大舒服的排版比例与香草/薰衣草淡紫色系，突出叙事和宏观故事性。
*   **Product Operations (`product-operations.json`)**: 高亮的状态边框、醒目的进度条和分栏卡片布局，契合研发和复杂业务线的运营跟进。

你可以在全局或单独小节级别动态调整：
- `density` (视觉密度): `compact` (紧凑), `balanced` (平衡) 或 `spacious` (宽松)。
- `section_layout` (排版结构): `cards` (卡片), `grid` (网格) 或 `list` (列表)。
- `source_display` (溯源面板): `summary` (精简) 或 `expanded` (展开)。

---

## 📋 发布版本

*   **v0.1.0** (2026-06-09)
    - 初始版本发布。
    - 实现对 CSV, XLSX, DOCX, MD, Plain Text 的完整多源数据提取器。
    - 提供 JSON Schema 与图表科学规约校验器。
    - 支持将模型单文件编译为离线自适应 HTML 周报（集成本地 ECharts）。
    - 预设 Executive, Editorial 和 Product Operations 三大主题模版。
    - 配套独立的 HTML 无障碍与结构规范核验脚本。
