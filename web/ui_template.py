"""Self-contained, 100% offline OEM Daily Web Analytics UI (`pt-BR` & `en`)."""


def render_index_html(initial_lang: str = "pt-BR") -> bytes:
    html = _HTML_TEMPLATE.replace("__INITIAL_LANG__", initial_lang)
    return html.encode("utf-8")


_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Daily Cockpit — Web Analytics</title>
<style>
  :root {
    --bg: #0b1017;
    --card: #111824;
    --card-dark: #0d131d;
    --border: #1e293b;
    --badge-bg: #162032;
    --badge-bd: #28364d;
    --txt-main: #f8fafc;
    --txt-sub: #94a3b8;
    --txt-muted: #64748b;
    --sky: #38bdf8;
    --teal: #2dd4bf;
    --green: #22c55e;
    --amber: #f59e0b;
    --danger: #ef4444;
    --purple: #a78bfa;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: radial-gradient(circle at 50% 0%, rgba(56, 189, 248, 0.10), transparent 46%), var(--bg);
    color: var(--txt-main);
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;
    min-height: 100vh;
    line-height: 1.45;
  }
  .mono {
    font-family: Consolas, "DejaVu Sans Mono", "Liberation Mono", ui-monospace, monospace;
  }
  header {
    position: sticky;
    top: 0;
    z-index: 30;
    background: rgba(11, 16, 23, 0.88);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid var(--border);
    padding: 12px 20px;
  }
  .hdr-inner {
    max-width: 1280px;
    margin: 0 auto;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    flex-wrap: wrap;
  }
  .brand {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: var(--green);
    box-shadow: 0 0 10px rgba(34, 197, 94, 0.7);
  }
  .brand-title {
    font-size: 14px;
    font-weight: 800;
    letter-spacing: 0.08em;
    color: var(--sky);
    text-transform: uppercase;
  }
  .brand-sub {
    font-size: 12px;
    color: var(--txt-sub);
    padding: 2px 8px;
    border-radius: 999px;
    background: var(--badge-bg);
    border: 1px solid var(--badge-bd);
  }
  .hdr-actions {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }
  button, .btn-link {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: var(--badge-bg);
    color: var(--txt-main);
    border: 1px solid var(--badge-bd);
    border-radius: 8px;
    padding: 7px 12px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    text-decoration: none;
    transition: all 0.15s ease;
  }
  button:hover, .btn-link:hover {
    border-color: var(--sky);
    color: var(--sky);
  }
  .btn-primary {
    background: rgba(56, 189, 248, 0.14);
    border-color: rgba(56, 189, 248, 0.45);
    color: var(--sky);
  }
  .btn-primary:hover {
    background: rgba(56, 189, 248, 0.24);
    color: #fff;
  }
  .btn-teal {
    background: rgba(45, 212, 191, 0.13);
    border-color: rgba(45, 212, 191, 0.45);
    color: var(--teal);
  }
  .btn-teal:hover {
    background: rgba(45, 212, 191, 0.24);
    color: #fff;
  }
  main {
    max-width: 1280px;
    margin: 0 auto;
    padding: 18px 20px 42px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  .toolbar-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 14px 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .toolbar-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    flex-wrap: wrap;
  }
  .slice-controls {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }
  select {
    background: var(--card-dark);
    color: var(--txt-main);
    border: 1px solid var(--badge-bd);
    border-radius: 8px;
    padding: 7px 11px;
    font-size: 13px;
    font-weight: 600;
    outline: none;
  }
  select:focus {
    border-color: var(--sky);
  }
  .export-group {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }
  .day-pills {
    display: flex;
    gap: 8px;
    overflow-x: auto;
    padding-bottom: 4px;
  }
  .day-pill {
    flex: 0 0 auto;
    background: var(--card-dark);
    border: 1px solid var(--border);
    border-radius: 9px;
    padding: 8px 12px;
    cursor: pointer;
    text-align: left;
    transition: all 0.14s ease;
  }
  .day-pill:hover {
    border-color: var(--badge-bd);
  }
  .day-pill.active {
    background: rgba(56, 189, 248, 0.12);
    border-color: var(--sky);
  }
  .day-pill .d-date {
    font-size: 13px;
    font-weight: 700;
    color: var(--txt-main);
  }
  .day-pill.active .d-date {
    color: var(--sky);
  }
  .day-pill .d-meta {
    font-size: 11px;
    color: var(--txt-muted);
    margin-top: 2px;
  }
  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(215px, 1fr));
    gap: 12px;
  }
  .kpi-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 11px;
    padding: 13px 15px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .kpi-lbl {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.06em;
    color: var(--txt-muted);
    text-transform: uppercase;
  }
  .kpi-val {
    font-size: 24px;
    font-weight: 800;
    color: var(--txt-main);
  }
  .kpi-sub {
    font-size: 12px;
    color: var(--txt-sub);
  }
  .chart-card, .table-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px;
  }
  .section-hdr {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    flex-wrap: wrap;
    margin-bottom: 12px;
  }
  .section-title {
    font-size: 14px;
    font-weight: 700;
    color: var(--txt-main);
    letter-spacing: 0.03em;
  }
  .tab-bar {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }
  .tab-btn.active {
    background: var(--sky);
    border-color: var(--sky);
    color: #06101a;
    font-weight: 700;
  }
  .chart-wrap {
    position: relative;
    width: 100%;
    height: 320px;
    background: var(--card-dark);
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
  }
  canvas {
    width: 100%;
    height: 100%;
    display: block;
  }
  .chart-legend {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    margin-top: 10px;
    font-size: 12px;
    color: var(--txt-sub);
  }
  .leg-item {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
  .leg-swatch {
    width: 12px;
    height: 4px;
    border-radius: 2px;
  }
  .tooltip {
    position: absolute;
    pointer-events: none;
    background: rgba(11, 16, 23, 0.94);
    border: 1px solid var(--badge-bd);
    border-radius: 8px;
    padding: 8px 10px;
    font-size: 12px;
    color: var(--txt-main);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45);
    display: none;
    z-index: 10;
    min-width: 155px;
  }
  .table-scroll {
    overflow-x: auto;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }
  th, td {
    padding: 10px 10px;
    text-align: left;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
  }
  th {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--txt-muted);
    background: var(--card-dark);
  }
  tr:hover td {
    background: rgba(255, 255, 255, 0.02);
  }
  tr.active-row td {
    background: rgba(56, 189, 248, 0.09);
  }
  .empty-state {
    text-align: center;
    padding: 48px 20px;
    color: var(--txt-sub);
  }
  .txt-sky { color: var(--sky); }
  .txt-teal { color: var(--teal); }
  .txt-amber { color: var(--amber); }
  .txt-danger { color: var(--danger); }
