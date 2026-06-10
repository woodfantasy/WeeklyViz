(() => {
  "use strict";

  const modelNode = document.getElementById("report-model");
  const baselineNode = document.getElementById("report-baseline");
  const embeddedModel = JSON.parse(modelNode.textContent);
  const baseline = JSON.parse(baselineNode.textContent);
  const storageKey = `weeklyviz:${embeddedModel.metadata.report_id}`;
  const history = [];
  const chartInstances = new Map();
  const editSnapshots = new WeakMap();
  const inputSnapshots = new WeakMap();
  let saveTimer = 0;
  let model = chooseNewestModel(embeddedModel, loadStoredModel());

  function chooseNewestModel(embedded, stored) {
    if (!stored || stored.metadata?.report_id !== embedded.metadata?.report_id) return embedded;
    const embeddedTime = Date.parse(embedded.metadata?.updated_at || 0) || 0;
    const storedTime = Date.parse(stored.metadata?.updated_at || 0) || 0;
    return storedTime > embeddedTime ? stored : embedded;
  }

  function loadStoredModel() {
    try {
      const raw = localStorage.getItem(storageKey);
      return raw ? JSON.parse(raw) : null;
    } catch (_error) {
      return null;
    }
  }

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function getPath(object, path) {
    return path.split(".").reduce((value, key) => value?.[key], object);
  }

  function setPath(object, path, value) {
    const parts = path.split(".");
    const finalKey = parts.pop();
    const parent = parts.reduce((current, key) => {
      if (current[key] === undefined) current[key] = /^\d+$/.test(key) ? [] : {};
      return current[key];
    }, object);
    parent[finalKey] = value;
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function pushHistory() {
    history.push(clone(model));
    if (history.length > 50) history.shift();
    updateUndoState();
  }

  function undo() {
    const previous = history.pop();
    if (!previous) return;
    model = previous;
    refreshAll();
    persistNow();
    toast("已撤销上一步修改");
  }

  function updateUndoState() {
    const button = document.querySelector('[data-action="undo"]');
    if (button) button.disabled = history.length === 0;
  }

  function syncSourceToggle() {
    const visible = document.body.classList.contains("sources-visible");
    const button = document.querySelector('[data-action="toggle-sources"]');
    if (!button) return;
    button.setAttribute("aria-pressed", String(visible));
    button.textContent = visible ? "收起来源" : "来源";
  }

  function toggleSources() {
    document.body.classList.toggle("sources-visible");
    syncSourceToggle();
    toast(document.body.classList.contains("sources-visible") ? "已展开完整来源" : "已收起来源细节");
  }

  function persistSoon() {
    window.clearTimeout(saveTimer);
    saveTimer = window.setTimeout(persistNow, 250);
  }

  function persistNow() {
    model.metadata.updated_at = new Date().toISOString();
    modelNode.textContent = JSON.stringify(model);
    try {
      localStorage.setItem(storageKey, JSON.stringify(model));
    } catch (_error) {
      toast("浏览器未允许本地保存，导出仍然可用");
    }
  }

  function toast(message) {
    const node = document.querySelector(".toast");
    node.textContent = message;
    node.classList.add("visible");
    window.clearTimeout(node._hideTimer);
    node._hideTimer = window.setTimeout(() => node.classList.remove("visible"), 2200);
  }

  function setEditMode(enabled) {
    document.body.classList.toggle("edit-mode-active", enabled);
    document.querySelectorAll("[data-path]").forEach((node) => {
      node.setAttribute("contenteditable", enabled ? "true" : "false");
    });
    const button = document.querySelector('[data-action="toggle-edit"]');
    button.setAttribute("aria-pressed", String(enabled));
    button.textContent = enabled ? "完成编辑" : "编辑";
    if (enabled) toast("文字编辑已开启，修改会自动保存");
  }

  function syncContentBindings() {
    document.title = model.metadata?.title || document.title;
    document.querySelectorAll("[data-path]").forEach((node) => {
      if (document.activeElement === node) return;
      const value = getPath(model, node.dataset.path);
      if (value !== undefined && node.textContent !== String(value)) {
        node.textContent = value;
      }
    });
  }

  function bindEditableContent() {
    document.addEventListener("beforeinput", (event) => {
      const node = event.target.closest('[contenteditable="true"][data-path]');
      if (node && !editSnapshots.has(node)) editSnapshots.set(node, clone(model));
    });
    document.addEventListener("focusin", (event) => {
      const node = event.target.closest('[contenteditable="true"][data-path]');
      if (!node || editSnapshots.has(node)) return;
      editSnapshots.set(node, clone(model));
    });
    document.addEventListener("input", (event) => {
      const node = event.target.closest('[contenteditable="true"][data-path]');
      if (!node) return;
      setPath(model, node.dataset.path, node.textContent.trim());
      if (node.dataset.path === "metadata.title") document.title = node.textContent.trim();
      persistSoon();
    });
    document.addEventListener("focusout", (event) => {
      const node = event.target.closest("[data-path]");
      if (!node || !editSnapshots.has(node)) return;
      const before = editSnapshots.get(node);
      editSnapshots.delete(node);
      if (JSON.stringify(before) !== JSON.stringify(model)) {
        history.push(before);
        if (history.length > 50) history.shift();
        updateUndoState();
      }
    });
  }

  function openDrawer(tab = "data") {
    document.body.classList.add("drawer-open");
    const drawer = document.querySelector(".editor-drawer");
    drawer.setAttribute("aria-hidden", "false");
    switchTab(tab);
    window.setTimeout(() => drawer.querySelector("button")?.focus(), 0);
  }

  function closeDrawer() {
    document.body.classList.remove("drawer-open");
    document.querySelector(".editor-drawer").setAttribute("aria-hidden", "true");
  }

  function switchTab(tab) {
    document.querySelectorAll("[data-editor-tab]").forEach((button) => {
      button.setAttribute("aria-selected", String(button.dataset.editorTab === tab));
    });
    document.querySelectorAll("[data-editor-panel]").forEach((panel) => {
      panel.hidden = panel.dataset.editorPanel !== tab;
    });
  }

  function field(label, path, value, type = "text", extra = "") {
    if (type === "textarea") {
      return `<div class="field"><label>${escapeHtml(label)}</label><textarea aria-label="${escapeHtml(label)}" data-model-input="${escapeHtml(path)}" ${extra}>${escapeHtml(value)}</textarea></div>`;
    }
    return `<div class="field"><label>${escapeHtml(label)}</label><input aria-label="${escapeHtml(label)}" type="${type}" value="${escapeHtml(value)}" data-model-input="${escapeHtml(path)}" ${extra}></div>`;
  }

  function renderDataEditor() {
    const panel = document.querySelector('[data-editor-panel="data"]');
    const groups = [];
    model.kpis?.forEach((item, index) => {
      groups.push(`<section class="editor-group"><h3>KPI · ${escapeHtml(item.label)}</h3>
        ${field("名称", `kpis.${index}.label`, item.label)}
        ${field("展示值", `kpis.${index}.display`, item.display ?? `${item.value ?? ""}${item.unit ?? ""}`)}
        ${field("原始值", `kpis.${index}.value`, item.value ?? "", typeof item.value === "number" ? "number" : "text", 'step="any"')}
        ${field("单位", `kpis.${index}.unit`, item.unit ?? "")}
        ${field("说明", `kpis.${index}.note`, item.note ?? "", "textarea")}
      </section>`);
    });
    model.progress?.forEach((item, index) => {
      groups.push(`<section class="editor-group"><h3>进度 · ${escapeHtml(item.label)}</h3>
        ${field("名称", `progress.${index}.label`, item.label)}
        ${field("当前值", `progress.${index}.current`, item.current, "number", 'step="any"')}
        ${field("目标值", `progress.${index}.target`, item.target, "number", 'step="any" min="0.000001"')}
        ${field("单位", `progress.${index}.unit`, item.unit ?? "")}
      </section>`);
    });
    model.charts?.forEach((chart, chartIndex) => {
      const seriesFields = chart.series.map((series, seriesIndex) => {
        const values = series.values.map((value) => Array.isArray(value) ? value.join(":") : value).join(", ");
        return `${field(`系列 ${seriesIndex + 1} 名称`, `charts.${chartIndex}.series.${seriesIndex}.name`, series.name)}
          ${field(`系列 ${seriesIndex + 1} 数据`, `charts.${chartIndex}.series.${seriesIndex}.values`, values, "textarea", `data-series-values="${chartIndex}:${seriesIndex}"`)}`;
      }).join("");
      groups.push(`<section class="editor-group"><h3>图表 · ${escapeHtml(chart.title)}</h3>
        ${field("标题", `charts.${chartIndex}.title`, chart.title)}
        ${field("业务问题", `charts.${chartIndex}.question`, chart.question)}
        ${field("单位", `charts.${chartIndex}.unit`, chart.unit)}
        ${field("标签（逗号分隔）", `charts.${chartIndex}.labels`, (chart.labels || []).join(", "), "textarea", `data-chart-labels="${chartIndex}"`)}
        ${seriesFields}
        ${field("洞察", `charts.${chartIndex}.insight`, chart.insight, "textarea")}
      </section>`);
    });
    panel.innerHTML = groups.length ? groups.join("") : "<p>当前报告没有可编辑的指标或图表数据。</p>";
  }

  function parseSeriesValues(raw) {
    return raw.split(/[,，\n]+/).map((part) => part.trim()).filter(Boolean).map((part) => {
      if (part.includes(":")) {
        const point = part.split(":").map((value) => Number(value.trim()));
        return point.every(Number.isFinite) ? point : part;
      }
      const number = Number(part);
      return Number.isFinite(number) ? number : part;
    });
  }

  function bindDataEditor() {
    const panel = document.querySelector('[data-editor-panel="data"]');
    panel.addEventListener("focusin", (event) => {
      const input = event.target.closest("[data-model-input]");
      if (input && !inputSnapshots.has(input)) inputSnapshots.set(input, clone(model));
    });
    panel.addEventListener("input", (event) => {
      const input = event.target.closest("[data-model-input]");
      if (!input) return;
      if (!inputSnapshots.has(input)) inputSnapshots.set(input, clone(model));
      let value = input.value;
      if (input.dataset.chartLabels !== undefined) {
        value = value.split(/[,，\n]+/).map((part) => part.trim()).filter(Boolean);
      } else if (input.dataset.seriesValues !== undefined) {
        value = parseSeriesValues(value);
      } else if (input.type === "number") {
        value = Number(value);
      }
      setPath(model, input.dataset.modelInput, value);
      syncContentBindings();
      refreshProgress();
      renderCharts();
      persistSoon();
    });
    panel.addEventListener("focusout", (event) => {
      const input = event.target.closest("[data-model-input]");
      if (!input || !inputSnapshots.has(input)) return;
      const before = inputSnapshots.get(input);
      inputSnapshots.delete(input);
      if (JSON.stringify(before) !== JSON.stringify(model)) {
        history.push(before);
        if (history.length > 50) history.shift();
        updateUndoState();
        toast("数据已更新");
      }
    });
  }

  function renderThemeEditor() {
    const panel = document.querySelector('[data-editor-panel="theme"]');
    const labels = {
      primary: "主色",
      accent: "强调色",
      background: "页面背景",
      surface: "内容表面",
      text: "正文",
      muted: "辅助文字",
    };
    const colorFields = Object.entries(labels).map(([key, label]) => `
      <div class="field">
        <label>${label}</label>
        <div class="color-field">
          <input type="color" value="${escapeHtml(model.theme[key])}" data-theme-color="${key}" aria-label="${label}取色器">
          <input type="text" value="${escapeHtml(model.theme[key])}" data-theme-text="${key}" aria-label="${label}颜色值" pattern="#[0-9A-Fa-f]{6}">
        </div>
      </div>
    `).join("");

    const currentLayout = model.presentation?.layout || "newsletter";
    const currentDensity = model.presentation?.density || "balanced";

    const presentationFields = `
      <div class="field">
        <label>周报排版 (Layout)</label>
        <select data-presentation-select="layout" aria-label="排版风格选择">
          <option value="dashboard" ${currentLayout === "dashboard" ? "selected" : ""}>管理驾驶舱大屏 (Dashboard)</option>
          <option value="newsletter" ${currentLayout === "newsletter" ? "selected" : ""}>叙事型周刊 (Newsletter)</option>
          <option value="kanban" ${currentLayout === "kanban" ? "selected" : ""}>敏捷研发看板 (Kanban)</option>
        </select>
      </div>
      <div class="field">
        <label>信息密度 (Density)</label>
        <select data-presentation-select="density" aria-label="信息密度选择">
          <option value="compact" ${currentDensity === "compact" ? "selected" : ""}>紧凑 (Compact)</option>
          <option value="balanced" ${currentDensity === "balanced" ? "selected" : ""}>适中 (Balanced)</option>
          <option value="spacious" ${currentDensity === "spacious" ? "selected" : ""}>宽松 (Spacious)</option>
        </select>
      </div>
    `;

    panel.innerHTML = presentationFields + colorFields + '<div class="contrast-result" data-contrast-result></div>';
    updateContrastResult();
  }

  function parseHex(color) {
    const match = /^#([0-9a-f]{6})$/i.exec(color);
    if (!match) return null;
    return [0, 2, 4].map((offset) => parseInt(match[1].slice(offset, offset + 2), 16) / 255);
  }

  function luminance(color) {
    const rgb = parseHex(color);
    if (!rgb) return 0;
    const values = rgb.map((value) => value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4);
    return 0.2126 * values[0] + 0.7152 * values[1] + 0.0722 * values[2];
  }

  function contrastRatio(a, b) {
    const one = luminance(a);
    const two = luminance(b);
    return (Math.max(one, two) + 0.05) / (Math.min(one, two) + 0.05);
  }

  function updateContrastResult() {
    const node = document.querySelector("[data-contrast-result]");
    if (!node) return;
    const ratio = contrastRatio(model.theme.text, model.theme.surface);
    node.textContent = `正文与表面对比度 ${ratio.toFixed(2)}:1 · ${ratio >= 4.5 ? "通过 WCAG AA" : "未达到 WCAG AA，请调整颜色"}`;
    node.style.color = ratio >= 4.5 ? "var(--success)" : "var(--danger)";
  }

  function bindThemeEditor() {
    const panel = document.querySelector('[data-editor-panel="theme"]');
    panel.addEventListener("focusin", (event) => {
      const input = event.target.closest("[data-theme-color], [data-theme-text]");
      if (input && !inputSnapshots.has(input)) inputSnapshots.set(input, clone(model));
    });
    panel.addEventListener("input", (event) => {
      const input = event.target.closest("[data-theme-color], [data-theme-text]");
      if (!input) return;
      const key = input.dataset.themeColor || input.dataset.themeText;
      if (!/^#[0-9a-f]{6}$/i.test(input.value)) {
        return;
      }
      if (!inputSnapshots.has(input)) inputSnapshots.set(input, clone(model));
      model.theme[key] = input.value.toUpperCase();
      applyTheme();
      const partner = panel.querySelector(
        input.dataset.themeColor ? `[data-theme-text="${key}"]` : `[data-theme-color="${key}"]`
      );
      if (partner) partner.value = model.theme[key];
      updateContrastResult();
      renderCharts();
      persistSoon();
    });
    panel.addEventListener("change", (event) => {
      const select = event.target.closest("[data-presentation-select]");
      if (!select) return;
      pushHistory();
      model.presentation = model.presentation || {};
      model.presentation[select.dataset.presentationSelect] = select.value;
      applyPresentation();
      persistSoon();
      toast("排版配置已更新");
    });
    panel.addEventListener("focusout", (event) => {
      const input = event.target.closest("[data-theme-color], [data-theme-text]");
      if (!input || !inputSnapshots.has(input)) return;
      const before = inputSnapshots.get(input);
      inputSnapshots.delete(input);
      if (JSON.stringify(before) !== JSON.stringify(model)) {
        history.push(before);
        if (history.length > 50) history.shift();
        updateUndoState();
        toast("主题已更新");
      }
    });
  }

  function applyTheme() {
    const root = document.documentElement;
    Object.entries(model.theme || {}).forEach(([key, value]) => {
      if (/^#[0-9a-f]{6}$/i.test(value)) root.style.setProperty(`--${key}`, value);
    });
  }

  function applyPresentation() {
    const root = document.documentElement;
    model.presentation = model.presentation || {};
    const layout = model.presentation.layout || "newsletter";
    const density = model.presentation.density || "balanced";
    root.setAttribute("data-layout", layout);
    root.setAttribute("data-density", density);
    window.setTimeout(resizeCharts, 50);
  }

  function refreshProgress() {
    model.progress?.forEach((item, index) => {
      const node = document.querySelectorAll(".progress-item")[index];
      if (!node) return;
      const current = Number(item.current);
      const target = Number(item.target);
      const percent = target > 0 ? current / target * 100 : 0;
      node.querySelector(".progress-copy h3").textContent = item.label;
      node.querySelector(".progress-copy strong").textContent = `${current} / ${target} ${item.unit || ""}`;
      node.querySelector(".progress-fill").style.width = `${Math.min(Math.max(percent, 0), 100)}%`;
      node.querySelector(".progress-meta > span").textContent = `${percent.toFixed(1)}%`;
      const track = node.querySelector(".progress-track");
      track.setAttribute("aria-valuemax", String(target));
      track.setAttribute("aria-valuenow", String(current));
    });
  }

  function cssColor(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  function chartPalette() {
    return [
      cssColor("--primary"),
      cssColor("--accent"),
      cssColor("--success"),
      cssColor("--warning"),
      "#3B82F6",
      "#D65A8A",
    ];
  }

  function commonChartOption(chart) {
    const muted = cssColor("--muted");
    const border = cssColor("--border");
    return {
      animationDuration: matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 500,
      color: chartPalette(),
      textStyle: {
        color: muted,
        fontFamily: getComputedStyle(document.body).fontFamily,
      },
      tooltip: {
        trigger: chart.type === "scatter" ? "item" : "axis",
        confine: true,
        borderWidth: 0,
        backgroundColor: cssColor("--text"),
        textStyle: { color: cssColor("--surface") },
        valueFormatter: (value) => `${value}${chart.unit ? ` ${chart.unit}` : ""}`,
      },
      legend: {
        top: 3,
        right: 0,
        textStyle: { color: muted, fontSize: 10 },
        itemWidth: 12,
        itemHeight: 7,
      },
      grid: { left: 52, right: 18, top: 52, bottom: 42, containLabel: true },
      xAxis: {
        type: "category",
        data: chart.labels || [],
        axisLine: { lineStyle: { color: border } },
        axisTick: { show: false },
        axisLabel: { color: muted, fontSize: 10, hideOverlap: true },
      },
      yAxis: {
        type: "value",
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { lineStyle: { color: border, type: "dashed" } },
        axisLabel: { color: muted, fontSize: 10 },
      },
    };
  }

  function waterfallOption(chart) {
    const values = chart.series[0].values.map(Number);
    let running = 0;
    const base = [];
    const positive = [];
    const negative = [];
    values.forEach((value) => {
      if (value >= 0) {
        base.push(running);
        positive.push(value);
        negative.push("-");
      } else {
        base.push(running + value);
        positive.push("-");
        negative.push(-value);
      }
      running += value;
    });
    return {
      ...commonChartOption(chart),
      tooltip: { ...commonChartOption(chart).tooltip, trigger: "axis" },
      series: [
        { type: "bar", stack: "waterfall", itemStyle: { color: "transparent" }, emphasis: { itemStyle: { color: "transparent" } }, data: base },
        { name: "增加", type: "bar", stack: "waterfall", itemStyle: { color: cssColor("--success") }, data: positive },
        { name: "减少", type: "bar", stack: "waterfall", itemStyle: { color: cssColor("--danger") }, data: negative },
      ],
    };
  }

  function optionForChart(chart) {
    const common = commonChartOption(chart);
    if (chart.type === "donut" || chart.type === "pie") {
      return {
        ...common,
        tooltip: { ...common.tooltip, trigger: "item" },
        legend: { ...common.legend, orient: "vertical", top: "middle", right: 0 },
        series: [{
          name: chart.series[0].name,
          type: "pie",
          radius: chart.type === "donut" ? ["48%", "72%"] : "70%",
          center: ["42%", "54%"],
          avoidLabelOverlap: true,
          itemStyle: { borderColor: cssColor("--surface"), borderWidth: 3 },
          label: { formatter: "{b}\n{d}%", color: cssColor("--muted"), fontSize: 10 },
          data: chart.labels.map((name, index) => ({ name, value: chart.series[0].values[index] })),
        }],
      };
    }
    if (chart.type === "funnel") {
      return {
        ...common,
        tooltip: { ...common.tooltip, trigger: "item" },
        series: [{
          name: chart.series[0].name,
          type: "funnel",
          left: "12%",
          width: "74%",
          top: 35,
          bottom: 20,
          label: { color: cssColor("--muted"), formatter: `{b}  {c}${chart.unit || ""}` },
          itemStyle: { borderColor: cssColor("--surface"), borderWidth: 2 },
          data: chart.labels.map((name, index) => ({ name, value: chart.series[0].values[index] })),
        }],
      };
    }
    if (chart.type === "waterfall") return waterfallOption(chart);
    if (chart.type === "scatter") {
      return {
        ...common,
        xAxis: { ...common.yAxis, name: chart.x_label || "" },
        yAxis: { ...common.yAxis, name: chart.y_label || "" },
        series: chart.series.map((series) => ({
          name: series.name,
          type: "scatter",
          symbolSize: 11,
          data: series.values,
        })),
      };
    }
    if (chart.type === "heatmap") {
      const yLabels = chart.y_labels || chart.series[0].y_labels || [];
      const values = chart.series[0].values;
      const numeric = values.map((point) => Number(point[2])).filter(Number.isFinite);
      return {
        ...common,
        tooltip: { ...common.tooltip, position: "top" },
        xAxis: { ...common.xAxis, data: chart.labels || [] },
        yAxis: { ...common.xAxis, data: yLabels },
        visualMap: {
          min: Math.min(...numeric, 0),
          max: Math.max(...numeric, 1),
          calculable: false,
          orient: "horizontal",
          left: "center",
          bottom: 0,
          inRange: { color: [cssColor("--soft-primary"), cssColor("--primary")] },
        },
        series: [{ type: "heatmap", data: values, label: { show: true, color: cssColor("--text") } }],
      };
    }
    const horizontal = chart.type === "horizontal-bar";
    const seriesType = ["bar", "horizontal-bar", "grouped-bar", "stacked-bar"].includes(chart.type) ? "bar" : "line";
    const option = {
      ...common,
      xAxis: horizontal ? common.yAxis : common.xAxis,
      yAxis: horizontal ? common.xAxis : common.yAxis,
      series: chart.series.map((series, index) => ({
        name: series.name,
        type: seriesType,
        data: series.values,
        smooth: seriesType === "line",
        symbolSize: 7,
        stack: chart.type === "stacked-bar" ? "total" : undefined,
        areaStyle: chart.type === "area" ? { opacity: index === 0 ? 0.19 : 0.08 } : undefined,
        lineStyle: seriesType === "line" ? { width: 3 } : undefined,
        itemStyle: seriesType === "bar" ? { borderRadius: horizontal ? [0, 6, 6, 0] : [6, 6, 0, 0] } : undefined,
      })),
    };
    if (horizontal) option.yAxis.data = chart.labels || [];
    return option;
  }

  function renderTimeline(node, chart) {
    node.innerHTML = `<div class="timeline-view">${(chart.labels || []).map((label, index) => `
      <div class="timeline-row">
        <strong>${escapeHtml(label)}</strong><span class="timeline-dot"></span>
        <span>${escapeHtml(chart.series[0]?.values[index]?.name ?? chart.series[0]?.values[index] ?? "")}</span>
      </div>`).join("")}</div>`;
  }

  function renderTable(node, chart) {
    const headings = chart.series.map((series) => `<th>${escapeHtml(series.name)}</th>`).join("");
    const rows = (chart.labels || []).map((label, rowIndex) => `
      <tr><th>${escapeHtml(label)}</th>${chart.series.map((series) => `<td>${escapeHtml(series.values[rowIndex])}</td>`).join("")}</tr>
    `).join("");
    node.innerHTML = `<div class="chart-fallback table-wrap"><table><thead><tr><th>项目</th>${headings}</tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function renderCharts() {
    model.charts?.forEach((chart) => {
      const node = document.querySelector(`[data-chart-id="${CSS.escape(chart.id)}"]`);
      if (!node) return;
      const existing = chartInstances.get(chart.id);
      if (existing) {
        existing.dispose();
        chartInstances.delete(chart.id);
      }
      node.innerHTML = "";
      node.setAttribute("aria-label", `${chart.title}: ${chart.insight}`);
      if (chart.type === "timeline") {
        renderTimeline(node, chart);
        return;
      }
      if (chart.type === "table") {
        renderTable(node, chart);
        return;
      }
      if (!window.echarts) {
        node.innerHTML = '<p class="chart-fallback">图表运行时未加载。</p>';
        return;
      }
      const instance = window.echarts.init(node, null, { renderer: "canvas" });
      instance.setOption(optionForChart(chart));
      chartInstances.set(chart.id, instance);
    });
  }

  function resizeCharts() {
    chartInstances.forEach((chart) => chart.resize());
  }

  function resetReport() {
    if (!window.confirm("恢复到生成时的报告内容？当前修改将被清除。")) return;
    pushHistory();
    model = clone(baseline);
    try {
      localStorage.removeItem(storageKey);
    } catch (_error) {}
    refreshAll();
    persistNow();
    toast("已恢复生成时版本");
  }

  function serializeReportDocument() {
    const cloneRoot = document.documentElement.cloneNode(true);
    cloneRoot.style.cssText = document.documentElement.style.cssText;
    const cloneBody = cloneRoot.querySelector("body");
    cloneBody.classList.remove("edit-mode-active", "drawer-open");
    cloneRoot.querySelector("title").textContent = model.metadata?.title || "Weekly Report";
    cloneRoot.querySelectorAll("[contenteditable]").forEach((node) => node.setAttribute("contenteditable", "false"));
    cloneRoot.querySelectorAll(".chart-canvas").forEach((node) => node.replaceChildren());
    cloneRoot.querySelector(".editor-drawer").setAttribute("aria-hidden", "true");
    const editButton = cloneRoot.querySelector('[data-action="toggle-edit"]');
    editButton.setAttribute("aria-pressed", "false");
    editButton.textContent = "编辑";
    const exportBuffer = cloneRoot.querySelector("[data-export-buffer]");
    exportBuffer.value = "";
    exportBuffer.textContent = "";
    cloneRoot.querySelector("#report-model").textContent = JSON.stringify(model).replaceAll("</", "<\\/");
    cloneRoot.setAttribute("data-layout", model.presentation?.layout || "newsletter");
    cloneRoot.setAttribute("data-density", model.presentation?.density || "balanced");
    return `<!doctype html>\n${cloneRoot.outerHTML}`;
  }

  function exportHtml() {
    persistNow();
    modelNode.textContent = JSON.stringify(model);
    const output = serializeReportDocument();
    document.querySelector("[data-export-buffer]").value = output;
    const blob = new Blob([output], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    const safeTitle = (model.metadata.title || "weekly-report").replace(/[\\/:*?"<>|]+/g, "-");
    anchor.href = url;
    anchor.download = `${safeTitle}.html`;
    anchor.click();
    URL.revokeObjectURL(url);
    toast("已导出当前编辑版本");
  }

  function refreshAll() {
    applyTheme();
    applyPresentation();
    syncContentBindings();
    refreshProgress();
    renderDataEditor();
    renderThemeEditor();
    renderCharts();
    updateUndoState();
  }

  function bindActions() {
    document.addEventListener("click", (event) => {
      const action = event.target.closest("[data-action]")?.dataset.action;
      if (!action) return;
      if (action === "toggle-edit") setEditMode(!document.body.classList.contains("edit-mode-active"));
      if (action === "open-data") openDrawer("data");
      if (action === "open-theme") openDrawer("theme");
      if (action === "toggle-sources") toggleSources();
      if (action === "close-drawer") closeDrawer();
      if (action === "undo") undo();
      if (action === "reset") resetReport();
      if (action === "print") window.print();
      if (action === "export") exportHtml();
    });
    document.addEventListener("click", (event) => {
      const tab = event.target.closest("[data-editor-tab]")?.dataset.editorTab;
      if (tab) switchTab(tab);
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeDrawer();
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "e") {
        event.preventDefault();
        setEditMode(!document.body.classList.contains("edit-mode-active"));
      }
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "z" && document.activeElement?.contentEditable !== "true") {
        event.preventDefault();
        undo();
      }
    });
    window.addEventListener("resize", resizeCharts, { passive: true });
  }

  function bindReportIndex() {
    const links = [...document.querySelectorAll(".report-index a")];
    if (!links.length || !("IntersectionObserver" in window)) return;
    const targets = links
      .map((link) => document.querySelector(link.getAttribute("href")))
      .filter(Boolean);
    const observer = new IntersectionObserver((entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (!visible) return;
      links.forEach((link) => {
        const active = link.getAttribute("href") === `#${visible.target.id}`;
        link.classList.toggle("active", active);
        if (active) link.setAttribute("aria-current", "location");
        else link.removeAttribute("aria-current");
      });
    }, { rootMargin: "-18% 0px -68% 0px", threshold: [0, 0.1, 0.5] });
    targets.forEach((target) => observer.observe(target));
  }

  applyTheme();
  bindEditableContent();
  bindActions();
  renderDataEditor();
  renderThemeEditor();
  bindDataEditor();
  bindThemeEditor();
  renderCharts();
  updateUndoState();
  syncSourceToggle();
  bindReportIndex();
  modelNode.textContent = JSON.stringify(model);
  window.WeeklyVizRuntime = Object.freeze({
    serialize: serializeReportDocument,
    snapshot: () => clone(model),
  });
})();
