#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";

const file = process.argv[2];
if (!file) {
  console.error("Usage: node scripts/validate_html.mjs <weekly-report.html>");
  process.exit(2);
}

const absolute = path.resolve(file);
if (!fs.existsSync(absolute)) {
  console.error(`error: file not found: ${absolute}`);
  process.exit(2);
}

const html = fs.readFileSync(absolute, "utf8");
const errors = [];
const warnings = [];
const markupOnly = html
  .replace(/<script\b[\s\S]*?<\/script>/gi, "")
  .replace(/<style\b[\s\S]*?<\/style>/gi, "");
const styleBodies = [...html.matchAll(/<style\b[^>]*>([\s\S]*?)<\/style>/gi)].map((match) => match[1]).join("\n");
const codeScripts = [...html.matchAll(/<script(?![^>]*type="application\/json")[^>]*>([\s\S]*?)<\/script>/gi)]
  .map((match) => match[1]);
const weeklyVizRuntime = codeScripts.at(-1) || "";

function requirePattern(pattern, message) {
  if (!pattern.test(html)) errors.push(message);
}

requirePattern(/^<!doctype html>/i, "missing HTML5 doctype");
requirePattern(/<meta\s+name="viewport"/i, "missing responsive viewport");
requirePattern(/<meta\s+name="generator"\s+content="WeeklyViz/i, "missing WeeklyViz generator metadata");
requirePattern(/<nav\b[^>]*aria-label=/i, "toolbar navigation needs an accessible label");
requirePattern(/<main\b[^>]*id="report-main"/i, "missing semantic main landmark");
requirePattern(/<h1\b/i, "missing report h1");
// chart-canvas check is conditional on model.charts having elements
requirePattern(/id="report-model"/i, "missing embedded report model");
requirePattern(/id="report-baseline"/i, "missing embedded baseline model");
requirePattern(/prefers-reduced-motion/i, "missing reduced-motion CSS");
requirePattern(/@media\s+print/i, "missing print stylesheet");
requirePattern(/data-action="export"/i, "missing HTML export control");
requirePattern(/data-action="toggle-edit"/i, "missing edit-mode control");
requirePattern(/data-action="toggle-sources"/i, "missing source-detail control");
requirePattern(/data-action="print"/i, "missing print/PDF control");
requirePattern(/data-density=/i, "missing presentation density metadata");
requirePattern(/class="source-marker"/i, "missing compact source trace markers");
requirePattern(/window\.echarts|var\s+echarts|this\.echarts/i, "missing embedded ECharts runtime");

if (/\beval\s*\(/.test(weeklyVizRuntime) || /\bnew\s+Function\s*\(/.test(weeklyVizRuntime)) {
  errors.push("unsafe dynamic code execution detected");
}

const externalPatterns = [
  /<script\b[^>]*\bsrc=["'](?!data:)[^"']+/gi,
  /<link\b[^>]*\bhref=["'](?!data:|#)[^"']+/gi,
];
for (const pattern of externalPatterns) {
  const matches = html.match(pattern);
  if (matches) errors.push(`external resource detected: ${matches[0]}`);
}
if (/url\(\s*["']?https?:\/\//i.test(styleBodies)) {
  errors.push("external URL detected in CSS");
}

const editableTrue = markupOnly.match(/contenteditable="true"/g)?.length ?? 0;
if (editableTrue > 0) {
  errors.push(`report must start read-only, found ${editableTrue} contenteditable=true element(s)`);
}

const modelMatch = html.match(/<script\s+type="application\/json"\s+id="report-model">([\s\S]*?)<\/script>/i);
if (!modelMatch) {
  errors.push("unable to locate embedded report model");
} else {
  try {
    const model = JSON.parse(modelMatch[1]);
    if (!model.metadata?.report_id) errors.push("embedded model is missing metadata.report_id");
    if (!model.metadata?.title) errors.push("embedded model is missing metadata.title");
    if (!Array.isArray(model.sources)) errors.push("embedded model sources must be an array");
    if (model.presentation?.show_toc !== false && !/class="report-index"/i.test(markupOnly)) {
      errors.push("missing report index navigation");
    }
    if (Array.isArray(model.charts) && model.charts.length > 0) {
      if (!/class="chart-canvas"/i.test(html)) {
        errors.push("missing chart container");
      }
    }
    const sourceIds = new Set((model.sources || []).map((source) => source.id));
    for (const collection of ["kpis", "progress", "charts", "metrics", "okrs"]) {
      for (const [index, item] of (model[collection] || []).entries()) {
        if (!item.source_refs?.length) {
          errors.push(`${collection}[${index}] has no source_refs`);
        } else {
          for (const sourceRef of item.source_refs) {
            if (!sourceIds.has(sourceRef)) errors.push(`${collection}[${index}] references unknown source ${sourceRef}`);
          }
        }
      }
    }
  } catch (error) {
    errors.push(`embedded report model is invalid JSON: ${error.message}`);
  }
}

const sizeMb = Buffer.byteLength(html) / 1024 / 1024;
if (sizeMb > 5) warnings.push(`file size is ${sizeMb.toFixed(2)} MB, above the 5 MB target`);

const duplicateIds = [];
const seenIds = new Set();
for (const match of html.matchAll(/\sid="([^"]+)"/g)) {
  if (seenIds.has(match[1])) duplicateIds.push(match[1]);
  seenIds.add(match[1]);
}
if (duplicateIds.length) errors.push(`duplicate HTML ids: ${[...new Set(duplicateIds)].join(", ")}`);

for (const warning of warnings) console.warn(`warning: ${warning}`);
if (errors.length) {
  for (const error of errors) console.error(`error: ${error}`);
  process.exit(1);
}

console.log(`Validated ${absolute}`);
console.log(`  size: ${sizeMb.toFixed(2)} MB`);
console.log(`  embedded model: valid`);
console.log(`  offline resources: valid`);
console.log(`  accessibility hooks: valid`);
