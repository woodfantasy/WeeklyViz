[[English](README.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md) | [Português](README.pt.md) | Français

<p align="center">
  <img src="assets/logo.svg" width="128" height="128" alt="WeeklyViz Logo">
</p>

<h1 align="center">WeeklyViz</h1>

<p align="center">
  <strong>Générateur de Rapports Hebdomadaires HTML Hors-ligne et Skill d'Agent Professionnel</strong>
</p>

<p align="center">
  <a href=""><img src="https://img.shields.io/badge/version-0.11-blue.svg" alt="Version"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
  <a href=""><img src="https://img.shields.io/badge/platform-Codex_/_Claude_Code-purple.svg" alt="Platform"></a>
</p>

<p align="center">
  Convertissez les mises à jour textuelles, feuilles de calcul et documents en <strong>rapports hebdomadaires HTML hors-ligne professionnels, adaptatifs, modifiables et traçables jusqu'à la source</strong>.
</p>

C'est une Claude Skill et un outil indépendant construit sous la spécification [Agent Skills](https://agentskills.io). Il associe l'extraction de données structurées avec un système de conception de niveau éditorial pour transformer les textes de travail, KPIs et graphiques en bulletins exécutifs raffinés. Conçu pour aider les développeurs, managers de produit et équipes opérationnelles à éliminer les copier-coller désordonnés et à livrer des rapports visuels de haute qualité.

---

## ✨ Fonctionnalités Clés

| Fonctionnalité | Description |
|----------------|-------------|
| 📊 **Extraction Multi-sources** | Analyse et extrait automatiquement les fichiers `.xlsx`, `.csv`, `.docx`, `.md`, `.markdown` et `.txt` pour en extraire les métriques, tableaux et textes. |
| 🛡️ **Validation Stricte** | Assure l'intégrité via un schéma JSON (`report.schema.json`) qui valide les types de données, chronologies, proportions et statuts avant génération. |
| 🎨 **Conception Éditoriale Adaptative** | Propose trois thèmes prédéfinis (`Executive`, `Editorial`, `Product Operations`) sans dépendances réseau externes (100% hors-ligne). |
| 🔗 **Traçabilité de la Source** | Lie automatiquement chaque KPI, barre de progression, graphique et élément à son fichier et ligne d'origine via des identifiants de hachage stables. |
| ✏️ **Édition Inline Interactive** | Le rapport HTML final permet de modifier les textes et les nombres en ligne, d'ajuster les couleurs de thème et d'exporter directement en PDF/impression. |
| 📈 **Apache ECharts Embarqué** | Utilise un moteur ECharts local (`echarts.min.js`) pour tracer des graphiques en lignes, barres, beignets, entonnoirs et cascades hors-ligne. |
| 🔍 **Contrôle Qualité** | Intègre un script de validation d'accessibilité et de structure HTML (`validate_html.mjs`) pour tester la navigation clavier et le chargement. |

---

## 🚀 Démarrage Rapide

### 1. Installer la Skill

<details>
<summary><b>Claude Code</b></summary>

Placez le dossier `weeklyviz/` dans `.claude/skills/` à la racine de votre projet :

```bash
git clone https://github.com/woodfantasy/WeeklyViz.git .claude/skills/weeklyviz
```
</details>

<details>
<summary><b>Cursor</b></summary>

Placez le dossier `weeklyviz/` dans `.cursor/skills/` à la racine de votre projet :

```bash
git clone https://github.com/woodfantasy/WeeklyViz.git .cursor/skills/weeklyviz
```
</details>

### 2. Flux de Travail

#### Étape 1: Extraire les Données
```bash
python3 scripts/weeklyviz.py extract \
  --input path/to/metrics.xlsx path/to/updates.md \
  --output source-bundle.json
```

#### Étape 2: Rédiger le Modèle de Rapport
Définissez le fichier `report-model.json` conformément au schéma [report.schema.json](references/report.schema.json).

#### Étape 3: Valider et Générer le HTML
```bash
# Valider les données et les règles des graphiques
python3 scripts/weeklyviz.py validate --report report-model.json

# Compiler en HTML
python3 scripts/weeklyviz.py render --report report-model.json --output weekly-report.html

# Valider l'accessibilité
node scripts/validate_html.mjs weekly-report.html
```

---

## 📋 Historique des Versions

*   **v0.11.0** (2026-06-09)
    - Structure des dossiers aplatie à la racine pour l'installation et l'exécution standard des agents.
    - Conception et mise à niveau premium du modèle `Editorial` avec arrière-plan pointillé, barre de style macOS, ombres portées solides, listes à puces et barres latérales.
    - Politique de sécurité pour exclure les données locales sensibles de Shiji dans le référentiel public.
*   **v0.1.0** (2026-06-09)
    - Version initiale.
    - Outil d'extraction pour CSV, XLSX, DOCX, MD et texte brut.
    - Validateur JSON Schema et règles de tracé strictes pour ECharts.
    - Compilation en rapport HTML interactif autonome hors-ligne.
