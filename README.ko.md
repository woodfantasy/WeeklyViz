[中文](README.zh-CN.md) | [English](README.md) | [日本語](README.ja.md) | 한국어 | [Español](README.es.md) | [Português](README.pt.md) | [Français](README.fr.md)

<p align="center">
  <img src="assets/logo.svg" width="128" height="128" alt="WeeklyViz Logo">
</p>

<h1 align="center">WeeklyViz</h1>

<p align="center">
  <strong>프로페셔널 오프라인 HTML 주간 보고서 생성기 및 에이전트 스킬</strong>
</p>

<p align="center">
  <a href=""><img src="https://img.shields.io/badge/version-0.1.1-blue.svg" alt="Version"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
  <a href=""><img src="https://img.shields.io/badge/platform-Codex_/_Claude_Code-purple.svg" alt="Platform"></a>
</p>

<p align="center">
  원시 업데이트 데이터, 스프레드시트, 문서를 <strong>프로페셔널하고 반응형이며, 편집 가능하고 소스 추적이 가능한 오프라인 HTML 주간 보고서</strong>로 AI 에이전트가 자동 변환합니다.
</p>

[Agent Skills](https://agentskills.io) 사양에 따라 구축된 Claude 스킬 및 단독 실행 도구입니다. AI 에이전트(Claude Code, Cursor, Codex 등)와 원활하게 연동되도록 설계되었습니다. Python 스크립트를 직접 실행하거나 코딩할 필요 없이 스킬을 설치하기만 하면 AI 에이전트가 모든 작업을 자동으로 처리합니다.

---

## 🖼️ 결과물 예시

<p align="center">
  <a href="assets/red-shiji-weekly-report.jpg">
    <img src="assets/red-shiji-weekly-report.jpg" width="860" alt="WeeklyViz 에디토리얼 주간 보고서 결과물 예시">
  </a>
</p>

<p align="center"><sub>경영진 요약, KPI 카드, 목표 진행률, 데이터 시각화, 프로젝트 업데이트, 리스크 및 다음 작업을 한 페이지에 구성한 WeeklyViz 결과물입니다. 이미지를 클릭하면 원본 해상도로 볼 수 있습니다.</sub></p>

---

## ✨ 주요 기능

| 기능 | 설명 |
|------|------|
| 📊 **다중 소스 추출** | `.xlsx`, `.csv`, `.docx`, `.md`, 및 `.txt` 파일을 자동으로 분석하여 핵심 지표와 작업 진행 상황을 추출합니다. |
| 🎨 **독창적인 디자인 시스템** | 세 가지 테마(`Executive`, `Editorial`, `Product Operations`)를 내장하고 있으며, 오프라인(네트워크 무관)으로 작동합니다. |
| 🔗 **소스 추적성** | 고유한 해시 ID를 사용해 모든 KPI와 목록 항목을 원본 파일 이름 및 줄 위치에 자동으로 매핑하여 데이터 신뢰성을 보장합니다. |
| ✏️ **대화형 인라인 편집** | 출력된 HTML 보고서는 인라인 편집을 지원합니다. 텍스트와 숫자를 바로 수정하고, 테마 색상을 변경하여 PDF/인쇄로 출력할 수 있습니다. |
| 📈 **ECharts 내장** | 로컬 ECharts 런타임(`echarts.min.js`)을 탑재해 꺾은선, 막대, 도넛 차트 등을 오프라인 환경에서 렌더링합니다. |

---

## 🚀 사용 방법 (매우 간단함)

### 1. 스킬 설치
에이전트의 스킬 폴더에 WeeklyViz를 추가합니다:

*   **Claude Code**: 프로젝트 루트의 `.claude/skills/weeklyviz` 디렉토리에 이 저장소를 복제합니다.
*   **Cursor**: 프로젝트 루트의 `.cursor/skills/weeklyviz` 디렉토리에 이 저장소를 복제합니다.
*   **기타 에이전트**: 에이전트의 사용자 정의 지침 파일 경로에 이 저장소를 배치합니다.

### 2. 에이전트에게 요청하세요!
Python 명령을 실행하거나 설정 파일을 직접 작성할 필요가 **없습니다**. 원시 파일(스프레드시트, 메모, 텍스트 복사본 등)을 에이전트에게 전달하고 다음과 같이 요청하세요:

> *"WeeklyViz를 사용해서 내 메모로 주간 보고서를 만들어줘."*

에이전트가 자동으로 파일을 읽고 지표를 추출 및 검증하여 정교한 오프라인 HTML 보고서(`weekly-report.html`)를 한 번에 생성해 드립니다.

---

## 🛠️ 개발자용 (선택 사항)

명령줄에서 WeeklyViz를 수동으로 실행하려는 경우:

```bash
# 소스 번들에 원시 데이터 추출
python3 scripts/weeklyviz.py extract --input notes.md data.xlsx --output source-bundle.json

# 보고서 모델 스키마 검증
python3 scripts/weeklyviz.py validate --report report-model.json

# 단일 파일 오프라인 HTML로 컴파일
python3 scripts/weeklyviz.py render --report report-model.json --output weekly-report.html
```

---

## 📋 버전 정보

*   **v0.1.1** (2026-06-09)
    - 표준 에이전트 로드 및 설치를 위해 디렉터리 계층 구조를 루트 폴더로 평탄화.
    - `Editorial` 템플릿에 도트 배경, macOS 창 표시 장식, 하드 그림자 카드, 도트라인 리스트, 양측 사이드바 장식을 추가하는 프리미엄 업그레이드 단행.
    - 보안 강화를 위해 민감한 내부 데이터를 Git 추적에서 제외하도록 .gitignore 구성 및 안전 정책 수립.
*   **v0.1.0** (2026-06-09)
    - 최초 버전 배포.
```