</style>
</head>
<body>
  <header>
    <div class="hdr-inner">
      <div class="brand">
        <span class="dot"></span>
        <span class="brand-title" id="ui-brand">PAINEL DIÁRIO · WEB ANALYTICS</span>
        <span class="brand-sub mono" id="ui-overview-badge">--</span>
      </div>
      <div class="hdr-actions">
        <button id="btn-refresh" onclick="reloadAll()">↻ <span id="lbl-refresh">Atualizar</span></button>
        <a class="btn-link" href="/api/export/all.zip" id="btn-all-zip">⬇ <span id="lbl-all-zip">Backup Completo (.zip)</span></a>
        <button id="btn-lang" onclick="toggleLang()" class="mono">PT-BR / EN</button>
      </div>
    </div>
  </header>

  <main>
    <section class="toolbar-card">
      <div class="toolbar-top">
        <div class="slice-controls">
          <button onclick="stepDay(1)" id="btn-prev-day" title="Older">&lt;</button>
          <select id="sel-date" class="mono" onchange="onDateChange(this.value)"></select>
          <button onclick="stepDay(-1)" id="btn-next-day" title="Newer">&gt;</button>
          <select id="sel-session" onchange="onSessionChange(this.value)"></select>
        </div>
        <div class="export-group">
          <a class="btn-link btn-primary" id="dl-daily-csv" href="#">⬇ <span id="lbl-dl-csv">CSV do Dia (.csv)</span></a>
          <a class="btn-link btn-teal" id="dl-daily-zip" href="#">⬇ <span id="lbl-dl-zip">Pacote do Dia (.zip)</span></a>
          <a class="btn-link" id="dl-daily-json" href="#">⬇ <span id="lbl-dl-json">Relatório (.json)</span></a>
        </div>
      </div>
      <div class="day-pills" id="day-pills"></div>
    </section>

    <div id="empty-box" class="toolbar-card empty-state" style="display:none;">
      <h3 id="lbl-empty-title" style="color:var(--txt-main); margin-bottom:6px;">Nenhum dado coletado ainda</h3>
      <p id="lbl-empty-sub">Assim que o carro gravar sessões em logs/session_*.csv, os slices diários aparecerão aqui.</p>
    </div>

    <div id="dashboard-content">
      <section class="kpi-grid" id="kpi-grid"></section>

      <section class="chart-card" style="margin-top:16px;">
        <div class="section-hdr">
          <div class="section-title" id="lbl-chart-title">Série Temporal do Slice Diário</div>
          <div class="tab-bar">
            <button class="tab-btn active" id="tab-dyn" onclick="setChartMode('dyn')"></button>
            <button class="tab-btn" id="tab-therm" onclick="setChartMode('therm')"></button>
            <button class="tab-btn" id="tab-elec" onclick="setChartMode('elec')"></button>
          </div>
        </div>
        <div class="chart-wrap" id="chart-wrap">
          <canvas id="telemetry-canvas"></canvas>
          <div class="tooltip mono" id="chart-tooltip"></div>
        </div>
        <div class="chart-legend" id="chart-legend"></div>
      </section>

      <section class="table-card" style="margin-top:16px;">
        <div class="section-hdr">
          <div class="section-title" id="lbl-sessions-title">Sessões Gravadas no Dia</div>
          <button id="btn-clear-filter" onclick="onSessionChange('')" style="display:none;"></button>
        </div>
        <div class="table-scroll">
          <table>
            <thead>
              <tr id="sessions-thead"></tr>
            </thead>
            <tbody id="sessions-tbody"></tbody>
          </table>
        </div>
      </section>
    </div>
  </main>

