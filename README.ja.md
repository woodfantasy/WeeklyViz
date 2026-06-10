[中文](README.zh-CN.md) | [English](README.md) | 日本語 | [한국어](README.ko.md) | [Español](README.es.md) | [Português](README.pt.md) | [Français](README.fr.md)

<p align="center">
  <img src="assets/logo.svg" width="128" height="128" alt="WeeklyViz Logo">
</p>

<h1 align="center">WeeklyViz</h1>

<p align="center">
  <strong>プロフェッショナルオフラインHTML週報ジェネレーター＆エージェントスキル</strong>
</p>

<p align="center">
  <a href=""><img src="https://img.shields.io/badge/version-0.1.1-blue.svg" alt="Version"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
  <a href=""><img src="https://img.shields.io/badge/platform-Codex_/_Claude_Code-purple.svg" alt="Platform"></a>
</p>

<p align="center">
  生の更新データ、スプレッドシート、ドキュメントを、<strong>プロフェッショナルでレスポンシブ、編集可能、ソース追跡可能なオフラインHTML週報</strong>にワンショットで変換します。
</p>

[Agent Skills](https://agentskills.io) 仕様に基づいて構築された Claude Skill およびスタンドアロンツールです。構造化されたデータ抽出と社論レベルのデザインシステムを組み合わせて、作業文、KPI、およびチャートを洗練された週報ブリーフィングに変換します。開発者、製品マネージャー、および運用チームが、乱雑なコピー＆ペースト週報をなくし、視覚的なレポートを作成するのを支援するように設計されています。

---

## 🖼️ 出力例

<p align="center">
  <a href="assets/red-shiji-weekly-report.jpg">
    <img src="assets/red-shiji-weekly-report.jpg" width="860" alt="WeeklyVizのエディトリアル週報の出力例">
  </a>
</p>

<p align="center"><sub>エグゼクティブサマリー、KPIカード、目標進捗、データ可視化、プロジェクト更新、リスク、次のアクションをまとめたWeeklyVizの出力例です。画像をクリックすると元の解像度で表示できます。</sub></p>

---

## ✨ 主な機能

| 機能 | 説明 |
|------|------|
| 📊 **マルチソース抽出** | `.xlsx`、`.csv`、`.docx`、`.md`、`.markdown`、および `.txt` ファイルを自動的に解析し、指標、テーブル、散文、および進捗リストを抽出します。 |
| 🛡️ **厳格なスキーマ検証** | データ型、時系列ルール、割合、およびステータスラベルを検証する強力な JSON スキーマ (`report.schema.json`) を強制します。 |
| 🎨 **高品質デザインシステム** | 3つのビルトイン高品質テーマ（`Executive`、`Editorial`、`Product Operations`）と、レスポンシブなレイアウトを提供します（ネットワーク接続不要）。 |
| 🔗 **ソース追跡可能性** | 安定したハッシュ ID を使用して、すべての KPI、進捗バー、グラフ、およびリスト項目を元のファイルと行に自動的にリンクします。 |
| ✏️ **インタラクティブ編集** | レンダリングされた HTML は完全にインタラクティブです。テキストや数値をインライン編集し、テーマ色を調整し、Print/PDF 用に書き出せます。 |
| 📈 **Apache ECharts 統合** | ローカルの ECharts ランタイム (`echarts.min.js`) を同梱し、オフラインで折れ線、棒、ドーナツ、漏斗、ヒートマップ、滝グラフを描画します。 |
| 🔍 **体系的な QA チェック** | HTML の構造とアクセシビリティを検証するスクリプト (`validate_html.mjs`) を含み、キーボード操作やオフラインの信頼性を検査します。 |

---

## 🚀 クイックスタート

### 1. スキルのインストール

<details>
<summary><b>Claude Code</b></summary>

プロジェクトルートの `.claude/skills/` 以下に `weeklyviz/` フォルダを配置します：

```bash
git clone https://github.com/woodfantasy/WeeklyViz.git .claude/skills/weeklyviz
```
</details>

<details>
<summary><b>Cursor</b></summary>

プロジェクトルートの `.cursor/skills/` 以下に `weeklyviz/` フォルダを配置します：

```bash
git clone https://github.com/woodfantasy/WeeklyViz.git .cursor/skills/weeklyviz
```
</details>

### 2. 基本ワークフロー

#### ステップ 1: データの抽出
```bash
python3 scripts/weeklyviz.py extract \
  --input path/to/metrics.xlsx path/to/updates.md \
  --output source-bundle.json
```

#### ステップ 2: 報告モデルの作成
[report.schema.json](references/report.schema.json) に従って `report-model.json` を構築します。

#### ステップ 3: 検証とHTMLレンダリング
```bash
# スキーマと図表ルールの検証
python3 scripts/weeklyviz.py validate --report report-model.json

# HTMLレンダリング
python3 scripts/weeklyviz.py render --report report-model.json --output weekly-report.html

# アクセシビリティ検証
node scripts/validate_html.mjs weekly-report.html
```

---

## 📋 リリースバージョン

*   **v0.1.1** (2026-06-09)
    - エージェントの標準的な読み込みとインストールのために、ディレクトリ階層をルートフォルダにフラット化。
    - `Editorial` テンプレートのプレミアムアップグレード（ドット背景、macOSスタイルのウィンドウバー、ハードシャドウ、ドット付き指標リスト、ダブルサイドバー装飾の追加）。
    - 公開リポジトリへのコミットを防ぐため、内部機密データ（Shiji週報など）を Git 追跡から完全に除外する安全ポリシーの策定。
*   **v0.1.0** (2026-06-09)
    - 初回リリース。
    - CSV, XLSX, DOCX, MD, プレーンテキスト抽出器。
    - JSON Schema 検証および ECharts 規約バリデーター。
    - オンプレミス/オフライン対応のインタラクティブ HTML 出力。
