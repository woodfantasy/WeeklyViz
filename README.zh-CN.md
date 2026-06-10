中文 | [English](README.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md) | [Português](README.pt.md) | [Français](README.fr.md)

<p align="center">
  <img src="assets/logo.svg" width="128" height="128" alt="WeeklyViz Logo">
</p>

<h1 align="center">WeeklyViz</h1>

<p align="center">
  <strong>专业离线 HTML 工作周报生成器 & Agent 技能</strong>
</p>

<p align="center">
  <a href=""><img src="https://img.shields.io/badge/version-0.1.1-blue.svg" alt="版本"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="协议"></a>
  <a href=""><img src="https://img.shields.io/badge/platform-Codex_/_Claude_Code-purple.svg" alt="平台"></a>
</p>

<p align="center">
  一键将原始工作记录、电子表格及文档，转化为<strong>专业、自适应、可编辑、可追溯的离线 HTML 周报</strong> —— 由您的 AI 智能体自动完成。
</p>

一个基于 [Agent Skills](https://agentskills.io) 规范构建的 Claude Skill 与独立命令行工具。专为与 AI 智能体（如 Claude Code, Cursor, Codex）配合而设计。您无需自己运行 Python 脚本或编写代码，只需安装本技能，即可让 AI 智能体完成所有繁琐的操作。

---

## 🖼️ 产出示例

<p align="center">
  <a href="assets/red-shiji-weekly-report.jpg">
    <img src="assets/red-shiji-weekly-report.jpg" width="860" alt="WeeklyViz 社论风格周报产出示例">
  </a>
</p>

<p align="center"><sub>WeeklyViz 生成的完整社论风格周报，集中展示管理摘要、核心指标、目标进度、数据图表、项目进展、风险与下周行动。点击图片可查看原始分辨率。</sub></p>

---

## ✨ 核心能力

| 能力 | 描述 |
|------|------|
| 📊 **多源数据提取** | 自动解析并提取 `.xlsx`, `.csv`, `.docx`, `.md`, 和 `.txt` 文件中的指标数据和工作进展。 |
| 🎨 **社论级设计系统** | 内置三款高审美主题（`Executive` 经营看板, `Editorial` 社论字体, `Product Operations` 研发网格），零外部网络请求（纯离线可用）。 |
| 🔗 **数据源可追溯性** | 自动将每个 KPI、进度条、图表 and 列表项映射到源文件名称与行数，实现对数据的穿透式追溯。 |
| ✏️ **交互式行内编辑** | 最终 HTML 报告支持行内编辑文本和数字、直接修改图表、微调主题色，并支持 Print/PDF 导出。 |
| 📈 **ECharts 本地渲染** | 内置本地 ECharts 运行时（`echarts.min.js`），支持折线图、柱状图、饼图等在离线环境下的交互式绘制。 |

---

## 🚀 如何使用（极简体验）

### 1. 安装 Skill
将 WeeklyViz 添加到您的 AI 智能体技能文件夹中：

*   **Claude Code**：克隆本仓库到您项目根目录的 `.claude/skills/weeklyviz` 路径下。
*   **Cursor**：克隆本仓库到您项目根目录 of `.cursor/skills/weeklyviz` 路径下。
*   **其他智能体**：将仓库放置在智能体的自定义提示词/指令路径中。

### 2. 告诉你的 Agent 即可！
你 **不需要** 学习 Python 或是运行任何命令行命令。只需将你的原始文件（如 Excel 表格、Markdown 笔记、文字粘贴）提供给 AI 智能体，并对它说：

> *“使用 WeeklyViz 将我的工作记录生成一份周报。”*

智能体将自动读取您的文件、提取指标数据、执行 Schema 校验，并直接为您生成精美的单文件离线 HTML 周报（`weekly-report.html`）。

---

## 🛠️ 开发者进阶（可选）

如果您希望在命令行中手动运行 WeeklyViz：

```bash
# 提取源数据到 bundle 包
python3 scripts/weeklyviz.py extract --input notes.md data.xlsx --output source-bundle.json

# 校验报告数据模型
python3 scripts/weeklyviz.py validate --report report-model.json

# 编译为单文件离线 HTML
python3 scripts/weeklyviz.py render --report report-model.json --output weekly-report.html
```

---

## 📋 发布版本

*   **v0.1.1** (2026-06-09)
    - 扁平化目录结构至根目录，适配标准的 Agent 加载与安装规范。
    - 升级并重构 `Editorial` 模版为更高级的社论风格，加入 dots 背景、macOS 窗口栏装饰、硬投影卡片、点线指标列表与双侧边栏装饰。
    - 确立安全隔离策略，将包含用户真实业务数据的周报与数据文件彻底排除出 Git 追踪列表。
*   **v0.1.0** (2026-06-09)
    - 初始版本发布。