<script>
const I18N = {
  "pt-BR": {
    brand: "PAINEL DIÁRIO · WEB ANALYTICS",
    refresh: "Atualizar",
    allZip: "Backup Completo (.zip)",
    dlCsv: "CSV do Dia (.csv)",
    dlZip: "Pacote do Dia (.zip)",
    dlJson: "Relatório (.json)",
    allSessions: "Todas as sessões do dia",
    emptyTitle: "Nenhum dado coletado ainda",
    emptySub: "Conecte ao carro com Gravação de Dados ativa para gerar arquivos em logs/session_*.csv.",
    chartTitle: "Telemetria do Slice Diário",
    tabDyn: "Velocidade & RPM",
    tabTherm: "Temperaturas (°C)",
    tabElec: "Bateria, TPS & Consumo",
    sessionsTitle: "Sessões / Viagens deste Dia",
    showFullDay: "Ver Dia Inteiro",
    overviewBadge: "{days} dias · {sessions} sessões · {mb} MB",
    pillSub: "{n} sess. · {km} km",
    kpiDist: "DISTÂNCIA NO DIA",
    kpiDistSub: "Motor ligado: {t}",
    kpiSpeed: "VELOCIDADE MÁX.",
    kpiSpeedSub: "Média em mov.: {avg} km/h",
    kpiRpm: "ROTAÇÃO MÁXIMA",
    kpiRpmSub: "Média: {avg} rpm · Redline: {rl}s",
    kpiWater: "ÁGUA (ARREFEC.)",
    kpiWaterSub: "Média: {avg}°C · Alerta: {w}s",
    kpiOil: "TEMP. DO ÓLEO",
    kpiOilSub: "Média: {avg}°C · Adm máx: {iat}°C",
    kpiVolt: "TENSÃO BATERIA",
    kpiVoltSub: "Mín: {min}V · Máx: {max}V",
    kpiEcon: "CONSUMO / CARGA",
    kpiEconSub: "TPS máx: {tps}% · Carga: {lod}%",
    kpiSamples: "AMOSTRAS DO SLICE",
    kpiSamplesSub: "Janela: {s} até {e}",
    thFile: "Arquivo da Sessão",
    thWindow: "Horário",
    thDur: "Duração",
    thDist: "Distância",
    thMaxSpd: "Vel. Máx",
    thMaxRpm: "RPM Máx",
    thMaxWat: "Água Máx",
    thSize: "Tamanho",
    thActions: "Ações",
    btnFilter: "Filtrar Gráfico",
    btnFiltering: "Selecionada",
    btnDownload: "Baixar .csv",
    lgSpeed: "Velocidade (km/h)",
    lgRpm: "Rotação (RPM)",
    lgWater: "Água (°C)",
    lgOil: "Óleo (°C)",
    lgIntake: "Admissão (°C)",
    lgWarn: "Alerta Térmico",
    lgVolt: "Bateria (V)",
    lgTps: "TPS (%)",
    lgLoad: "Carga (%)",
    lgKml: "Consumo (km/l)"
  },
  "en": {
    brand: "DAILY COCKPIT · WEB ANALYTICS",
    refresh: "Refresh",
    allZip: "Full Backup (.zip)",
    dlCsv: "Daily Slice (.csv)",
    dlZip: "Daily Bundle (.zip)",
    dlJson: "JSON Report (.json)",
    allSessions: "All sessions of the day",
    emptyTitle: "No telemetry logs recorded yet",
    emptySub: "Drive with CSV Data Logging enabled to record logs/session_*.csv files.",
    chartTitle: "Daily Slice Telemetry Series",
    tabDyn: "Speed & RPM",
    tabTherm: "Temperatures (°C)",
    tabElec: "Battery, TPS & Economy",
    sessionsTitle: "Recorded Sessions on This Day",
    showFullDay: "Show Full Day",
    overviewBadge: "{days} days · {sessions} sessions · {mb} MB",
    pillSub: "{n} sess. · {km} km",
    kpiDist: "DAILY DISTANCE",
    kpiDistSub: "Engine-on: {t}",
    kpiSpeed: "PEAK SPEED",
    kpiSpeedSub: "Moving avg: {avg} km/h",
    kpiRpm: "PEAK ENGINE RPM",
    kpiRpmSub: "Avg: {avg} rpm · Redline: {rl}s",
    kpiWater: "COOLANT TEMP",
    kpiWaterSub: "Avg: {avg}°C · Warning: {w}s",
    kpiOil: "ENGINE OIL TEMP",
    kpiOilSub: "Avg: {avg}°C · Max IAT: {iat}°C",
    kpiVolt: "BATTERY VOLTAGE",
    kpiVoltSub: "Min: {min}V · Max: {max}V",
    kpiEcon: "ECONOMY / LOAD",
    kpiEconSub: "Max TPS: {tps}% · Load: {lod}%",
    kpiSamples: "SLICE SAMPLES",
    kpiSamplesSub: "Window: {s} to {e}",
    thFile: "Session File",
    thWindow: "Time Window",
    thDur: "Duration",
    thDist: "Distance",
    thMaxSpd: "Max Speed",
    thMaxRpm: "Max RPM",
    thMaxWat: "Max Coolant",
    thSize: "Size",
    thActions: "Actions",
    btnFilter: "Filter Chart",
    btnFiltering: "Selected",
    btnDownload: "Download .csv",
    lgSpeed: "Speed (km/h)",
    lgRpm: "Engine RPM",
    lgWater: "Coolant (°C)",
    lgOil: "Oil (°C)",
    lgIntake: "Intake IAT (°C)",
    lgWarn: "Thermal Warning",
    lgVolt: "Battery (V)",
    lgTps: "Throttle TPS (%)",
    lgLoad: "Engine Load (%)",
    lgKml: "Economy (km/L)"
  }
};

