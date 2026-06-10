[中文](README.zh-CN.md) | [English](README.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | Español | [Português](README.pt.md) | [Français](README.fr.md)

<p align="center">
  <img src="assets/logo.svg" width="128" height="128" alt="WeeklyViz Logo">
</p>

<h1 align="center">WeeklyViz</h1>

<p align="center">
  <strong>Generador de Informes Semanales HTML Offline y Skill de Agente Profesional</strong>
</p>

<p align="center">
  <a href=""><img src="https://img.shields.io/badge/version-0.1.1-blue.svg" alt="Version"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
  <a href=""><img src="https://img.shields.io/badge/platform-Codex_/_Claude_Code-purple.svg" alt="Platform"></a>
</p>

<p align="center">
  Convierta actualizaciones de texto, hojas de cálculo y documentos en <strong>informes semanales HTML offline profesionales, adaptables, editables y con trazabilidad de origen</strong>, generados automáticamente por su Agente de IA.
</p>

Es un Claude Skill y herramienta independiente construida bajo la especificación [Agent Skills](https://agentskills.io). Está diseñado para funcionar perfectamente con Agentes de IA (como Claude Code, Cursor o Codex). En lugar de ejecutar scripts de python o codificar usted mismo, simplemente instale el skill y deje que su Agente de IA haga todo el trabajo.

---

## 🖼️ Ejemplo de Resultado

<p align="center">
  <a href="assets/red-shiji-weekly-report.jpg">
    <img src="assets/red-shiji-weekly-report.jpg" width="860" alt="Ejemplo de informe semanal editorial generado por WeeklyViz">
  </a>
</p>

<p align="center"><sub>Un informe editorial completo generado con WeeklyViz: resumen ejecutivo, tarjetas KPI, progreso de objetivos, visualizaciones, avances de proyectos, riesgos y próximas acciones. Haga clic en la imagen para verla en resolución completa.</sub></p>

---

## ✨ Capacidades Clave

| Capacidad | Descripción |
|------------|-------------|
| 📊 **Extracción Multifuente** | Procesa automáticamente archivos `.xlsx`, `.csv`, `.docx`, `.md` y `.txt` para extraer métricas y listas de progreso. |
| 🎨 **Diseño Editorial Adaptativo** | Ofrece tres temas integrados (`Executive`, `Editorial`, `Product Operations`) con diseños adaptables y sin dependencias de red externas. |
| 🔗 **Trazabilidad de Origen** | Vincula automáticamente cada KPI, barra de progreso, gráfico y lista con su archivo y línea de origen mediante IDs hash estables. |
| ✏️ **Edición Interactiva** | El HTML generado permite editar textos y números en línea, cambiar colores de temas y exportar directamente a formato impreso o PDF. |
| 📈 **Integración de ECharts** | Incluye un motor de ECharts local (`echarts.min.js`) para renderizar gráficos de línea, barra, rosca y embudo sin conexión. |

---

## 🚀 Cómo Usar (Muy Simple)

### 1. Instalar la Skill
Agregue WeeklyViz a la carpeta de habilidades de su Agente de IA:

*   **Claude Code**: Clone este repositorio dentro de `.claude/skills/weeklyviz` en la raíz de su proyecto.
*   **Cursor**: Clone este repositorio dentro de `.cursor/skills/weeklyviz` en la raíz de su proyecto.
*   **Otros Agentes**: Coloque el repositorio bajo la ruta de instrucciones personalizadas de su agente.

### 2. ¡Solo Pídaselo a su Agente!
Usted **no** necesita ejecutar comandos de Python ni escribir archivos de configuración. Simplemente proporcione sus archivos (hojas de cálculo, notas, textos pegados) a su Agente de IA y pídale:

> *"Oye Claude, usa WeeklyViz para generar un informe semanal a partir de mi notas."*

El agente leerá automáticamente sus archivos, extraerá los datos, validará las restricciones y compilará el informe HTML final fuera de línea (`weekly-report.html`) en un solo paso.

---

## 🛠️ Detalles del Desarrollador (Opcional)

Si desea ejecutar WeeklyViz manualmente a través de la línea de comandos:

```bash
# Extraer datos sin procesar en un bundle
python3 scripts/weeklyviz.py extract --input notes.md data.xlsx --output source-bundle.json

# Validar el esquema del modelo de reporte
python3 scripts/weeklyviz.py validate --report report-model.json

# Compilar en un archivo HTML autónomo
python3 scripts/weeklyviz.py render --report report-model.json --output weekly-report.html
```

---

## 📋 Versiones de Lanzamiento

*   **v0.1.1** (2026-06-09)
    - Estructura de directorios aplanada a la raíz para la instalación y ejecución estándar de agentes.
    - Diseño y actualización premium de la plantilla `Editorial` con fondos de puntos, barra de estilo macOS, sombras sólidas desplazadas, listas de puntos y barras laterales.
    - Política de seguridad para excluir datos locales sensibles de Shiji en el repositorio público.
*   **v0.1.0** (2026-06-09)
    - Versión inicial.
