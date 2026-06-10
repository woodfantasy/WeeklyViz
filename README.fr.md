[中文](README.zh-CN.md) | [English](README.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md) | [Português](README.pt.md) | Français

<p align="center">
  <img src="assets/logo.svg" width="128" height="128" alt="WeeklyViz Logo">
</p>

<h1 align="center">WeeklyViz</h1>

<p align="center">
  <strong>Générateur de Rapports Hebdomadaires HTML Hors-ligne et Skill d'Agent Professionnel</strong>
</p>

<p align="center">
  <a href=""><img src="https://img.shields.io/badge/version-0.1.1-blue.svg" alt="Version"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
  <a href=""><img src="https://img.shields.io/badge/platform-Codex_/_Claude_Code-purple.svg" alt="Platform"></a>
</p>

<p align="center">
  Convertissez les mises à jour textuelles, feuilles de calcul et documents en <strong>rapports hebdomadaires HTML hors-ligne professionnels, adaptatifs, modifiables et traçables jusqu'à la source</strong>, générés automatiquement par votre Agent IA.
</p>

C'est une Claude Skill et un outil indépendant construit sous la spécification [Agent Skills](https://agentskills.io). Il est conçu pour fonctionner de manière fluide avec des Agents IA (comme Claude Code, Cursor ou Codex). Plutôt que d'exécuter des scripts Python ou de coder vous-même, il vous suffit d'installer ce skill et de laisser votre Agent IA faire tout le travail.

---

## 🖼️ Exemple de Résultat

<p align="center">
  <a href="assets/red-shiji-weekly-report.jpg">
    <img src="assets/red-shiji-weekly-report.jpg" width="860" alt="Exemple de rapport hebdomadaire éditorial généré par WeeklyViz">
  </a>
</p>

<p align="center"><sub>Un rapport éditorial complet généré avec WeeklyViz : synthèse exécutive, cartes KPI, progression des objectifs, visualisations, suivi des projets, risques et prochaines actions. Cliquez sur l'image pour l'afficher en pleine résolution.</sub></p>

---

## ✨ Fonctionnalités Clés

| Fonctionnalité | Description |
|----------------|-------------|
| 📊 **Extraction Multi-sources** | Analyse et traite automatiquement les fichiers `.xlsx`, `.csv`, `.docx`, `.md` et `.txt` pour en extraire les métriques et les listes. |
| 🎨 **Conception Éditoriale Adaptative** | Propose trois thèmes prédéfinis (`Executive`, `Editorial`, `Product Operations`) sans dépendances réseau externes (100% hors-ligne). |
| 🔗 **Traçabilité de la Source** | Lie automatiquement chaque KPI, barre de progression, graphique et élément à son fichier et sa ligne d'origine via des identifiants stables. |
| ✏️ **Édition Inline Interactive** | Le rapport HTML final permet de modifier les textes et les nombres en ligne, d'ajuster les couleurs de thème et d'exporter en PDF. |
| 📈 **Apache ECharts Embarqué** | Utilise un moteur ECharts local (`echarts.min.js`) pour tracer des graphiques en lignes, barres et beignets hors-ligne. |

---

## 🚀 Comment l'utiliser (Super Simple)

### 1. Installer la Skill
Ajoutez WeeklyViz au dossier de skills de votre Agent IA :

*   **Claude Code** : Placez ce dépôt dans `.claude/skills/weeklyviz` à la racine de votre projet.
*   **Cursor** : Placez ce dépôt dans `.cursor/skills/weeklyviz` à la racine de votre projet.
*   **Autres Agents** : Placez ce dépôt sous le chemin d'instructions personnalisées de votre agent.

### 2. Demandez simplement à votre Agent !
Vous **n'avez pas** besoin d'exécuter de commandes Python ni d'écrire de fichiers de configuration. Donnez simplement vos fichiers (tableaux, notes, textes copiés) à votre Agent IA et demandez :

> *"Hé Claude, utilise WeeklyViz pour générer un rapport hebdomadaire à partir de mes notes."*

L'agent lira automatiquement vos fichiers, en extraira les données, effectuera les validations et compilera le rapport HTML final hors ligne (`weekly-report.html`) en une seule fois.

---

## 🛠️ Détails du Développeur (Optionnel)

Si vous souhaitez exécuter WeeklyViz manuellement en ligne de commande :

```bash
# Extraer les données brutes dans un bundle
python3 scripts/weeklyviz.py extract --input notes.md data.xlsx --output source-bundle.json

# Valider le schéma du modèle de rapport
python3 scripts/weeklyviz.py validate --report report-model.json

# Compiler en rapport HTML autonome hors-ligne
python3 scripts/weeklyviz.py render --report report-model.json --output weekly-report.html
```

---

## 📋 Historique des Versions

*   **v0.1.1** (2026-06-09)
    - Structure des dossiers aplatie à la racine pour l'installation et l'exécution standard des agents.
    - Conception et mise à niveau premium du modèle `Editorial` avec arrière-plan pointillé, barre de style macOS, ombres portées solides, listes à puces et barres latérales.
    - Politique de sécurité pour exclure les données locales sensibles de Shiji dans le référentiel public.
*   **v0.1.0** (2026-06-09)
    - Version initiale.