let state = {
  lang: "__INITIAL_LANG__" === "en" ? "en" : "pt-BR",
  days: [],
  overview: null,
  selectedDate: "",
  sessionFilter: "",
  sliceData: null,
  chartMode: "dyn",
  hoverIdx: -1
};

function tr(key, vars = {}) {
  const dict = I18N[state.lang] || I18N["pt-BR"];
  let s = dict[key] || key;
  for (const [k, v] of Object.entries(vars)) {
    s = s.replace(`{${k}}`, v);
  }
  return s;
}

function fmtDuration(sec) {
  const s = Math.max(0, Math.round(sec || 0));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const r = s % 60;
  if (h > 0) return `${h}h ${String(m).padStart(2,"0")}m ${String(r).padStart(2,"0")}s`;
  return `${m}m ${String(r).padStart(2,"0")}s`;
}

function fmtBytes(b) {
  if (!b) return "0 KB";
  if (b >= 1048576) return (b / 1048576).toFixed(2) + " MB";
  return Math.max(1, Math.round(b / 1024)) + " KB";
}

function toggleLang() {
  state.lang = state.lang === "pt-BR" ? "en" : "pt-BR";
  renderStaticLabels();
  renderDaySelector();
  renderSlice();
}

function renderStaticLabels() {
  document.getElementById("ui-brand").textContent = tr("brand");
  document.getElementById("lbl-refresh").textContent = tr("refresh");
  document.getElementById("lbl-all-zip").textContent = tr("allZip");
  document.getElementById("lbl-dl-csv").textContent = tr("dlCsv");
  document.getElementById("lbl-dl-zip").textContent = tr("dlZip");
  document.getElementById("lbl-dl-json").textContent = tr("dlJson");
  document.getElementById("lbl-empty-title").textContent = tr("emptyTitle");
  document.getElementById("lbl-empty-sub").textContent = tr("emptySub");
  document.getElementById("lbl-chart-title").textContent = tr("chartTitle");
  document.getElementById("tab-dyn").textContent = tr("tabDyn");
  document.getElementById("tab-therm").textContent = tr("tabTherm");
  document.getElementById("tab-elec").textContent = tr("tabElec");
  document.getElementById("lbl-sessions-title").textContent = tr("sessionsTitle");
  document.getElementById("btn-clear-filter").textContent = tr("showFullDay");

  if (state.overview) {
    const mb = (state.overview.total_bytes / 1048576).toFixed(2);
    document.getElementById("ui-overview-badge").textContent = tr("overviewBadge", {
      days: state.overview.days_count,
      sessions: state.overview.sessions_count,
      mb: mb
    });
  }
}

