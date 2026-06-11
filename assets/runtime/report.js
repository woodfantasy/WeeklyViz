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
    const design = model.template_design || {};
    const typography = design.typography || {};
    const geometry = design.geometry || {};
    const hero = design.hero || {};
    const chart = design.chart || {};
    const designVariables = {
      "--font-display": typography.display,
      "--font-body": typography.body,
      "--font-numeric": typography.numeric,
      "--font-label": typography.label,
      "--radius-lg": geometry.radius_lg,
      "--radius-md": geometry.radius_md,
      "--radius-sm": geometry.radius_sm,
      "--border-width": geometry.border_width,
      "--card-shadow": geometry.card_shadow,
      "--page-shadow": geometry.page_shadow,
    };
    Object.entries(designVariables).forEach(([name, value]) => {
      if (typeof value === "string" && value.trim()) root.style.setProperty(name, value);
    });
    root.setAttribute("data-card-shape", geometry.card_shape || "rounded");
    root.setAttribute("data-section-style", geometry.section_style || "rule");
    root.setAttribute("data-hero-style", hero.style || "slab");
    root.setAttribute("data-chart-style", chart.style || "balanced");
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
    if (model.metadata?.scope) {
      root.setAttribute("data-scope", model.metadata.scope);
    } else {
      root.removeAttribute("data-scope");
    }
    initOperatingReview();
    window.setTimeout(resizeCharts, 50);
  }

  function initOperatingReview() {
    const layout = model.presentation?.layout || "newsletter";
    if (layout !== "operating-review") {
      document.querySelectorAll(".toggle-chart-data-btn").forEach(b => b.remove());
      document.querySelectorAll(".chart-raw-table-wrap").forEach(t => t.remove());
      return;
    }

    // 1. Setup Tab Switching Click Listeners (Scrolling Jump Links)
    const tabBtns = document.querySelectorAll(".operating-review-tabs .tab-btn");
    tabBtns.forEach(btn => {
      btn.onclick = () => {
        const tab = btn.dataset.tab;
        let target = null;
        if (tab === "summary") target = document.getElementById("summary-section");
        else if (tab === "kpis") target = document.getElementById("kpis");
        else if (tab === "metrics") target = document.getElementById("metrics-section");
        else if (tab === "progress") target = document.getElementById("progress");
        else if (tab === "charts") target = document.getElementById("charts");
        else if (tab === "okrs") target = document.getElementById("okrs-section");
        else if (tab === "sections") target = document.querySelector("[id^='work-']");
        else if (tab === "requirements") target = document.getElementById("requirements-section");
        else if (tab === "risks") target = document.getElementById("risks");
        else if (tab === "next_actions") target = document.getElementById("next_actions");
        else if (tab === "sources") target = document.querySelector(".source-section");

        if (target) {
          const topOffset = target.getBoundingClientRect().top + window.pageYOffset - 140; // Subtract sticky nav height
          window.scrollTo({ top: topOffset, behavior: "smooth" });
          tabBtns.forEach(b => b.classList.toggle("active", b === btn));
        }
      };
    });

    // 2. Highlight tabs on scroll
    if ("IntersectionObserver" in window) {
      const observerLinks = [
        { tab: "summary", el: document.getElementById("summary-section") },
        { tab: "kpis", el: document.getElementById("kpis") },
        { tab: "metrics", el: document.getElementById("metrics-section") },
        { tab: "progress", el: document.getElementById("progress") },
        { tab: "charts", el: document.getElementById("charts") },
        { tab: "okrs", el: document.getElementById("okrs-section") },
        { tab: "sections", el: document.querySelector("[id^='work-']") },
        { tab: "requirements", el: document.getElementById("requirements-section") },
        { tab: "risks", el: document.getElementById("risks") },
        { tab: "next_actions", el: document.getElementById("next_actions") },
        { tab: "sources", el: document.querySelector(".source-section") }
      ].filter(item => item.el);

      const observer = new IntersectionObserver((entries) => {
        const visible = entries
          .filter(e => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (!visible) return;
        const matchingLink = observerLinks.find(item => item.el === visible.target);
        if (matchingLink) {
          tabBtns.forEach(btn => btn.classList.toggle("active", btn.dataset.tab === matchingLink.tab));
        }
      }, { rootMargin: "-120px 0px -60% 0px", threshold: [0, 0.1, 0.5] });

      observerLinks.forEach(item => observer.observe(item.el));
    }

    // 3. OKR collapse/expand toggles
    const okrHeaders = document.querySelectorAll(".okr-tree .okr-node-header");
    okrHeaders.forEach(header => {
      header.onclick = (e) => {
        if (e.target.closest('[contenteditable="true"]')) return;
        const parent = header.parentElement;
        if (parent.classList.contains("okr-objective") || parent.classList.contains("okr-kr") || parent.classList.contains("okr-plan")) {
          parent.classList.toggle("collapsed");
        }
      };
    });

    // 4. Requirements View Toggles (Table vs Kanban)
    const viewToggles = document.querySelectorAll(".view-toggles .toggle-btn");
    const viewContainers = document.querySelectorAll(".req-view-container");
    viewToggles.forEach(btn => {
      btn.onclick = () => {
        const targetView = btn.dataset.view;
        viewToggles.forEach(b => b.classList.toggle("active", b === btn));
        viewContainers.forEach(container => {
          if (container.dataset.viewTarget === targetView) {
            container.style.display = targetView === "table" ? "block" : "grid";
            container.classList.add("active");
          } else {
            container.style.display = "none";
            container.classList.remove("active");
          }
        });
      };
    });

    // 4. Populate Requirements Owner filter
    const ownerFilter = document.getElementById("req-owner-filter");
    const priFilter = document.getElementById("req-pri-filter");
    if (ownerFilter) {
      const rows = document.querySelectorAll(".req-table tbody tr");
      const owners = new Set();
      rows.forEach(row => {
        const owner = row.dataset.owner;
        if (owner && owner !== "-") owners.add(owner);
      });
      ownerFilter.innerHTML = '<option value="all">全部</option>';
      Array.from(owners).sort().forEach(owner => {
        const opt = document.createElement("option");
        opt.value = owner;
        opt.textContent = owner;
        ownerFilter.appendChild(opt);
      });

      const applyFilters = () => {
        const selOwner = ownerFilter.value;
        const selPri = priFilter.value;

        rows.forEach(row => {
          const matchOwner = (selOwner === "all" || row.dataset.owner === selOwner);
          const matchPri = (selPri === "all" || row.dataset.pri === selPri);
          row.style.display = (matchOwner && matchPri) ? "" : "none";
        });

        const columns = document.querySelectorAll(".kanban-column");
        columns.forEach(col => {
          const cards = col.querySelectorAll(".kanban-card");
          let visibleCount = 0;
          cards.forEach(card => {
            const cardFooterText = card.querySelector(".card-footer")?.textContent || "";
            const matchOwner = (selOwner === "all" || cardFooterText.includes(selOwner));
            const matchPri = (selPri === "all" || card.dataset.pri === selPri);
            if (matchOwner && matchPri) {
              card.style.display = "";
              visibleCount++;
            } else {
              card.style.display = "none";
            }
          });
          const countBadge = col.querySelector(".column-count");
          if (countBadge) countBadge.textContent = visibleCount;
          const emptyState = col.querySelector(".column-empty");
          if (emptyState) emptyState.style.display = visibleCount === 0 ? "block" : "none";
        });
      };

      ownerFilter.onchange = applyFilters;
      priFilter.onchange = applyFilters;
    }

    // 5. Metric card click down-drill
    const metricCards = document.querySelectorAll(".metric-card");
    metricCards.forEach(card => {
      card.style.cursor = "pointer";
      card.onclick = (e) => {
        if (e.target.closest('[contenteditable="true"]') || e.target.closest('a') || e.target.closest('button')) return;
        const mId = card.dataset.metricId;
        const chartsTab = document.querySelector('.operating-review-tabs .tab-btn[data-tab="charts"]');
        if (chartsTab) {
          chartsTab.click();
          const targetChart = document.querySelector(`[data-chart-card="${mId}"]`) || document.querySelector(`#charts`);
          if (targetChart) {
            window.setTimeout(() => {
              targetChart.scrollIntoView({ behavior: "smooth", block: "center" });
            }, 100);
          }
        }
      };
    });

    // 6. Chart to Raw Data Table toggle button
    const chartCards = document.querySelectorAll(".chart-card");
    chartCards.forEach(card => {
      const header = card.querySelector(".chart-header");
      if (!header || card.querySelector(".toggle-chart-data-btn")) return;
      
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "toggle-chart-data-btn";
      btn.textContent = "显示数据";
      header.appendChild(btn);

      const canvas = card.querySelector(".chart-canvas");
      const chartId = canvas ? canvas.dataset.chartId : null;
      let rawTableWrap = null;

      btn.onclick = () => {
        const isDataVisible = card.classList.toggle("show-raw-data");
        btn.textContent = isDataVisible ? "显示图表" : "显示数据";
        if (isDataVisible) {
          if (canvas) canvas.style.display = "none";
          if (!rawTableWrap && chartId && model.charts) {
            const chartData = model.charts.find(c => c.id === chartId);
            if (chartData) {
              rawTableWrap = document.createElement("div");
              rawTableWrap.className = "chart-raw-table-wrap";
              rawTableWrap.innerHTML = buildRawDataTable(chartData);
              canvas.parentNode.insertBefore(rawTableWrap, canvas.nextSibling);
            }
          }
          if (rawTableWrap) rawTableWrap.style.display = "block";
        } else {
          if (canvas) {
            canvas.style.display = "block";
            resizeCharts();
          }
          if (rawTableWrap) rawTableWrap.style.display = "none";
        }
      };
    });
  }

  function buildRawDataTable(chartData) {
    const labels = chartData.labels || [];
    const series = chartData.series || [];
    if (!labels.length || !series.length) return '<div class="column-empty">无原始数据</div>';

    let html = '<table class="chart-raw-table"><thead><tr><th>日期 / 类别</th>';
    series.forEach(s => {
      html += `<th>${escapeHtml(s.name)}</th>`;
    });
    html += '</tr></thead><tbody>';

    labels.forEach((label, i) => {
      html += `<tr><td><strong>${escapeHtml(label)}</strong></td>`;
      series.forEach(s => {
        const val = s.values[i] !== undefined ? s.values[i] : "-";
        html += `<td>${val}</td>`;
      });
      html += '</tr>';
    });
    html += '</tbody></table>';
    return html;
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
    const configured = model.template_design?.chart?.palette;
    const supplemental = Array.isArray(configured)
      ? configured.filter((value) => /^#[0-9a-f]{6}$/i.test(value))
      : [];
    return [
      cssColor("--primary"),
      cssColor("--accent"),
      ...supplemental,
      cssColor("--success"),
      cssColor("--warning"),
      "#3B82F6",
      "#D65A8A",
    ].filter((value, index, values) => value && values.indexOf(value) === index).slice(0, 8);
  }

  function chartLanguage() {
    const configured = model.template_design?.chart || {};
    const gridTypes = { none: "solid", solid: "solid", dashed: "dashed", dotted: "dotted" };
    const symbols = new Set(["circle", "rect", "roundRect", "triangle", "diamond", "pin", "arrow", "none"]);
    const donut = Array.isArray(configured.donut) && configured.donut.length === 2
      ? configured.donut
      : ["48%", "72%"];
    return {
      style: configured.style || "balanced",
      grid: configured.grid || "dashed",
      gridType: gridTypes[configured.grid] || "dashed",
      smooth: configured.smooth !== false,
      symbol: symbols.has(configured.symbol) ? configured.symbol : "circle",
      lineWidth: Number(configured.line_width) || 3,
      symbolSize: Number(configured.symbol_size) || 7,
      barRadius: Math.max(0, Number(configured.bar_radius) || 0),
      areaOpacity: Math.max(0, Math.min(0.5, Number(configured.area_opacity) || 0.12)),
      donut,
      legend: configured.legend === "bottom" ? "bottom" : "top",
    };
  }

  function commonChartOption(chart) {
    const muted = cssColor("--muted");
    const border = cssColor("--border");
    const language = chartLanguage();
    const legendAtBottom = language.legend === "bottom";
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
        top: legendAtBottom ? undefined : 3,
        bottom: legendAtBottom ? 0 : undefined,
        right: 0,
        textStyle: { color: muted, fontSize: 10 },
        itemWidth: 12,
        itemHeight: 7,
      },
      grid: { left: 52, right: 18, top: 52, bottom: legendAtBottom ? 58 : 42, containLabel: true },
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
        splitLine: {
          show: language.grid !== "none",
          lineStyle: { color: border, type: language.gridType },
        },
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
    const language = chartLanguage();
    if (chart.type === "donut" || chart.type === "pie") {
      return {
        ...common,
        tooltip: { ...common.tooltip, trigger: "item" },
        legend: { ...common.legend, orient: "vertical", top: "middle", right: 0 },
        series: [{
          name: chart.series[0].name,
          type: "pie",
          radius: chart.type === "donut" ? language.donut : language.donut[1],
          center: ["42%", "54%"],
          avoidLabelOverlap: true,
          itemStyle: {
            borderColor: cssColor("--surface"),
            borderWidth: language.style === "minimal" ? 1 : 3,
            borderRadius: language.barRadius,
          },
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
          itemStyle: {
            borderColor: cssColor("--surface"),
            borderWidth: 2,
            borderRadius: language.barRadius,
          },
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
          symbol: language.symbol === "none" ? "circle" : language.symbol,
          symbolSize: Math.max(9, language.symbolSize + 4),
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
        smooth: seriesType === "line" && language.smooth,
        symbol: language.symbol,
        showSymbol: language.symbol !== "none",
        symbolSize: language.symbolSize,
        stack: chart.type === "stacked-bar" ? "total" : undefined,
        areaStyle: chart.type === "area"
          ? { opacity: index === 0 ? language.areaOpacity : language.areaOpacity * 0.55 }
          : undefined,
        lineStyle: seriesType === "line" ? { width: language.lineWidth } : undefined,
        itemStyle: seriesType === "bar"
          ? {
              borderRadius: horizontal
                ? [0, language.barRadius, language.barRadius, 0]
                : [language.barRadius, language.barRadius, 0, 0],
            }
          : undefined,
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

  function bindSpotlight() {
    const selector = ".kpi-card, .metric-card, .okr-objective, .okr-kr, .okr-plan, .okr-requirement, .requirement-card, .action-card, .summary-band, .work-card, .work-item, .kanban-card";
    const body = document.body;

    document.addEventListener("mouseover", (event) => {
      const card = event.target.closest(selector);
      if (!card) return;
      body.classList.add("spotlight-active");
      card.classList.add("spotlight-focused");
    });

    document.addEventListener("mouseout", (event) => {
      const card = event.target.closest(selector);
      if (!card) return;
      const related = event.relatedTarget;
      if (related && card.contains(related)) return;
      body.classList.remove("spotlight-active");
      card.classList.remove("spotlight-focused");
    });
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
  initOperatingReview();
  bindSpotlight();
  modelNode.textContent = JSON.stringify(model);
  window.WeeklyVizRuntime = Object.freeze({
    serialize: serializeReportDocument,
    snapshot: () => clone(model),
    chartLanguage: () => clone(chartLanguage()),
  });
})();
