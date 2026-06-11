#!/usr/bin/env node

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { spawnSync } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";

import jpeg from "jpeg-js";
import pixelmatch from "pixelmatch";
import { chromium } from "playwright";
import { PNG } from "pngjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const DEFAULT_REPORT = path.join(ROOT, "evals", "fixtures", "report-model.json");
const DEFAULT_BASELINE = path.join(ROOT, "evals", "visual-baselines");
const DEFAULT_OUTPUT = path.join(ROOT, "output", "playwright", "visual-regression");
const CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const VIEWPORTS = [
  { id: "desktop", width: 1440, height: 1200 },
  { id: "laptop", width: 1024, height: 900 },
  { id: "tablet", width: 768, height: 900 },
  { id: "mobile", width: 390, height: 844 },
];

function parseArgs(argv) {
  const options = {
    update: false,
    report: DEFAULT_REPORT,
    baselineDir: DEFAULT_BASELINE,
    outputDir: DEFAULT_OUTPUT,
    themes: [],
    maxDiffRatio: 0.01,
  };
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === "--update") {
      options.update = true;
    } else if (argument === "--report") {
      options.report = path.resolve(argv[++index]);
    } else if (argument === "--baseline-dir") {
      options.baselineDir = path.resolve(argv[++index]);
    } else if (argument === "--output-dir") {
      options.outputDir = path.resolve(argv[++index]);
    } else if (argument === "--theme") {
      options.themes.push(...argv[++index].split(",").filter(Boolean));
    } else if (argument === "--max-diff-ratio") {
      options.maxDiffRatio = Number(argv[++index]);
    } else {
      throw new Error(`Unknown argument: ${argument}`);
    }
  }
  if (!Number.isFinite(options.maxDiffRatio) || options.maxDiffRatio < 0 || options.maxDiffRatio > 1) {
    throw new Error("--max-diff-ratio must be between 0 and 1");
  }
  return options;
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function writeJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`);
}

function run(command, args) {
  const result = spawnSync(command, args, {
    cwd: ROOT,
    encoding: "utf8",
    env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1" },
  });
  if (result.status !== 0) {
    const detail = [result.stdout, result.stderr].filter(Boolean).join("\n").trim();
    throw new Error(`${command} ${args.join(" ")} failed\n${detail}`);
  }
}

function loadTemplates(selectedThemes) {
  const templateDir = path.join(ROOT, "assets", "templates");
  const templates = fs.readdirSync(templateDir)
    .filter((name) => name.endsWith(".json"))
    .map((name) => readJson(path.join(templateDir, name)))
    .sort((a, b) => a.id.localeCompare(b.id));
  if (!selectedThemes.length) return templates;
  const selected = new Set(selectedThemes);
  const result = templates.filter((template) => selected.has(template.id));
  const missing = [...selected].filter((id) => !result.some((template) => template.id === id));
  if (missing.length) throw new Error(`Unknown theme(s): ${missing.join(", ")}`);
  return result;
}

function prepareReport(baseModel, template) {
  const model = structuredClone(baseModel);
  model.template = template.id;
  delete model.theme;
  model.metadata.generated_at = "2030-01-15T00:00:00+00:00";
  model.metadata.updated_at = model.metadata.generated_at;
  model.presentation = {
    ...(model.presentation || {}),
    layout: template.canonical_layout,
    section_layout: template.canonical_section_layout,
    density: "compact",
    show_toc: true,
  };
  delete model.presentation.layout_order;
  for (const section of model.sections || []) {
    section.layout = template.canonical_section_layout;
  }
  return model;
}

function designSignature(template) {
  return crypto
    .createHash("sha256")
    .update(JSON.stringify(template.design))
    .digest("hex")
    .slice(0, 16);
}

async function launchBrowser() {
  const executablePath = process.env.WEEKLYVIZ_CHROME_PATH || CHROME_PATH;
  const launchOptions = {
    headless: true,
    args: ["--font-render-hinting=none", "--force-color-profile=srgb"],
  };
  if (fs.existsSync(executablePath)) launchOptions.executablePath = executablePath;
  try {
    return await chromium.launch(launchOptions);
  } catch (error) {
    if (!launchOptions.executablePath) throw error;
    console.warn(`Chrome launch failed, falling back to Playwright Chromium: ${error.message}`);
    delete launchOptions.executablePath;
    return chromium.launch(launchOptions);
  }
}

async function collectMetrics(page) {
  return page.evaluate(() => {
    const root = document.documentElement;
    const body = document.body;
    const visible = (node) => {
      const style = getComputedStyle(node);
      const rect = node.getBoundingClientRect();
      return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
    };
    const textNodes = [...document.querySelectorAll("body *")].filter((node) => {
      if (!visible(node)) return false;
      if (["SCRIPT", "STYLE", "NOSCRIPT", "TEXTAREA"].includes(node.tagName)) return false;
      return [...node.childNodes].some((child) => child.nodeType === Node.TEXT_NODE && child.textContent.trim());
    });
    const fontSizes = textNodes.map((node) => Number.parseFloat(getComputedStyle(node).fontSize)).filter(Number.isFinite);
    const clipped = [...document.querySelectorAll("[data-path], table")].filter((node) => {
      if (!visible(node)) return false;
      const style = getComputedStyle(node);
      const clipsX = ["hidden", "clip"].includes(style.overflowX);
      return clipsX && node.scrollWidth > node.clientWidth + 2;
    }).map((node) => node.getAttribute("data-path") || node.className || node.tagName).slice(0, 20);
    const deadNavTargets = [...document.querySelectorAll('a[href^="#"]')].filter((link) => {
      const target = link.getAttribute("href").slice(1);
      return target && !document.getElementById(target);
    }).map((link) => link.getAttribute("href"));
    const kpiGrid = document.querySelector(".kpi-grid");
    const kpiColumns = kpiGrid
      ? getComputedStyle(kpiGrid).gridTemplateColumns.split(" ").filter(Boolean).length
      : 0;
    const chartNodes = [...document.querySelectorAll(".chart-canvas")];
    const report = document.querySelector(".report-wrap");
    const hero = document.querySelector(".report-hero");
    const firstCard = document.querySelector(".kpi-card, .metric-card, .chart-card, .work-item, .kanban-card");
    const firstSection = document.querySelector(".report-section");
    const firstNumeric = document.querySelector(".kpi-value, .metric-value, .progress-copy strong");
    const firstLabel = document.querySelector(".section-kicker, .kpi-label, .status-label");
    return {
      documentWidth: root.scrollWidth,
      viewportWidth: root.clientWidth,
      widthDelta: Math.max(0, root.scrollWidth - root.clientWidth),
      pageHeight: Math.max(root.scrollHeight, body.scrollHeight),
      reportWidth: report ? Math.round(report.getBoundingClientRect().width) : 0,
      minFontSize: fontSizes.length ? Math.min(...fontSizes) : 0,
      tinyTextCount: fontSizes.filter((size) => size < 9.9).length,
      clipped,
      deadNavTargets,
      kpiCount: document.querySelectorAll(".kpi-card").length,
      kpiColumns,
      sectionCount: document.querySelectorAll(".report-section").length,
      chartCount: chartNodes.length,
      renderedChartCount: chartNodes.filter((node) => node.querySelector("canvas, svg, .chart-fallback")).length,
      attributes: {
        template: root.dataset.templateId,
        layout: root.dataset.layout,
        cardShape: root.dataset.cardShape,
        sectionStyle: root.dataset.sectionStyle,
        heroStyle: root.dataset.heroStyle,
        chartStyle: root.dataset.chartStyle,
      },
      typography: {
        body: getComputedStyle(body).fontFamily,
        display: hero ? getComputedStyle(hero.querySelector("h1") || hero).fontFamily : "",
        numeric: firstNumeric ? getComputedStyle(firstNumeric).fontFamily : "",
        label: firstLabel ? getComputedStyle(firstLabel).fontFamily : "",
      },
      geometry: {
        cardRadius: firstCard ? getComputedStyle(firstCard).borderRadius : "",
        cardShadow: firstCard ? getComputedStyle(firstCard).boxShadow : "",
        sectionBorder: firstSection ? getComputedStyle(firstSection).borderTopStyle : "",
        heroBackground: hero ? getComputedStyle(hero).backgroundImage : "",
      },
      chartLanguage: window.WeeklyVizRuntime?.chartLanguage?.() || null,
    };
  });
}

function compareImage(currentPath, baselinePath, diffPath, maxDiffRatio) {
  if (!fs.existsSync(baselinePath)) {
    return { pass: false, ratio: 1, reason: "missing baseline" };
  }
  const current = jpeg.decode(fs.readFileSync(currentPath), { useTArray: true, formatAsRGBA: true });
  const baseline = jpeg.decode(fs.readFileSync(baselinePath), { useTArray: true, formatAsRGBA: true });
  if (current.width !== baseline.width || current.height !== baseline.height) {
    return {
      pass: false,
      ratio: 1,
      reason: `dimension mismatch ${current.width}x${current.height} vs ${baseline.width}x${baseline.height}`,
    };
  }
  const diff = new PNG({ width: current.width, height: current.height });
  const different = pixelmatch(
    baseline.data,
    current.data,
    diff.data,
    current.width,
    current.height,
    { threshold: 0.1, includeAA: false },
  );
  const ratio = different / (current.width * current.height);
  if (ratio > maxDiffRatio) {
    fs.mkdirSync(path.dirname(diffPath), { recursive: true });
    fs.writeFileSync(diffPath, PNG.sync.write(diff));
  }
  return { pass: ratio <= maxDiffRatio, ratio, reason: ratio <= maxDiffRatio ? "" : "pixel difference exceeded threshold" };
}

function structuralFailures(metrics, template, viewport, consoleErrors) {
  const expected = {
    template: template.id,
    layout: template.canonical_layout,
    cardShape: template.design.geometry.card_shape,
    sectionStyle: template.design.geometry.section_style,
    heroStyle: template.design.hero.style,
    chartStyle: template.design.chart.style,
  };
  const failures = [];
  for (const [key, value] of Object.entries(expected)) {
    if (metrics.attributes[key] !== value) {
      failures.push(`${key} expected ${value}, got ${metrics.attributes[key]}`);
    }
  }
  if (metrics.widthDelta > 1) failures.push(`horizontal overflow: ${metrics.widthDelta}px`);
  if (metrics.minFontSize < 9.9) failures.push(`minimum visible font is ${metrics.minFontSize}px`);
  if (metrics.tinyTextCount) failures.push(`${metrics.tinyTextCount} visible text node(s) below 10px`);
  if (metrics.clipped.length) failures.push(`clipped content: ${metrics.clipped.join(", ")}`);
  if (metrics.deadNavTargets.length) failures.push(`dead navigation: ${metrics.deadNavTargets.join(", ")}`);
  if (metrics.chartCount !== metrics.renderedChartCount) {
    failures.push(`rendered ${metrics.renderedChartCount}/${metrics.chartCount} charts`);
  }
  if (!metrics.chartLanguage || metrics.chartLanguage.style !== template.design.chart.style) {
    failures.push("chart language did not reach the runtime");
  }
  if (viewport.width >= 768 && metrics.kpiCount > 1 && metrics.kpiColumns < 2) {
    failures.push(`${viewport.id} KPI grid has ${metrics.kpiColumns} column(s)`);
  }
  if (viewport.id === "mobile" && metrics.kpiCount > 1 && metrics.kpiColumns !== 1) {
    failures.push(`mobile KPI grid has ${metrics.kpiColumns} column(s)`);
  }
  failures.push(...consoleErrors.map((message) => `browser console: ${message}`));
  return failures;
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  const templates = loadTemplates(options.themes);
  const baseModel = readJson(options.report);
  if (baseModel.metadata?.synthetic !== true) {
    throw new Error("Visual regression fixtures must set metadata.synthetic to true");
  }

  fs.rmSync(options.outputDir, { recursive: true, force: true });
  fs.mkdirSync(options.outputDir, { recursive: true });
  const reportsDir = path.join(options.outputDir, "reports");
  const currentDir = path.join(options.outputDir, "current");
  const diffDir = path.join(options.outputDir, "diff");
  const baselineImageDir = path.join(options.baselineDir, "screenshots");
  const baselineManifestPath = path.join(options.baselineDir, "manifest.json");
  if (options.update && !options.themes.length) {
    fs.rmSync(baselineImageDir, { recursive: true, force: true });
  }
  const previousManifest = fs.existsSync(baselineManifestPath) ? readJson(baselineManifestPath) : null;
  const manifest = {
    schemaVersion: 1,
    fixture: path.relative(ROOT, options.report),
    viewports: VIEWPORTS,
    themes: {},
  };

  for (const template of templates) {
    const modelPath = path.join(reportsDir, `${template.id}.json`);
    const htmlPath = path.join(reportsDir, `${template.id}.html`);
    writeJson(modelPath, prepareReport(baseModel, template));
    run("python3", [
      "scripts/weeklyviz.py", "render",
      "--report", modelPath,
      "--template", template.id,
      "--output", htmlPath,
    ]);
    run("node", ["scripts/validate_html.mjs", htmlPath]);
    manifest.themes[template.id] = {
      designSignature: designSignature(template),
      viewports: {},
    };
  }

  const browser = await launchBrowser();
  const failures = [];
  try {
    for (const viewport of VIEWPORTS) {
      const context = await browser.newContext({
        viewport: { width: viewport.width, height: viewport.height },
        deviceScaleFactor: 1,
        colorScheme: "light",
        reducedMotion: "reduce",
        locale: "zh-CN",
      });
      for (const template of templates) {
        const page = await context.newPage();
        const consoleErrors = [];
        page.on("console", (message) => {
          if (message.type() === "error") consoleErrors.push(message.text());
        });
        page.on("pageerror", (error) => consoleErrors.push(error.message));
        const htmlPath = path.join(reportsDir, `${template.id}.html`);
        await page.goto(pathToFileURL(htmlPath).href, { waitUntil: "load" });
        await page.emulateMedia({ reducedMotion: "reduce" });
        await page.addStyleTag({
          content: `
            *, *::before, *::after {
              animation-duration: 0s !important;
              animation-delay: 0s !important;
              transition: none !important;
              caret-color: transparent !important;
            }
            .toolbar, .editor-drawer, .toast, [data-export-buffer] { display: none !important; }
            .report-wrap { margin-top: 0 !important; }
          `,
        });
        await page.evaluate(() => document.fonts?.ready);
        await page.waitForFunction(() => [...document.querySelectorAll(".chart-canvas")].every(
          (node) => node.querySelector("canvas, svg, .chart-fallback"),
        ));
        await page.waitForTimeout(100);

        const metrics = await collectMetrics(page);
        const imageName = `${template.id}-${viewport.id}.jpg`;
        const currentPath = path.join(currentDir, imageName);
        const baselinePath = path.join(baselineImageDir, imageName);
        const diffPath = path.join(diffDir, imageName);
        fs.mkdirSync(currentDir, { recursive: true });
        await page.screenshot({
          path: currentPath,
          type: "jpeg",
          quality: 88,
          fullPage: true,
          animations: "disabled",
        });

        const structural = structuralFailures(metrics, template, viewport, consoleErrors);
        let visual = { pass: true, ratio: 0, reason: "" };
        if (options.update) {
          fs.mkdirSync(baselineImageDir, { recursive: true });
          fs.copyFileSync(currentPath, baselinePath);
        } else {
          visual = compareImage(currentPath, baselinePath, diffPath, options.maxDiffRatio);
          if (!visual.pass) structural.push(`visual: ${visual.reason} (${(visual.ratio * 100).toFixed(3)}%)`);
          const previousHeight = previousManifest?.themes?.[template.id]?.viewports?.[viewport.id]?.pageHeight;
          if (previousHeight && Math.abs(metrics.pageHeight - previousHeight) / previousHeight > 0.08) {
            structural.push(`page height changed from ${previousHeight}px to ${metrics.pageHeight}px`);
          }
        }
        manifest.themes[template.id].viewports[viewport.id] = {
          ...metrics,
          visualDiffRatio: visual.ratio,
        };
        if (structural.length) failures.push({
          theme: template.id,
          viewport: viewport.id,
          errors: structural,
        });
        console.log(
          `${structural.length ? "FAIL" : "PASS"} ${template.id}/${viewport.id}`
          + ` ${metrics.reportWidth}px wide, ${metrics.pageHeight}px tall`
          + (options.update ? " baseline updated" : `, diff ${(visual.ratio * 100).toFixed(3)}%`),
        );
        await page.close();
      }
      await context.close();
    }
  } finally {
    await browser.close();
  }

  writeJson(path.join(options.outputDir, "summary.json"), { ...manifest, failures });
  if (options.update && !failures.length) writeJson(baselineManifestPath, manifest);
  if (failures.length) {
    console.error(`\nVisual regression failed in ${failures.length} theme/viewport case(s):`);
    for (const failure of failures) {
      console.error(`- ${failure.theme}/${failure.viewport}: ${failure.errors.join("; ")}`);
    }
    process.exitCode = 1;
  } else {
    console.log(`\nVisual regression passed for ${templates.length} theme(s) across ${VIEWPORTS.length} viewport(s).`);
  }
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exitCode = 1;
});