async function reloadAll() {
  const res = await fetch("/api/days");
  const data = await res.json();
  state.days = data.days || [];
  state.overview = data.overview || null;
  renderStaticLabels();

  if (state.days.length === 0) {
    document.getElementById("empty-box").style.display = "block";
    document.getElementById("dashboard-content").style.display = "none";
    document.getElementById("day-pills").innerHTML = "";
    document.getElementById("sel-date").innerHTML = "";
    return;
  }

  document.getElementById("empty-box").style.display = "none";
  document.getElementById("dashboard-content").style.display = "block";

  if (!state.selectedDate || !state.days.some(d => d.date === state.selectedDate)) {
    state.selectedDate = state.days[0].date;
    state.sessionFilter = "";
  }

  renderDaySelector();
  await loadDailySlice();
}

function renderDaySelector() {
  const sel = document.getElementById("sel-date");
  sel.innerHTML = state.days.map(d =>
    `<option value="${d.date}" ${d.date === state.selectedDate ? "selected" : ""}>${d.date} (${d.sessions_count})</option>`
  ).join("");

  const pills = document.getElementById("day-pills");
  pills.innerHTML = state.days.map(d => `
    <div class="day-pill ${d.date === state.selectedDate ? "active" : ""}" onclick="onDateChange('${d.date}')">
      <div class="d-date mono">${d.date}</div>
      <div class="d-meta">${tr("pillSub", { n: d.sessions_count, km: d.distance_km.toFixed(1) })}</div>
    </div>
  `).join("");

  const d = encodeURIComponent(state.selectedDate);
  document.getElementById("dl-daily-csv").href = `/api/export/daily/${d}.csv`;
  document.getElementById("dl-daily-zip").href = `/api/export/daily/${d}.zip`;
  document.getElementById("dl-daily-json").href = `/api/export/daily/${d}.json`;
}

async function onDateChange(newDate) {
  if (!newDate) return;
  state.selectedDate = newDate;
  state.sessionFilter = "";
  renderDaySelector();
  await loadDailySlice();
}

async function stepDay(delta) {
  const idx = state.days.findIndex(d => d.date === state.selectedDate);
  if (idx < 0) return;
  const next = idx + delta;
  if (next >= 0 && next < state.days.length) {
    await onDateChange(state.days[next].date);
  }
}

async function onSessionChange(fname) {
  state.sessionFilter = fname || "";
  await loadDailySlice();
}

async function loadDailySlice() {
  if (!state.selectedDate) return;
  let url = `/api/daily/${encodeURIComponent(state.selectedDate)}`;
  if (state.sessionFilter) {
    url += `?session=${encodeURIComponent(state.sessionFilter)}`;
  }
  const res = await fetch(url);
  state.sliceData = await res.json();
  state.hoverIdx = -1;
  renderSlice();
}

