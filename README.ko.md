[English](README.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md) | 한국어 | [Español](README.es.md) | [Português](README.pt.md) | [Français](README.fr.md)

<p align="center">
  <img src="weeklyviz/assets/logo.svg" width="128" height="128" alt="WeeklyViz Logo">
</p>

<h1 align="center">WeeklyViz</h1>

<p align="center">
  <strong>프로페셔널 오프라인 HTML 주간 보고서 생성기 및 에이전트 스킬</strong>
</p>

<p align="center">
  <a href=""><img src="https://img.shields.io/badge/version-0.1-blue.svg" alt="Version"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
  <a href=""><img src="https://img.shields.io/badge/platform-Codex_/_Claude_Code-purple.svg" alt="Platform"></a>
</p>

<p align="center">
  원시 업데이트 데이터, 스프레드시트, 문서를 <strong>프로페셔널하고 반응형이며, 편집 가능하고 소스 추적이 가능한 오프라인 HTML 주간 보고서</strong>로 변환합니다.
</p>

[Agent Skills](https://agentskills.io) 사양에 따라 구축된 Claude Skill 및 단독 실행 도구입니다. 구조화된 데이터 추출과 편집 수준의 디자인 시스템을 결합하여 업무 요약, 핵심 지표(KPI) 및 차트를 정교한 주간 요약 보고서로 생성합니다. 개발자, 제품 매니저, 운영 팀이 매주 수동으로 정리하는 번거로움을 덜고 시각적이고 직관적인 보고서를 작성할 수 있도록 설계되었습니다.

---

## ✨ 주요 기능

| 기능 | 설명 |
|------|------|
| 📊 **다중 소스 추출** | `.xlsx`, `.csv`, `.docx`, `.md`, `.markdown`, 및 `.txt` 파일을 자동으로 구문 분석하여 원시 지표, 표, 텍스트 및 업데이트 목록을 추출합니다. |
| 🛡️ **엄격한 스키마 검증** | 데이터 유형, 시계열 규칙, 비율 및 상태 레이블을 검증하는 강력한 JSON 스키마 (`report.schema.json`)를 강제 적용합니다. |
| 🎨 **社論급 디자인 시스템** | 세 가지 기본 테마(`Executive`, `Editorial`, `Product Operations`)와 반응형 레이아웃을 내장하고 있으며, 오프라인(네트워크 연결 불필요)으로 작동합니다. |
| 🔗 **소스 추적성** | 고유한 해시 ID를 사용하여 모든 KPI, 진행 바, 차트, 목록 항목을 원본 파일 이름 및 줄 위치에 자동으로 매핑합니다. |
| ✏️ **대화형 인라인 편집** | 렌더링된 HTML 보고서는 인라인 편집을 지원합니다. 텍스트와 숫자를 바로 수정하고, 테마 색상을 변경하며, Print/PDF로 내보낼 수 있습니다. |
| 📈 **Apache ECharts 내장** | 로컬 ECharts 런타임(`echarts.min.js`)을 사용하여 꺾은선, 막대, 도넛, 깔때기, 열지도(Heatmap) 및 폭포수 차트를 오프라인으로 렌더링합니다. |
| 🔍 **체계적인 QA 검증** | 웹 접근성 및 HTML 구조를 검증하는 스크립트(`validate_html.mjs`)를 통해 키보드 포커스 및 오프라인 신뢰성을 점검합니다. |

---

## 🚀 빠른 시작

### 1. 스킬 설치

<details>
<summary><b>Claude Code</b></summary>

프로젝트 루트의 `.claude/skills/` 디렉토리에 `weeklyviz/` 폴더를 복사합니다:

```bash
git clone https://github.com/woodfantasy/WeeklyViz.git .claude/skills/weeklyviz
```
</details>

<details>
<summary><b>Cursor</b></summary>

프로젝트 루트의 `.cursor/skills/` 디렉토리에 `weeklyviz/` 폴더를 복사합니다:

```bash
git clone https://github.com/woodfantasy/WeeklyViz.git .cursor/skills/weeklyviz
```
</details>

### 2. 기본 작업 흐름

#### 1단계: 데이터 추출
```bash
python3 weeklyviz/scripts/weeklyviz.py extract \
  --input path/to/metrics.xlsx path/to/updates.md \
  --output source-bundle.json
```

#### 2단계: 보고서 모델 작성
[report.schema.json](weeklyviz/references/report.schema.json)에 맞추어 `report-model.json` 데이터를 정의합니다.

#### 3단계: 검증 및 HTML 렌더링
```bash
# 스키마 및 차트 제약 검증
python3 weeklyviz/scripts/weeklyviz.py validate --report report-model.json

# HTML 렌더링
python3 weeklyviz/scripts/weeklyviz.py render --report report-model.json --output weekly-report.html

# 접근성 검증
node weeklyviz/scripts/validate_html.mjs weekly-report.html
```

---

## 📋 버전 정보

*   **v0.1.0** (2026-06-09)
    - 최초 버전 배포.
    - CSV, XLSX, DOCX, MD, Plain Text 지원 데이터 추출기.
    - JSON Schema 및 ECharts 하드 검증기 탑재.
    - 단일 파일 기반 오프라인 대화형 HTML 보고서 컴파일 지원.