function renderSlice() {
  if (!state.sliceData) return;
  const m = state.sliceData.metrics;
  const sessions = state.sliceData.sessions || [];

  // Session dropdown
  const selSess = document.getElementById("sel-session");
  selSess.innerHTML = `<option value="">${tr("allSessions")} (${sessions.length})</option>` +
    sessions.map(s =>
      `<option value="${s.filename}" ${s.filename === state.sessionFilter ? "selected" : ""}>${s.start_time} - ${s.end_time} (${s.samples})</option>`
    ).join("");

  document.getElementById("btn-clear-filter").style.display = state.sessionFilter ? "inline-flex" : "none";

  // KPI cards
  const watCls = m.max_water_c >= 105 ? "txt-danger" : (m.max_water_c >= 95 ? "txt-amber" : "txt-teal");
  const vltCls = (m.min_voltage_v > 0 && m.min_voltage_v < 11.8) ? "txt-danger" : "txt-sky";
  const econVal = m.avg_consumption_kml > 0 ? `${m.avg_consumption_kml.toFixed(1)} km/l` : `${m.max_throttle_pct.toFixed(0)}% TPS`;

  const kpis = [
    { lbl: tr("kpiDist"), val: `${m.distance_km.toFixed(2)} km`, cls: "txt-sky", sub: tr("kpiDistSub", { t: fmtDuration(m.engine_on_s) }) },
    { lbl: tr("kpiSpeed"), val: `${m.max_speed_kmh.toFixed(0)} km/h`, cls: "", sub: tr("kpiSpeedSub", { avg: m.avg_moving_speed_kmh.toFixed(1) }) },
    { lbl: tr("kpiRpm"), val: `${Math.round(m.max_rpm)} rpm`, cls: m.redline_s > 0 ? "txt-amber" : "", sub: tr("kpiRpmSub", { avg: Math.round(m.avg_rpm), rl: m.redline_s.toFixed(0) }) },
    { lbl: tr("kpiWater"), val: m.max_water_c > 0 ? `${m.max_water_c.toFixed(1)} °C` : "-- °C", cls: watCls, sub: tr("kpiWaterSub", { avg: m.avg_water_c.toFixed(1), w: m.warn_water_s.toFixed(0) }) },
    { lbl: tr("kpiOil"), val: m.max_oil_c > 0 ? `${m.max_oil_c.toFixed(1)} °C` : "-- °C", cls: "", sub: tr("kpiOilSub", { avg: m.avg_oil_c.toFixed(1), iat: m.max_intake_c.toFixed(0) }) },
    { lbl: tr("kpiVolt"), val: m.avg_voltage_v > 0 ? `${m.avg_voltage_v.toFixed(2)} V` : "-- V", cls: vltCls, sub: tr("kpiVoltSub", { min: m.min_voltage_v.toFixed(2), max: m.max_voltage_v.toFixed(2) }) },
    { lbl: tr("kpiEcon"), val: econVal, cls: "txt-teal", sub: tr("kpiEconSub", { tps: m.max_throttle_pct.toFixed(0), lod: m.max_load_pct.toFixed(0) }) },
    { lbl: tr("kpiSamples"), val: `${m.samples}`, cls: "", sub: tr("kpiSamplesSub", { s: m.start_time, e: m.end_time }) },
  ];

  document.getElementById("kpi-grid").innerHTML = kpis.map(k => `
    <div class="kpi-card">
      <div class="kpi-lbl">${k.lbl}</div>
      <div class="kpi-val mono ${k.cls}">${k.val}</div>
      <div class="kpi-sub">${k.sub}</div>
    </div>
  `).join("");

  // Sessions table
  document.getElementById("sessions-thead").innerHTML = `
    <th>${tr("thFile")}</th>
    <th>${tr("thWindow")}</th>
    <th>${tr("thDur")}</th>
    <th>${tr("thDist")}</th>
    <th>${tr("thMaxSpd")}</th>
    <th>${tr("thMaxRpm")}</th>
    <th>${tr("thMaxWat")}</th>
    <th>${tr("thSize")}</th>
    <th>${tr("thActions")}</th>
  `;

  document.getElementById("sessions-tbody").innerHTML = sessions.map(s => {
    const isSel = s.filename === state.sessionFilter;
    return `
      <tr class="${isSel ? "active-row" : ""}">
        <td class="mono">${s.filename}</td>
        <td class="mono">${s.start_time} → ${s.end_time}</td>
        <td class="mono">${fmtDuration(s.duration_s)}</td>
        <td class="mono">${s.distance_km.toFixed(2)} km</td>
        <td class="mono">${s.max_speed_kmh.toFixed(0)} km/h</td>
        <td class="mono">${Math.round(s.max_rpm)}</td>
        <td class="mono">${s.max_water_c > 0 ? s.max_water_c.toFixed(1) + " °C" : "--"}</td>
        <td class="mono">${fmtBytes(s.size_bytes)}</td>
        <td>
          <button class="${isSel ? "btn-primary" : ""}" onclick="onSessionChange('${isSel ? "" : s.filename}')">
            ${isSel ? tr("btnFiltering") : tr("btnFilter")}
          </button>
          <a class="btn-link" href="/api/download/session/${encodeURIComponent(s.filename)}">⬇ ${tr("btnDownload")}</a>
        </td>
      </tr>
    `;
  }).join("");

  drawChart();
}

function setChartMode(mode) {
  state.chartMode = mode;
  ["dyn", "therm", "elec"].forEach(m => {
    document.getElementById(`tab-${m}`).classList.toggle("active", m === mode);
  });
  drawChart();
}

function getChannels() {
  if (state.chartMode === "therm") {
    return [
      { key: "wat", label: tr("lgWater"), color: "#38bdf8", unit: "°C", scaleMax: 130, scaleMin: 30 },
      { key: "oil", label: tr("lgOil"),   color: "#f59e0b", unit: "°C", scaleMax: 130, scaleMin: 30 },
      { key: "iat", label: tr("lgIntake"),color: "#2dd4bf", unit: "°C", scaleMax: 130, scaleMin: 0 }
    ];
  }
  if (state.chartMode === "elec") {
    return [
      { key: "vlt", label: tr("lgVolt"), color: "#38bdf8", unit: "V",    scaleMax: 16,  scaleMin: 10 },
      { key: "thr", label: tr("lgTps"),  color: "#2dd4bf", unit: "%",    scaleMax: 100, scaleMin: 0 },
      { key: "lod", label: tr("lgLoad"), color: "#a78bfa", unit: "%",    scaleMax: 100, scaleMin: 0 },
      { key: "kml", label: tr("lgKml"),  color: "#f59e0b", unit: "km/l", scaleMax: 30,  scaleMin: 0 }
    ];
  }
  return [
    { key: "spd", label: tr("lgSpeed"), color: "#38bdf8", unit: "km/h", scaleMax: 200, scaleMin: 0, fill: true },
    { key: "rpm", label: tr("lgRpm"),   color: "#2dd4bf", unit: "rpm",  scaleMax: 7000, scaleMin: 0 }
  ];
}

function drawChart() {
  const wrap = document.getElementById("chart-wrap");
  const canvas = document.getElementById("telemetry-canvas");
  const tooltip = document.getElementById("chart-tooltip");
  if (!state.sliceData) return;

  const series = state.sliceData.series || [];
  const dpr = window.devicePixelRatio || 1;
  const W = wrap.clientWidth;
  const H = wrap.clientHeight;
  canvas.width = W * dpr;
  canvas.height = H * dpr;

  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, W, H);

  const channels = getChannels();
  document.getElementById("chart-legend").innerHTML = channels.map(c => `
    <span class="leg-item"><span class="leg-swatch" style="background:${c.color}"></span>${c.label}</span>
  `).join("");

  if (series.length === 0) {
    tooltip.style.display = "none";
    return;
  }

  const padL = 48, padR = 48, padT = 18, padB = 28;
  const plotW = Math.max(10, W - padL - padR);
  const plotH = Math.max(10, H - padT - padB);

  // Horizontal grid lines
  ctx.strokeStyle = "#1e293b";
  ctx.lineWidth = 1;
  ctx.font = "11px Consolas, monospace";
  ctx.fillStyle = "#64748b";
  const primary = channels[0];
  const secondary = channels[1] || null;

  for (let i = 0; i <= 4; i++) {
    const frac = i / 4;
    const y = padT + plotH * (1 - frac);
    ctx.beginPath();
    ctx.moveTo(padL, y);
    ctx.lineTo(padL + plotW, y);
    ctx.stroke();

    const vLeft = primary.scaleMin + frac * (primary.scaleMax - primary.scaleMin);
    ctx.textAlign = "right";
    ctx.fillStyle = primary.color;
    ctx.fillText(Math.round(vLeft), padL - 8, y + 4);

    if (secondary && secondary.scaleMax !== primary.scaleMax) {
      const vRight = secondary.scaleMin + frac * (secondary.scaleMax - secondary.scaleMin);
      ctx.textAlign = "left";
      ctx.fillStyle = secondary.color;
      ctx.fillText(Math.round(vRight), padL + plotW + 8, y + 4);
    }
  }

  // Thermal reference line at 95°C
  if (state.chartMode === "therm") {
    const warnC = (state.sliceData.thresholds && state.sliceData.thresholds.temp_warn) || 95;
    const wy = padT + plotH * (1 - (warnC - 30) / (130 - 30));
    ctx.save();
    ctx.setLineDash([5, 5]);
    ctx.strokeStyle = "rgba(239, 68, 68, 0.55)";
    ctx.beginPath();
    ctx.moveTo(padL, wy);
    ctx.lineTo(padL + plotW, wy);
    ctx.stroke();
    ctx.restore();
  }

  // Time labels along X axis
  ctx.fillStyle = "#64748b";
  ctx.textAlign = "center";
  const ticks = Math.min(6, series.length);
  for (let t = 0; t < ticks; t++) {
    const idx = ticks === 1 ? 0 : Math.round((t / (ticks - 1)) * (series.length - 1));
    const x = padL + (series.length === 1 ? plotW / 2 : (idx / (series.length - 1)) * plotW);
    ctx.fillText(series[idx].t, x, H - 8);
  }

  // Session boundary markers
  ctx.save();
  ctx.setLineDash([3, 4]);
  ctx.strokeStyle = "rgba(148, 163, 184, 0.25)";
  for (let i = 1; i < series.length; i++) {
    if (series[i].s !== series[i - 1].s) {
      const sx = padL + (i / (series.length - 1)) * plotW;
      ctx.beginPath();
      ctx.moveTo(sx, padT);
      ctx.lineTo(sx, padT + plotH);
      ctx.stroke();
    }
  }
  ctx.restore();

  // Plot channels
  channels.forEach(ch => {
    const span = Math.max(1e-6, ch.scaleMax - ch.scaleMin);
    ctx.beginPath();
    series.forEach((pt, i) => {
      const x = padL + (series.length === 1 ? plotW / 2 : (i / (series.length - 1)) * plotW);
      const raw = pt[ch.key] || 0;
      const clamped = Math.max(ch.scaleMin, Math.min(ch.scaleMax, raw));
      const y = padT + plotH * (1 - (clamped - ch.scaleMin) / span);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = ch.color;
    ctx.lineWidth = 2;
    ctx.stroke();

    if (ch.fill && series.length > 1) {
      ctx.lineTo(padL + plotW, padT + plotH);
      ctx.lineTo(padL, padT + plotH);
      ctx.closePath();
      const grad = ctx.createLinearGradient(0, padT, 0, padT + plotH);
      grad.addColorStop(0, "rgba(56, 189, 248, 0.24)");
      grad.addColorStop(1, "rgba(56, 189, 248, 0.01)");
      ctx.fillStyle = grad;
      ctx.fill();
    }
  });

  // Crosshair & Tooltip
  if (state.hoverIdx >= 0 && state.hoverIdx < series.length) {
    const pt = series[state.hoverIdx];
    const hx = padL + (series.length === 1 ? plotW / 2 : (state.hoverIdx / (series.length - 1)) * plotW);
    ctx.strokeStyle = "rgba(248, 250, 252, 0.45)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(hx, padT);
    ctx.lineTo(hx, padT + plotH);
    ctx.stroke();

    const lines = [`<div style="color:#94a3b8;margin-bottom:4px;">${pt.t}</div>`];
    channels.forEach(ch => {
      const val = pt[ch.key] ?? 0;
      lines.push(`<div style="color:${ch.color};">${ch.key.toUpperCase()}: <b>${val}</b> ${ch.unit}</div>`);
    });
    tooltip.innerHTML = lines.join("");
    tooltip.style.display = "block";
    const tipLeft = hx + 14 + 170 > W ? Math.max(8, hx - 175) : hx + 14;
    tooltip.style.left = `${tipLeft}px`;
    tooltip.style.top = "18px";
  } else {
    tooltip.style.display = "none";
  }
}

(function bindChartEvents() {
  const wrap = document.getElementById("chart-wrap");
  function handleMove(clientX) {
    if (!state.sliceData || !state.sliceData.series || !state.sliceData.series.length) return;
    const rect = wrap.getBoundingClientRect();
    const padL = 48, padR = 48;
    const plotW = Math.max(10, rect.width - padL - padR);
    const rel = Math.max(0, Math.min(1, (clientX - rect.left - padL) / plotW));
    state.hoverIdx = Math.round(rel * (state.sliceData.series.length - 1));
    drawChart();
  }
  wrap.addEventListener("mousemove", e => handleMove(e.clientX));
  wrap.addEventListener("touchmove", e => {
    if (e.touches && e.touches[0]) handleMove(e.touches[0].clientX);
  }, { passive: true });
  wrap.addEventListener("mouseleave", () => {
    state.hoverIdx = -1;
    drawChart();
  });
  window.addEventListener("resize", () => drawChart());
})();

reloadAll();
</script>
</body>
</html>
"""
