import {
  esc,
  date,
  number,
  money,
  signed,
  when,
  age,
  isFresh,
  proposalStatus,
  csv,
  humanize,
} from "./core.mjs?v=2";

const $ = (id) => document.getElementById(id);
const all = (selector) => [...document.querySelectorAll(selector)];
const icons = {
  grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  chart: '<path d="M3 3v18h18M6 15l5-5 4 3 6-8"/>',
  layers: '<path d="m12 3 10 5-10 5L2 8zm-9 10 9 5 9-5M3 18l9 5 9-5"/>',
  briefcase:
    '<rect x="3" y="7" width="18" height="14" rx="2"/><path d="M8 7V4h8v3M3 12c5 4 13 4 18 0M10 13h4v4h-4z"/>',
  sparkle:
    '<path d="m12 3 2.4 6.6L21 12l-6.6 2.4L12 21l-2.4-6.6L3 12l6.6-2.4zM20 2v4m-2-2h4"/>',
  flask: '<path d="M9 3h6M10 3v6L4 19q-1 2 2 2h12q3 0 2-2L14 9V3M7 15h10"/>',
  activity: '<path d="M2 12h5l3-8 4 16 3-8h5"/>',
  shield: '<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6zM8 12l3 3 5-6"/>',
  moon: '<path d="M21 13A9 9 0 0 1 11 3a9 9 0 1 0 10 10Z"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1 1m12 12 1 1M5 19l1-1M18 6l1-1"/>',
  settings:
    '<path d="m9 3-.8 3-3 .7-1.5 2.6 2 2.7-2 2.7 1.5 2.6 3 .7.8 3h6l.8-3 3-.7 1.5-2.6-2-2.7 2-2.7-1.5-2.6-3-.7-.8-3z"/><circle cx="12" cy="12" r="3"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
  bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 8-3 8h18s-3-1-3-8M10 20h4"/>',
  refresh:
    '<path d="M20 7a9 9 0 0 0-15-1L3 9m0-6v6h6M4 17a9 9 0 0 0 15 1l2-3m0 6v-6h-6"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  wallet:
    '<rect x="3" y="5" width="18" height="15" rx="2"/><path d="M17 12h4v4h-4a2 2 0 0 1 0-4ZM3 7V4l14-2v3"/>',
  coins:
    '<ellipse cx="9" cy="6" rx="6" ry="3"/><path d="M3 6v5c0 4 12 4 12 0V6M3 11v5c0 4 12 4 12 0v-5M18 9c4 0 4 6 0 6m0 0v5"/>',
  trend: '<path d="m3 17 6-6 4 4 8-10m-6 0h6v6"/>',
  compass: '<circle cx="12" cy="12" r="9"/><path d="m16 8-3 5-5 3 3-5z"/>',
  database:
    '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 4 16 4 16 0V5M4 12c0 4 16 4 16 0"/>',
  "arrow-right": '<path d="M4 12h16m-6-6 6 6-6 6"/>',
  "arrow-up": '<path d="M12 20V4m-6 6 6-6 6 6"/>',
  download: '<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
  lock: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V6a4 4 0 0 1 8 0v4M12 14v3"/>',
  x: '<path d="m6 6 12 12M6 18 18 6"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  alert: '<path d="m12 3 10 18H2zM12 9v5m0 3v.1"/>',
  chevrons: '<path d="m9 8 3-3 3 3m-6 8 3 3 3-3"/>',
  "wifi-off":
    '<path d="m3 3 18 18M2 8a16 16 0 0 1 4-2m5-1a16 16 0 0 1 11 3M5 12a11 11 0 0 1 6-2m5 1 3 1M8 16a6 6 0 0 1 6-1m-2 5v.1"/>',
};
const icon = (name) =>
  `<span class="icon" aria-hidden="true"><svg viewBox="0 0 24 24">${icons[name] || icons.activity}</svg></span>`;
all("[data-icon]").forEach((el) => {
  el.innerHTML = icon(el.dataset.icon).replace(/^<span[^>]*>|<\/span>$/g, "");
  el.setAttribute("aria-hidden", "true");
});
const routes = {
  overview: [
    "Overview",
    "Market overview",
    "YOUR WORKSPACE, AT A GLANCE",
    "A considered view of your market, research, and paper portfolio.",
    "grid",
  ],
  market: [
    "Markets",
    "The options landscape",
    "CONTEXT BEFORE CONVICTION",
    "Explore the chain, inspect volatility, and understand your exposure.",
    "chart",
  ],
  proposals: [
    "Trade proposals",
    "The strategy desk",
    "FROM SIGNAL TO DECISION",
    "Review deterministic signals and risk controls before a paper order.",
    "layers",
  ],
  portfolio: [
    "Portfolio",
    "Your paper portfolio",
    "CAPITAL, WITH CONTEXT",
    "Track simulated positions, rule-based exits, and every fill.",
    "briefcase",
  ],
  agents: [
    "AI workspace",
    "A broader perspective",
    "FOUR SPECIALISTS. ONE WORKSPACE.",
    "Explore your research with four bounded, read-only advisory roles.",
    "sparkle",
  ],
  backtest: [
    "Backtesting",
    "Test your thinking",
    "A REPLAY, NOT A PREDICTION",
    "Examine the process across historical snapshots before taking the next step.",
    "flask",
  ],
  activity: [
    "Activity",
    "A clear record",
    "TRANSPARENCY AT EVERY STEP",
    "Follow the decisions, controls, and actions across your workspace.",
    "activity",
  ],
};
const agents = [
  [
    "market_research",
    "Market Research Agent",
    "Underlying trends and supplied market context.",
    "compass",
  ],
  [
    "options_analyst",
    "Options Analyst Agent",
    "Option chains, volatility, Greeks, and positioning.",
    "chart",
  ],
  [
    "strategy_reasoning",
    "Strategy Reasoning Agent",
    "The conditions behind deterministic proposals.",
    "layers",
  ],
  [
    "trading_assistant",
    "Trading Assistant Agent",
    "Your positions, available cash, and controls.",
    "sparkle",
  ],
];
const riskLabels = {
  paper_only: "Paper execution only",
  source_matches: "Expected data source",
  kill_switch_clear: "New entries enabled",
  proposal_valid: "Proposal has not expired",
  snapshot_fresh: "Fresh market snapshot",
  underlying_fresh: "Fresh underlying price",
  position_marks_fresh: "Existing positions have fresh marks",
  long_only: "Long options only",
  cash_available: "Sufficient available cash",
  trade_premium_limit: "Trade premium within limit",
  portfolio_premium_limit: "Total premium within limit",
  daily_loss_limit: "Daily loss within limit",
  position_count: "Position count within limit",
  no_duplicate_position: "No duplicate open instrument",
  instrument_present: "Contract present in chain",
  instrument_matches: "Correct instrument",
  quote_fresh: "Fresh option quote",
  before_expiry_cutoff: "Before expiry cutoff",
  whole_lots: "Whole lot quantity",
  tick_alignment: "Price aligned to tick size",
  spread_limit: "Bid–ask spread within limit",
  open_interest: "Positive open interest",
  displayed_depth: "Sufficient displayed quantity",
  within_limit: "Estimated fill within limit",
};
const state = {
  overview: null,
  analytics: null,
  market: null,
  timeline: [],
  proposals: [],
  positions: [],
  orders: [],
  audit: new Map(),
  notes: [],
  runs: [],
  backtests: [],
  risks: {},
  underlying: "NIFTY",
  optionType: "all",
  proposalFilter: "all",
  positionFilter: "OPEN",
  range: 120,
  selectedAgent: "trading_assistant",
  backtestId: "",
  connected: false,
  authenticated: false,
  authRequired: false,
  offset: 0,
  lastSync: null,
  olderAvailable: true,
};
let route = "overview",
  refreshFlight = null,
  review = null,
  agentQuestion = null;
const busy = new Set();
const now = () => Date.now() + state.offset;
const text = (id, value) => {
  $(id).textContent = value;
};
const html = (id, value) => {
  const el = $(id);
  if (el.dataset.rendered === value) return;
  const expanded = new Set(
    [...el.querySelectorAll("details[open]")].map((x) => x.dataset.key),
  );
  el.innerHTML = value;
  el.dataset.rendered = value;
  el.querySelectorAll("details").forEach((x) => {
    if (expanded.has(x.dataset.key)) x.open = true;
  });
};
const pill = (label, kind = "") =>
  `<span class="badge ${kind}">${esc(label)}</span>`;
const empty = (title, description, action = "") =>
  `<div class="empty-state">${icon("compass")}<strong>${esc(title)}</strong><p>${esc(description)}</p>${action}</div>`;
const definition = (rows) =>
  `<dl class="definition-list">${rows.map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join("")}</dl>`;
const currentFresh = () =>
  state.connected &&
  state.overview &&
  isFresh(state.analytics?.as_of, state.overview.max_quote_age_seconds, now());
const entryReady = () => currentFresh() && !state.overview?.kill_switch;
const filteredProposals = () =>
  state.proposals.filter(
    (p) =>
      state.proposalFilter === "all" ||
      proposalStatus(p, now()) === state.proposalFilter,
  );
function toast(message, error = false) {
  const el = document.createElement("div");
  el.className = "toast" + (error ? " error" : "");
  el.innerHTML =
    icon(error ? "alert" : "check") +
    `<span>${esc(message)}</span><button aria-label="Dismiss notification">${icon("x")}</button>`;
  el.querySelector("button").onclick = () => el.remove();
  $("toast-stack").append(el);
  setTimeout(() => el.remove(), error ? 14000 : 7000);
}
function showError(id, error) {
  text(id, error?.message || error);
  $(id).hidden = false;
}
function showModal(id) {
  closeNav();
  if (!$(id).open) $(id).showModal();
}
function sessionLost() {
  state.authenticated = false;
  state.connected = false;
  renderConnection("Sign in to continue", "Your workspace session has ended.");
  if (!$("auth-dialog").open) {
    all("dialog[open]").forEach((d) => d.close());
    showModal("auth-dialog");
  }
  updateControls();
}
async function request(path, method = "GET", body) {
  const controller = new AbortController(),
    timer = setTimeout(() => controller.abort(), 28000);
  try {
    const response = await fetch(path, {
      method,
      credentials: "same-origin",
      signal: controller.signal,
      headers: body === undefined ? {} : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const result = await response.json().catch(() => null);
    if (!response.ok) {
      if (response.status === 401 && path.startsWith("/api/")) sessionLost();
      const message =
        result?.message ||
        (result?.risk?.reasons?.length
          ? result.risk.reasons
              .map((x) => riskLabels[x] || humanize(x))
              .join("; ")
          : null) ||
        result?.details?.map((x) => x.message).join("; ") ||
        (response.status === 401
          ? "Sign in to continue."
          : response.status >= 500
            ? "The service is unavailable. Please try again shortly."
            : humanize(result?.error) ||
              `Request failed (${response.status}).`);
      const error = new Error(message);
      error.status = response.status;
      error.result = result;
      throw error;
    }
    if (result === null)
      throw new Error(
        "The service returned an unreadable response. Please refresh.",
      );
    return result;
  } catch (error) {
    if (error.name === "AbortError")
      throw new Error(
        "The request timed out. Refresh before retrying an order.",
      );
    if (error instanceof TypeError)
      throw new Error(
        "Unable to reach the workspace. Check your connection and try again.",
      );
    throw error;
  } finally {
    clearTimeout(timer);
  }
}
const api = (path, method, body) => request("/api/v1" + path, method, body);
async function run(key, fn, errorId) {
  if (busy.has(key)) return;
  busy.add(key);
  updateControls();
  if (errorId) $(errorId).hidden = true;
  try {
    return await fn();
  } catch (error) {
    if (errorId) showError(errorId, error);
    else toast(error.message, true);
  } finally {
    busy.delete(key);
    updateControls();
  }
}
async function refresh(force = false) {
  if (refreshFlight) {
    await refreshFlight;
    if (!force) return;
  }
  if (!state.authenticated) return;
  refreshFlight = (async () => {
    try {
      const optional = (path) =>
        api(path).catch((e) => {
          if (e.status === 404) return null;
          throw e;
        });
      const values = await Promise.all([
        api("/overview"),
        optional("/analytics"),
        api("/market/timeline?limit=120"),
        api("/proposals"),
        api("/positions"),
        api("/paper/orders"),
        api("/audit?newest=true&limit=100"),
        api("/notifications"),
        api("/agents/runs"),
        api("/backtests"),
        api("/risk/evaluations"),
        state.underlying === "NIFTY"
          ? Promise.resolve(null)
          : optional("/analytics?underlying=" + state.underlying),
      ]);
      const [
        overview,
        analytics,
        timeline,
        proposals,
        positions,
        orders,
        events,
        notes,
        runs,
        backtests,
        evaluations,
        market,
      ] = values;
      Object.assign(state, {
        overview,
        analytics,
        timeline,
        proposals,
        positions,
        orders,
        notes,
        runs,
        backtests,
        market: state.underlying === "NIFTY" ? analytics : market,
        connected: true,
        lastSync: new Date().toISOString(),
        offset: date(overview.server_time).getTime() - Date.now(),
      });
      events.events.forEach((e) => state.audit.set(e.id, e));
      if (state.audit.size === events.events.length)
        state.olderAvailable = events.events.length === 100;
      state.risks = {};
      evaluations.forEach((r) => {
        state.risks[r.proposal_id] ??= r.decision;
      });
      if (!backtests.some((x) => x.id === state.backtestId))
        state.backtestId = backtests[0]?.id || "";
      render();
    } catch (error) {
      state.connected = false;
      renderConnection(
        error.status === 401 ? "Sign in to continue" : "Connection interrupted",
        error.message,
      );
      updateControls();
      throw error;
    }
  })();
  try {
    await refreshFlight;
  } finally {
    refreshFlight = null;
  }
}
function renderConnection(title = "", detail = "") {
  $("connection-banner").hidden = state.connected;
  text("connection-error", title || "Connection interrupted");
  text("connection-help", detail || "Displayed values may be out of date.");
  text(
    "connection",
    state.connected
      ? "Workspace connected"
      : state.authenticated
        ? "Connection needs attention"
        : "Workspace locked",
  );
  text(
    "last-sync",
    state.lastSync
      ? "Last synced " + when(state.lastSync, false) + " IST"
      : "Waiting for connection",
  );
  ["footer-dot", "sidebar-dot"].forEach((id) =>
    $(id).classList.toggle("offline", !state.connected),
  );
  text(
    "session-label",
    state.authRequired ? "Private browser session" : "Local session",
  );
  $("sign-out").hidden = !state.authRequired;
}
function chart(rows, valueKey, timeKey, id, light = false) {
  if (!rows.length)
    return empty(
      "Your market, in view.",
      "Load a sample tick to start a recorded price series.",
    );
  const values = rows.map((r) => Number(r[valueKey])),
    times = rows.map((r) => date(r[timeKey]).getTime());
  const lo = Math.min(...values),
    hi = Math.max(...values),
    pad = Math.max((hi - lo) * 0.15, Math.abs(hi) * 0.00025, 1),
    min = lo - pad,
    max = hi + pad;
  const W = 680,
    H = 206,
    L = 65,
    R = 15,
    T = 13,
    B = 35,
    x = (i) =>
      times.at(-1) === times[0]
        ? (L + W - R) / 2
        : L + ((times[i] - times[0]) / (times.at(-1) - times[0])) * (W - L - R),
    y = (v) => T + ((max - v) / (max - min)) * (H - T - B);
  const line = values
    .map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(2)},${y(v).toFixed(2)}`)
    .join(" ");
  const stroke = light ? "var(--green)" : "#c8e6b5",
    labels = light ? "var(--muted)" : "#98b1a0",
    grid = light ? "var(--line)" : "#355044";
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${light ? "Paper equity" : "Stored NIFTY prices"} across ${rows.length} observations"><defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="${stroke}" stop-opacity=".16"/><stop offset="100%" stop-color="${stroke}" stop-opacity="0"/></linearGradient></defs>${[
    0, 0.5, 1,
  ]
    .map((t) => {
      const v = min + (max - min) * t,
        yy = y(v);
      return `<path d="M${L} ${yy}H${W - R}" stroke="${grid}" stroke-dasharray="3 5"/><text x="${L - 10}" y="${yy + 3}" text-anchor="end" fill="${labels}" font-size="10">${number(v, 0)}</text>`;
    })
    .join(
      "",
    )}${values.length > 1 ? `<path d="${line}L${x(values.length - 1)},${H - B}L${x(0)},${H - B}Z" fill="url(#${id})"/><path d="${line}" fill="none" stroke="${stroke}" stroke-width="2" stroke-linejoin="round"/>` : ""}<circle cx="${x(values.length - 1)}" cy="${y(values.at(-1))}" r="4" fill="${stroke}"/><text x="${L}" y="${H - 7}" fill="${labels}" font-size="10">${esc(when(rows[0][timeKey]))}</text><text x="${W - R}" y="${H - 7}" text-anchor="end" fill="${labels}" font-size="10">${values.length > 1 ? esc(when(rows.at(-1)[timeKey])) : "1 recorded observation"}</text></svg>`;
}
function renderOverview() {
  const o = state.overview;
  if (!o) return;
  text("equity", money(o.equity));
  text("cash", money(o.cash));
  text("pnl", money(o.unrealized_pnl));
  $("pnl").className = Number(o.unrealized_pnl) < 0 ? "negative" : "positive";
  text(
    "equity-change",
    signed((Number(o.equity) / Number(o.starting_cash) - 1) * 100) + "%",
  );
  $("equity-change").className =
    Number(o.total_pnl) < 0 ? "negative" : "positive";
  text(
    "cash-percent",
    number(
      Number(o.equity) > 0 ? (Number(o.cash) / Number(o.equity)) * 100 : 0,
      1,
    ) + "%",
  );
  text(
    "position-count",
    o.open_positions + " open position" + (o.open_positions === 1 ? "" : "s"),
  );
  text("risk-status", o.kill_switch ? "Entries paused" : "Controls active");
  text("risk-caption", money(o.risk_limits.max_trade_premium) + " max / trade");
  text(
    "ready-risk",
    o.kill_switch
      ? "Entries paused; exits remain available"
      : "Recomputed before every paper fill",
  );
  text("ready-risk-status", o.kill_switch ? "Paused" : "Active");
  text(
    "ready-ai",
    o.ai_provider === "offline"
      ? "Offline summaries · no model connected"
      : "Model explanations · advisory only",
  );
  text(
    "source-note",
    o.source === "DEMO"
      ? "Fictional contracts. Sample prices. Simulated funds."
      : "Kite market data. Simulated funds. Paper execution only.",
  );
  text(
    "environment-title",
    o.source === "DEMO"
      ? "A workspace for practice."
      : "Your paper trading workspace.",
  );
  $("strip-demo").hidden = !o.demo_enabled;
  $("run-backtest").hidden = !o.demo_enabled;
  const exposure = state.positions
    .filter((p) => p.status === "OPEN")
    .reduce(
      (s, p) => s + Number(p.entry_price) * p.quantity + Number(p.entry_fee),
      0,
    );
  text("exposure-label", money(exposure));
  $("exposure-progress").value = Math.min(
    100,
    (exposure / Number(o.risk_limits.max_total_premium)) * 100,
  );
  text(
    "exposure-limit",
    "of " + money(o.risk_limits.max_total_premium) + " configured limit",
  );
  text("spot", number(state.analytics?.spot));
  text(
    "spot-change",
    state.analytics
      ? signed(state.analytics.change_pct) + "% vs previous close"
      : "No snapshot",
  );
  $("spot-change").className =
    "market-change " +
    (state.analytics?.change_pct < 0 ? "negative" : "positive");
  text(
    "chart-source",
    o.source === "DEMO" ? "Sample prices · IST" : "Kite prices · IST",
  );
  html(
    "market-chart",
    chart(
      state.timeline.slice(-state.range),
      "spot",
      "timestamp",
      "market-gradient",
    ),
  );
  html(
    "recent-proposals",
    state.proposals.length
      ? state.proposals
          .slice(0, 3)
          .map(
            (p) =>
              `<a href="#proposals" class="compact-row">${icon("layers")}<div><strong>${esc(p.intent.instrument_id.replace("NFO:", ""))}</strong><small>Buy ${p.intent.quantity} · ${money(p.intent.limit_price)} limit</small></div>${pill(humanize(proposalStatus(p, now())), proposalStatus(p, now()) === "pending" ? "good" : "")}</a>`,
          )
          .join("")
      : empty(
          "A clear next step.",
          "Refresh sample prices, then generate your first proposal.",
        ),
  );
  html(
    "recent-activity",
    events()
      .slice(0, 3)
      .map(
        (e) =>
          `<a href="#activity" class="compact-row">${icon(eventIcon(e.event))}<div><strong>${esc(eventTitle(e.event))}</strong><small>${esc(e.actor)} · ${when(e.created_at)}</small></div><span class="subtle">↗</span></a>`,
      )
      .join("") ||
      empty(
        "A fresh workspace.",
        "Your actions and control decisions will appear here.",
      ),
  );
  html(
    "settings-limits",
    definition([
      ["Execution", "Paper only"],
      [
        "Data source",
        o.source === "DEMO" ? "Illustrative sample data" : "Kite",
      ],
      ["Maximum trade premium", money(o.risk_limits.max_trade_premium)],
      ["Maximum total premium", money(o.risk_limits.max_total_premium)],
      ["Daily loss limit", money(o.risk_limits.max_daily_loss)],
      ["Maximum open positions", o.risk_limits.max_positions],
      ["Maximum quote age", o.max_quote_age_seconds + " seconds"],
    ]).replace(/^<dl[^>]*>|<\/dl>$/g, ""),
  );
  $("kill-switch").setAttribute("aria-checked", String(o.kill_switch));
}
function chainRows() {
  const query = $("chain-search").value.trim().toLowerCase();
  return (state.market?.chain || []).filter(
    (q) =>
      (state.optionType === "all" || q.type === state.optionType) &&
      ($("expiry").value === "all" || q.expiry === $("expiry").value) &&
      (!query ||
        `${q.instrument_id} ${q.strike} ${q.type}`
          .toLowerCase()
          .includes(query)),
  );
}
function renderMarket() {
  const a = state.market,
    expiry = $("expiry").value,
    expiries = [...new Set((a?.chain || []).map((q) => q.expiry))].sort();
  html(
    "expiry",
    '<option value="all">All expiries</option>' +
      expiries
        .map(
          (e) =>
            `<option value="${esc(e)}">${esc(date(e).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric", timeZone: "Asia/Kolkata" }))}</option>`,
        )
        .join(""),
  );
  $("expiry").value = expiries.includes(expiry) ? expiry : "all";
  text("chain-spot", number(a?.spot));
  text("pcr", number(a?.put_call_oi_ratio));
  const ivs = (a?.chain || []).map((x) => x.iv).filter((x) => x !== null);
  text(
    "chain-iv",
    ivs.length
      ? number((ivs.reduce((s, x) => s + x, 0) / ivs.length) * 100) + "%"
      : "—",
  );
  text(
    "chain-source",
    state.underlying +
      " · NFO · " +
      (a?.source === "DEMO" ? "SAMPLE" : a?.source || "NO DATA"),
  );
  const rows = chainRows(),
    near = a?.chain?.length
      ? Math.min(
          ...a.chain.map((q) => Math.abs(Number(q.strike) - Number(a.spot))),
        )
      : null;
  html(
    "chain",
    rows.length
      ? rows
          .map(
            (q) =>
              `<tr class="${Math.abs(Number(q.strike) - Number(a.spot)) === near ? "atm" : ""}"><td><strong>${number(q.strike, 0)}</strong>${Math.abs(Number(q.strike) - Number(a.spot)) === near ? '<span class="atm-label">ATM</span>' : ""}<small>${esc(q.expiry)}</small></td><td><span class="option-tag ${q.type === "PE" ? "put" : ""}">${esc(q.type)}</span></td><td>${number(q.bid)}</td><td>${number(q.ask)}</td><td title="${q.iv == null ? "No valid implied volatility for this quote" : "Estimated from the bid–ask midpoint"}">${q.iv == null ? "—" : number(q.iv * 100) + "%"}</td><td>${number(q.greeks?.delta, 3)}</td><td>${number(q.greeks?.gamma, 5)}</td><td>${number(q.greeks?.theta)}</td><td>${number(q.greeks?.vega)}</td><td>${number(q.oi, 0)}</td></tr>`,
          )
          .join("")
      : `<tr><td colspan="10" class="empty-cell">${a ? "No contracts match these filters." : state.underlying === "BANKNIFTY" ? "No BANK NIFTY snapshot. The sample generator supplies NIFTY only." : "No market snapshot yet. Update the sample market to explore the chain."}</td></tr>`,
  );
  text(
    "chain-count",
    `${rows.length} of ${a?.chain?.length || 0} contracts${a ? " · " + when(a.as_of) + " IST" : ""}`,
  );
}
function riskDetails(p) {
  const risk = state.risks[p.id];
  if (!risk) return "";
  return `<details class="risk-detail" data-key="risk-${esc(p.id)}"><summary>${risk.allowed ? "Passed at last assessment" : "Blocked at last assessment"} <span>View ${Object.keys(risk.checks).length} checks</span></summary><div class="risk-checks">${Object.entries(
    risk.checks,
  )
    .map(
      ([key, ok]) =>
        `<div class="${ok ? "positive" : "negative"}">${icon(ok ? "check" : "x")}<span>${esc(riskLabels[key] || humanize(key))}</span></div>`,
    )
    .join(
      "",
    )}<small>Checks run again at confirmation. This record is not a standing approval.</small></div></details>`;
}
function renderProposals() {
  const rows = filteredProposals();
  html(
    "proposal-list",
    rows.length
      ? rows
          .map((p) => {
            const i = p.intent,
              status = proposalStatus(p, now());
            return `<article class="proposal-card"><div class="proposal-top"><span class="strategy-label">${icon("layers")} MOMENTUM · V1</span>${pill(humanize(status), status === "pending" ? "good" : "")}</div><div class="proposal-body"><h2 class="proposal-title">Long ${i.instrument_id.endsWith("PE") ? "put" : "call"} proposal</h2><span class="instrument-code">${esc(i.instrument_id)}</span><p class="signal-text">${esc(i.signal)}</p><div class="proposal-details"><div><small>QUANTITY</small><strong>${number(i.quantity, 0)}</strong></div><div><small>LIMIT PRICE</small><strong>${money(i.limit_price)}</strong></div><div><small>PREMIUM AT LIMIT</small><strong>${money(Number(i.limit_price) * i.quantity)}</strong></div></div><div class="exit-rules"><span>Stop ${number(Number(i.stop_loss_pct) * 100, 0)}%</span><span>Target ${number(Number(i.take_profit_pct) * 100, 0)}%</span><span>Time exit ${i.max_holding_minutes}m</span></div></div><div class="proposal-actions"><span class="expiry-hint">${status === "pending" ? "Valid until " + when(p.expires_at, false) + " IST" : "Created " + when(p.created_at)}</span>${status === "pending" ? `<button class="button primary small" data-review="${esc(p.id)}">Review paper order ${icon("arrow-right")}</button>` : ""}</div>${riskDetails(p)}</article>`;
          })
          .join("")
      : empty(
          "No " +
            (state.proposalFilter === "all" ? "" : state.proposalFilter + " ") +
            "proposals.",
          "A fresh snapshot and a qualifying signal create your next proposal.",
        ),
  );
}
function renderPortfolio() {
  const rows = state.positions.filter(
    (p) => state.positionFilter === "all" || p.status === state.positionFilter,
  );
  html(
    "positions",
    rows.length
      ? rows
          .map((p) => {
            const pnl =
                p.status === "OPEN"
                  ? (Number(p.mark_price) - Number(p.entry_price)) *
                      p.quantity -
                    Number(p.entry_fee)
                  : Number(p.realized_pnl),
              fresh = isFresh(
                p.mark_at,
                state.overview?.max_quote_age_seconds || 60,
                now(),
              );
            return `<tr><td><strong>${esc(p.instrument_id.replace("NFO:", ""))}</strong><small>${when(p.opened_at)} IST</small></td><td>${number(p.quantity, 0)}</td><td>${money(p.entry_price)}</td><td>${money(p.mark_price)}<small>${p.status === "OPEN" ? (fresh ? "As of " : "Stale · ") + when(p.mark_at, false) : "Final stored mark"}</small></td><td class="${pnl < 0 ? "negative" : "positive"}">${money(pnl)}</td><td>${pill(humanize(p.status), p.status === "OPEN" ? "good" : "")}</td><td>${p.status === "OPEN" ? `<button class="button small" data-close="${esc(p.id)}">Close position</button>` : "—"}</td></tr>`;
          })
          .join("")
      : `<tr><td colspan="7" class="empty-cell">No ${state.positionFilter === "all" ? "" : state.positionFilter.toLowerCase() + " "}positions. Filled paper proposals appear here.</td></tr>`,
  );
  html(
    "orders",
    state.orders.length
      ? state.orders
          .map(
            (o) =>
              `<tr><td><strong>${esc(o.instrument_id.replace("NFO:", ""))}</strong><small>${when(o.created_at)} IST</small></td><td><span class="option-tag ${o.side === "SELL" ? "put" : ""}">${esc(o.side)}</span></td><td>${o.quantity}</td><td>${money(o.fill_price)}</td><td>${money(o.fee)}</td><td>${esc(humanize(o.reason))}</td></tr>`,
          )
          .join("")
      : '<tr><td colspan="6" class="empty-cell">Your paper fills will appear here.</td></tr>',
  );
  text("order-count", state.orders.length + " latest orders");
}
function renderAgents() {
  const offline = state.overview?.ai_provider !== "openai";
  text("ai-mode", offline ? "Offline summaries" : "Model explanations enabled");
  text(
    "ai-explanation",
    offline
      ? "No language model is connected. Each role returns a fixed summary of supplied workspace data."
      : "Four read-only specialists explain supplied workspace data. Verify model output against the recorded facts.",
  );
  html(
    "agent-cards",
    agents
      .map(
        ([id, name, desc, glyph], index) =>
          `<button class="agent-card ${state.selectedAgent === id ? "selected" : ""}" data-agent="${id}" aria-pressed="${state.selectedAgent === id}">${icon(glyph)}<small>0${index + 1}</small><strong>${name}</strong><p>${desc}</p><span class="agent-state">${state.selectedAgent === id ? "Selected specialist" : "Explore perspective"} ↗</span></button>`,
      )
      .join(""),
  );
  const agent = agents.find((a) => a[0] === state.selectedAgent);
  text("conversation-eyebrow", agent[1].toUpperCase());
  text(
    "conversation-title",
    state.selectedAgent === "trading_assistant"
      ? "A second perspective."
      : "Explore this perspective.",
  );
  const runs = state.runs
    .filter((r) => r.agent === state.selectedAgent)
    .slice(0, 8)
    .reverse();
  html(
    "conversation",
    runs.length
      ? runs
          .map(
            (r) =>
              `${r.output.question ? `<article class="message question"><div class="message-meta"><strong>You</strong><small>${when(r.created_at)}</small></div><p>${esc(r.output.question)}</p></article>` : ""}<article class="message"><div class="message-meta">${icon(agent[3])}<strong>${esc(agent[1])}</strong><small>${r.provider === "offline" ? "Offline summary" : "Model response"} · ${when(r.created_at)}</small></div><p>${esc(r.output.text)}</p></article>`,
          )
          .join("")
      : empty(
          "Start with a question.",
          offline
            ? "Choose a specialist and request a summary. Offline mode cannot answer free-form questions."
            : "Choose a specialist and ask about your current workspace.",
        ),
  );
  text(
    "chat-context",
    offline
      ? "Offline mode returns a fixed summary"
      : "Workspace context is read-only",
  );
}
function renderBacktests() {
  html(
    "backtest-select",
    state.backtests.length
      ? state.backtests
          .map(
            (r) =>
              `<option value="${esc(r.id)}">${when(r.created_at)} IST · ${esc(r.report.source)} · ${r.id.slice(0, 6)}</option>`,
          )
          .join("")
      : '<option value="">No saved runs</option>',
  );
  $("backtest-select").value = state.backtestId;
  const run = state.backtests.find((r) => r.id === state.backtestId);
  if (!run) {
    html(
      "backtest-result",
      empty(
        "Research begins with a replay.",
        "Run the sample backtest to save your first report.",
      ),
    );
    return;
  }
  const r = run.report;
  html(
    "backtest-result",
    `<div class="backtest-metrics">${[
      ["Net P&L", money(r.net_pnl)],
      ["Max drawdown", money(r.max_drawdown)],
      ["Closed trades", r.trade_count],
      ["Ending equity", money(r.ending_equity)],
    ]
      .map(
        ([label, val]) =>
          `<div><span>${label}</span><strong>${val}</strong></div>`,
      )
      .join(
        "",
      )}</div><article class="panel backtest-result-panel"><div class="panel-header"><div><span class="eyebrow">${esc(r.source)} · ${r.snapshot_count} OBSERVATIONS</span><h2>Paper equity through the replay</h2></div>${pill("Saved report")}</div><div class="replay-chart">${chart(r.equity_curve, "equity", "at", "replay-gradient", true)}</div><div class="panel-foot">${r.rejections.length} risk / limit rejections · ${r.open_positions_at_end} positions open at end · ${r.trade_count} closed trades</div></article><div class="backtest-note"><strong>Simulation assumptions</strong><ul>${r.assumptions.map((a) => `<li>${esc(a)}</li>`).join("")}</ul></div>`,
  );
}
const eventTitle = (event) =>
  ({
    "market.snapshot_ingested": "Market snapshot recorded",
    "market.snapshot": "Market snapshot recorded",
    "paper.entry_filled": "Paper entry filled",
    "paper.exit_filled": "Paper position closed",
    "risk.evaluated": "Risk assessment completed",
    "risk.kill_switch_changed": "Entry control updated",
    "proposal.created": "Trade proposal generated",
    "agent.completed": "Advisory summary saved",
    "agent.failed": "Advisory request failed",
    "backtest.completed": "Backtest report saved",
    "monitor.attention": "Position needs attention",
  })[event] || humanize(event);
const eventIcon = (event) =>
  event.startsWith("paper")
    ? "briefcase"
    : event.startsWith("risk")
      ? "shield"
      : event.startsWith("market")
        ? "chart"
        : event.startsWith("agent")
          ? "sparkle"
          : event.startsWith("backtest")
            ? "flask"
            : "activity";
const events = () => [...state.audit.values()].sort((a, b) => b.id - a.id);
function renderActivity() {
  const filter = $("audit-filter").value,
    rows = events().filter(
      (e) => filter === "all" || e.event.startsWith(filter),
    );
  html(
    "audit-list",
    rows.length
      ? rows
          .map(
            (e) =>
              `<details class="audit-item" data-key="event-${e.id}"><summary>${icon(eventIcon(e.event))}<div><strong>${esc(eventTitle(e.event))}</strong><small>${esc(e.actor)} · Event #${e.id}</small></div><span>${when(e.created_at)} IST</span></summary><pre>${esc(JSON.stringify(e.payload, null, 2))}</pre></details>`,
          )
          .join("")
      : empty(
          "No matching activity.",
          "Actions will appear here as they happen.",
        ),
  );
  text("audit-count", `${rows.length} matching · ${state.audit.size} loaded`);
  $("older-events").hidden = !state.olderAvailable;
  html(
    "notifications",
    state.notes.length
      ? state.notes
          .map(
            (n) =>
              `<article class="notification">${icon(n.topic.startsWith("risk") ? "shield" : "bell")}<div><strong>${esc(humanize(n.topic))}</strong><p>${esc(n.message)}</p><small>${when(n.created_at)} IST · Workspace inbox</small></div></article>`,
          )
          .join("")
      : empty(
          "All quiet for now.",
          "Paper orders and control changes will appear here.",
        ),
  );
}
function renderFreshness() {
  const o = state.overview,
    fresh = currentFresh();
  text(
    "data-status",
    !state.connected
      ? "Disconnected"
      : fresh
        ? "Fresh snapshot"
        : state.analytics
          ? "Stale snapshot"
          : "Awaiting data",
  );
  $("data-status").className = "badge dark" + (fresh ? " good" : "");
  text(
    "as-of",
    state.analytics
      ? "As of " +
          when(state.analytics.as_of) +
          " IST · " +
          age(state.analytics.as_of, now())
      : "No stored data yet",
  );
  text(
    "ready-data",
    fresh
      ? "Within the " + o.max_quote_age_seconds + "-second freshness limit"
      : state.analytics
        ? "Refresh prices before a new entry"
        : "Load a sample snapshot to begin",
  );
  text("ready-data-status", fresh ? "Ready" : "Waiting");
  text(
    "mark-status",
    state.positions.some(
      (p) =>
        p.status === "OPEN" &&
        !isFresh(p.mark_at, o?.max_quote_age_seconds || 60, now()),
    )
      ? "marks stale · refresh prices"
      : "net of entry fees",
  );
  text(
    "chain-freshness",
    !state.connected
      ? "Disconnected"
      : !state.market
        ? "No snapshot"
        : isFresh(state.market.as_of, o?.max_quote_age_seconds || 60, now())
          ? "Fresh snapshot"
          : "Stale snapshot",
  );
  text(
    "proposal-count",
    state.proposals.filter((p) => proposalStatus(p, now()) === "pending")
      .length,
  );
  const gate = !state.connected
    ? "Connect to the workspace before creating a proposal."
    : o?.kill_switch
      ? "New entries are paused. You can still review records and close positions."
      : !fresh
        ? "Prices need a refresh. New entries require a fresh market snapshot."
        : "Fresh prices are available. Every paper fill will run through deterministic risk checks.";
  html(
    "proposal-gate",
    icon(entryReady() ? "shield" : "alert") +
      `<span>${gate}</span>` +
      (!fresh && state.connected && o?.demo_enabled
        ? '<button class="text-link" data-action="demo">Update sample market ↗</button>'
        : ""),
  );
  updateControls();
}
function render() {
  renderConnection();
  renderOverview();
  renderMarket();
  renderProposals();
  renderPortfolio();
  renderAgents();
  renderBacktests();
  renderActivity();
  renderFreshness();
}
function updateControls() {
  if (review && !review.close && $("review-dialog").open) {
    const expired = proposalStatus(review.proposal, now()) !== "pending";
    text(
      "review-validity",
      expired
        ? "This proposal has expired. Generate a new proposal to continue."
        : !currentFresh()
          ? "Prices are stale. Close this review and refresh the market."
          : state.overview?.kill_switch
            ? "New entries are paused."
            : "Risk and prices are rechecked on confirmation.",
    );
  }
  all("[data-action]").forEach((b) => {
    const key = b.dataset.action;
    b.disabled =
      busy.has(key) ||
      (["new-proposal"].includes(key) && !entryReady()) ||
      (["demo", "monitor", "backtest", "older-events"].includes(key) &&
        !state.connected) ||
      (["export-chain"].includes(key) && !chainRows().length) ||
      (["export-orders"].includes(key) && !state.orders.length) ||
      (["export-backtest"].includes(key) && !state.backtestId);
  });
  all("[data-review]").forEach((b) => {
    const p = state.proposals.find((p) => p.id === b.dataset.review);
    b.disabled =
      !state.connected ||
      !p ||
      proposalStatus(p, now()) !== "pending" ||
      busy.has("review");
  });
  all("[data-close]").forEach(
    (b) => (b.disabled = !state.connected || busy.has("review")),
  );
  $("underlying").disabled = busy.has("underlying");
  $("kill-switch").disabled = !state.connected || busy.has("kill");
  $("send-question").disabled = !state.connected || busy.has("chat");
  $("send-question").innerHTML = busy.has("chat")
    ? "Preparing response…"
    : "Send question " + icon("arrow-up");
  $("load-demo").disabled = busy.has("demo-submit");
  $("auth-submit").disabled = busy.has("login");
  $("confirm-order").disabled =
    busy.has("confirm") ||
    !state.connected ||
    !review ||
    (!review.close &&
      (!review.allowed ||
        !entryReady() ||
        proposalStatus(review.proposal, now()) !== "pending"));
  all("#review-dialog [data-dismiss]").forEach(
    (b) => (b.disabled = busy.has("confirm")),
  );
  $("confirm-order").textContent = busy.has("confirm")
    ? "Submitting…"
    : review?.close
      ? "Confirm paper exit"
      : "Confirm paper order";
  $("refresh").classList.toggle("spinning", busy.has("refresh"));
}
function navigate(focus = false) {
  const value = location.hash.slice(1),
    aliases = { positions: "portfolio", chain: "market", ai: "agents" };
  route = routes[value] ? value : aliases[value] || "overview";
  const [label, title, eyebrow, description] = routes[route];
  all("[data-page]").forEach((el) => (el.hidden = el.dataset.page !== route));
  all("[data-nav]").forEach((el) => {
    el.classList.toggle("active", el.dataset.nav === route);
    if (el.dataset.nav === route) el.setAttribute("aria-current", "page");
    else el.removeAttribute("aria-current");
  });
  text("breadcrumb-current", label);
  html("page-title", esc(title) + "<span>.</span>");
  text("page-eyebrow", eyebrow);
  text("page-description", description);
  document.title = label + " — Murarka Capital";
  const primary = $("page-primary");
  const primaryAction =
    route === "market"
      ? "demo"
      : route === "backtest"
        ? "backtest"
        : route === "agents"
          ? "focus-chat"
          : route === "activity"
            ? "settings"
            : "new-proposal";
  primary.dataset.action = primaryAction;
  primary.hidden =
    (primaryAction === "demo" || primaryAction === "backtest") &&
    state.overview?.demo_enabled === false;
  primary.innerHTML =
    icon(
      primaryAction === "new-proposal"
        ? "plus"
        : primaryAction === "demo"
          ? "chart"
          : primaryAction === "backtest"
            ? "flask"
            : primaryAction === "settings"
              ? "settings"
              : "sparkle",
    ) +
    {
      demo: "Update sample",
      backtest: "Run sample replay",
      "focus-chat": "Ask a question",
      settings: "Settings",
      "new-proposal": "New proposal",
    }[primaryAction];
  closeNav();
  if ($("search-dialog").open) $("search-dialog").close();
  if (focus) {
    $("page-title").focus({ preventScroll: true });
    window.scrollTo({ top: 0, behavior: "instant" });
  }
  updateControls();
}
const mobile = matchMedia("(max-width:720px)");
function closeNav() {
  $("sidebar").classList.remove("open");
  $("mobile-scrim").hidden = true;
  $("mobile-menu").setAttribute("aria-expanded", "false");
  $("sidebar").inert = mobile.matches;
  document.querySelector(".app-shell").inert = false;
  document.body.classList.remove("nav-open");
}
function openNav() {
  $("sidebar").inert = false;
  $("sidebar").classList.add("open");
  $("mobile-scrim").hidden = false;
  $("mobile-menu").setAttribute("aria-expanded", "true");
  document.querySelector(".app-shell").inert = true;
  document.body.classList.add("nav-open");
  $("main-nav").querySelector("[aria-current=page]").focus();
}
function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  text(
    "theme-label",
    theme === "light" ? "Dark appearance" : "Light appearance",
  );
  $("theme-toggle").querySelector(".icon").innerHTML = icon(
    theme === "light" ? "moon" : "sun",
  ).replace(/^<span[^>]*>|<\/span>$/g, "");
  try {
    localStorage.setItem("optionlab-theme", theme);
  } catch {}
}
function searchPages() {
  const q = $("quick-search").value.trim().toLowerCase();
  html(
    "search-results",
    Object.entries(routes)
      .filter(([, r]) => r.join(" ").toLowerCase().includes(q))
      .map(
        ([key, r]) =>
          `<a href="#${key}">${icon(r[4])}<span>${r[0]}</span><small>Open ↗</small></a>`,
      )
      .join("") ||
      empty("No pages found.", "Try “portfolio”, “markets”, or “activity”."),
  );
}
function openSearch() {
  showModal("search-dialog");
  $("quick-search").value = "";
  searchPages();
  $("quick-search").focus();
}
function download(name, data, type) {
  const link = document.createElement("a"),
    url = URL.createObjectURL(new Blob([data], { type }));
  link.href = url;
  link.download = name;
  link.hidden = true;
  document.body.append(link);
  link.click();
  link.remove();
  // Give Safari and embedded browsers time to hand the blob to their download manager.
  setTimeout(() => URL.revokeObjectURL(url), 30000);
  toast("Export prepared: " + name);
}
async function reviewEntry(id) {
  const p = state.proposals.find((p) => p.id === id);
  if (!p) return;
  const risk = await api(
    "/proposals/" + encodeURIComponent(id) + "/risk",
    "POST",
  );
  state.risks[id] = risk;
  review = { proposal: p, allowed: risk.allowed };
  text("review-title", "Review your paper order.");
  $("review-error").hidden = true;
  html(
    "review-content",
    `<div class="review-hero"><strong>Buy ${number(p.intent.quantity, 0)} units</strong><small>${esc(p.intent.instrument_id)}</small></div>${definition(
      [
        ["Limit price", money(p.intent.limit_price)],
        ["Maximum premium + entry fee", money(risk.estimated_cost)],
        [
          "Stop / target",
          number(Number(p.intent.stop_loss_pct) * 100, 0) +
            "% / " +
            number(Number(p.intent.take_profit_pct) * 100, 0) +
            "%",
        ],
        ["Time exit", p.intent.max_holding_minutes + " minutes"],
        ["Proposal valid until", when(p.expires_at, false) + " IST"],
      ],
    )}<div class="review-result ${risk.allowed ? "good" : "bad"}">${risk.allowed ? `${Object.keys(risk.checks).length} checks passed at this assessment.` : "Entry blocked."}${!risk.allowed ? "<ul>" + risk.reasons.map((x) => `<li>${esc(riskLabels[x] || humanize(x))}</li>`).join("") + "</ul>" : ""}</div><p id="review-validity" class="review-validity"></p><div class="modal-note">The server rechecks risk and the current quote at confirmation. Fills are simulated at the ask plus one adverse tick, within your limit.</div>`,
  );
  renderProposals();
  showModal("review-dialog");
  updateControls();
}
function reviewClose(id) {
  const p = state.positions.find((p) => p.id === id);
  if (!p) return;
  review = { close: p };
  text("review-title", "Close this paper position?");
  $("review-error").hidden = true;
  html(
    "review-content",
    `<div class="review-hero"><strong>Sell ${number(p.quantity, 0)} units</strong><small>${esc(p.instrument_id)}</small></div>${definition(
      [
        ["Entry price", money(p.entry_price)],
        ["Last stored bid mark", money(p.mark_price)],
        ["Mark recorded", when(p.mark_at) + " IST"],
        ["Exit fee", money(state.overview.paper_fee_per_order)],
      ],
    )}<div class="modal-note">The final exit uses a fresh executable bid minus one adverse tick. The server will reject an exit if a valid fresh quote is unavailable. The stored mark is not a guaranteed fill.</div>`,
  );
  showModal("review-dialog");
  updateControls();
}
const actions = {
  refresh: async () => {
    await refresh(true);
    toast("Workspace refreshed.");
  },
  retry: async () => {
    await startSession(false);
  },
  settings: () => showModal("settings-dialog"),
  demo: () => {
    const spot = Number(state.analytics?.spot);
    if (spot >= 20000 && spot <= 30000) $("demo-spot").value = spot;
    $("demo-error").hidden = true;
    showModal("demo-dialog");
  },
  "focus-chat": () => {
    $("question").focus();
  },
  "new-proposal": async () => {
    const p = await api("/proposals", "POST", {});
    await api("/proposals/" + p.id + "/risk", "POST");
    await refresh(true);
    location.hash = "proposals";
    toast("Proposal saved. Review the signal and risk checks.");
  },
  monitor: async () => {
    const result = await api("/monitor/run", "POST");
    await refresh(true);
    toast(
      result.attention.length
        ? result.attention.length + " positions need fresh quotes or attention."
        : result.closed_orders.length +
            " exits completed. Position checks are up to date.",
      Boolean(result.attention.length),
    );
  },
  backtest: async () => {
    const r = await api("/demo/backtest", "POST");
    state.backtestId = r.id;
    await refresh(true);
    location.hash = "backtest";
    toast("Replay complete. Your report is saved.");
  },
  "older-events": async () => {
    const oldest = Math.min(...state.audit.keys());
    const r = await api("/audit?newest=true&limit=100&before_id=" + oldest);
    r.events.forEach((e) => state.audit.set(e.id, e));
    state.olderAvailable = r.events.length === 100;
    renderActivity();
  },
  "export-chain": () =>
    download(
      "murarka-capital-chain.csv",
      csv([
        [
          "Instrument",
          "Expiry",
          "Strike",
          "Type",
          "Bid",
          "Ask",
          "IV",
          "Delta",
          "Gamma",
          "Theta per day",
          "Vega per 1%",
          "OI",
        ],
        ...chainRows().map((q) => [
          q.instrument_id,
          q.expiry,
          q.strike,
          q.type,
          q.bid,
          q.ask,
          q.iv,
          q.greeks?.delta,
          q.greeks?.gamma,
          q.greeks?.theta,
          q.greeks?.vega,
          q.oi,
        ]),
      ]),
      "text/csv;charset=utf-8",
    ),
  "export-orders": () =>
    download(
      "murarka-capital-paper-orders.csv",
      csv([
        [
          "ID",
          "Instrument",
          "Side",
          "Quantity",
          "Fill price",
          "Fee",
          "Reason",
          "Time UTC",
        ],
        ...state.orders.map((o) => [
          o.id,
          o.instrument_id,
          o.side,
          o.quantity,
          o.fill_price,
          o.fee,
          o.reason,
          o.created_at,
        ]),
      ]),
      "text/csv;charset=utf-8",
    ),
  "export-backtest": () =>
    download(
      "murarka-capital-backtest-" + state.backtestId + ".json",
      JSON.stringify(
        state.backtests.find((r) => r.id === state.backtestId),
        null,
        2,
      ),
      "application/json",
    ),
};
document.addEventListener("click", (event) => {
  const b = event.target.closest("button,a");
  if (!b) return;
  if (b.classList.contains("skip-link")) {
    event.preventDefault();
    $("main").focus();
    return;
  }
  if (b.tagName === "A" && b.getAttribute("href") === "#" + route) {
    event.preventDefault();
    navigate(true);
  }
  if (b.dataset.action && actions[b.dataset.action])
    run(b.dataset.action, actions[b.dataset.action]);
  if (b.dataset.route) location.hash = b.dataset.route;
  if (b.dataset.dismiss) $(b.dataset.dismiss).close();
  if (b.dataset.spot) $("demo-spot").value = b.dataset.spot;
  if (b.dataset.review) run("review", () => reviewEntry(b.dataset.review));
  if (b.dataset.close) run("review", () => reviewClose(b.dataset.close));
  if (b.dataset.agent) {
    state.selectedAgent = b.dataset.agent;
    renderAgents();
  }
  if (b.dataset.prompt) {
    $("question").value = b.dataset.prompt;
    $("question").focus();
  }
  const filters = [
    ["type", "optionType", renderMarket],
    ["proposalFilter", "proposalFilter", renderProposals],
    ["positionFilter", "positionFilter", renderPortfolio],
    ["range", "range", renderOverview],
  ];
  filters.forEach(([attribute, key, renderFn]) => {
    if (b.dataset[attribute] !== undefined) {
      state[key] =
        key === "range" ? Number(b.dataset[attribute]) : b.dataset[attribute];
      b.parentElement
        .querySelectorAll("button")
        .forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      renderFn();
      updateControls();
    }
  });
  if (b.closest("#search-results")) $("search-dialog").close();
});
$("demo-form").onsubmit = (event) => {
  event.preventDefault();
  run(
    "demo-submit",
    async () => {
      await api("/demo/tick", "POST", { spot: $("demo-spot").value });
      await refresh(true);
      $("demo-dialog").close();
      toast("Sample market updated. Open positions were checked for exits.");
    },
    "demo-error",
  );
};
$("auth-form").onsubmit = (event) => {
  event.preventDefault();
  run(
    "login",
    async () => {
      await request("/auth/login", "POST", { token: $("api-token").value });
      $("api-token").value = "";
      state.authenticated = true;
      $("auth-dialog").close();
      await refresh(true);
      toast("Welcome to your workspace.");
    },
    "auth-error",
  );
};
$("sign-out").onclick = () =>
  run("logout", async () => {
    await request("/auth/logout", "POST", {});
    state.authenticated = false;
    state.connected = false;
    all("dialog[open]").forEach((d) => d.close());
    location.reload();
  });
$("kill-switch").onclick = () =>
  run("kill", async () => {
    await api("/risk/kill-switch", "PUT", {
      enabled: !state.overview.kill_switch,
    });
    await refresh(true);
    toast(
      state.overview.kill_switch
        ? "New entries paused. Existing positions can still exit."
        : "New entries enabled, subject to all risk checks.",
    );
  });
$("confirm-order").onclick = () =>
  run(
    "confirm",
    async () => {
      const pending = review;
      try {
        if (pending.close)
          await api("/positions/" + pending.close.id + "/close", "POST", {
            idempotency_key: "manual-exit:" + pending.close.id,
          });
        else
          await api("/paper/orders", "POST", {
            proposal_id: pending.proposal.id,
            idempotency_key: "entry:" + pending.proposal.id,
          });
        $("review-dialog").close();
        toast(
          pending.close
            ? "Paper position closed."
            : "Paper order filled. Your position and ledger are updated.",
        );
      } catch (error) {
        if (error.result?.risk) {
          state.risks[pending.proposal.id] = error.result.risk;
          if (review) review.allowed = false;
        }
        throw error;
      } finally {
        await refresh(true);
      }
    },
    "review-error",
  );
$("review-dialog").addEventListener("close", () => {
  review = null;
});
$("review-dialog").addEventListener("cancel", (event) => {
  if (busy.has("confirm")) event.preventDefault();
});
$("chat-form").onsubmit = (event) => {
  event.preventDefault();
  const question = $("question").value.trim();
  if (!question) {
    $("question").focus();
    return;
  }
  run("chat", async () => {
    const role = state.selectedAgent;
    agentQuestion = question;
    await api("/agents/explain", "POST", {
      agent: role,
      question,
      proposal_id:
        role === "strategy_reasoning" ? (state.proposals[0]?.id ?? null) : null,
    });
    if ($("question").value.trim() === agentQuestion) $("question").value = "";
    await refresh(true);
    $("conversation").scrollTop = $("conversation").scrollHeight;
  });
};
$("question").onkeydown = (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    event.preventDefault();
    $("chat-form").requestSubmit();
  }
};
$("underlying").onchange = () =>
  run("underlying", async () => {
    state.underlying = $("underlying").value;
    state.market = null;
    renderMarket();
    renderFreshness();
    await refresh(true);
  });
$("expiry").onchange = () => {
  renderMarket();
  updateControls();
};
$("chain-search").oninput = () => {
  renderMarket();
  updateControls();
};
$("backtest-select").onchange = () => {
  state.backtestId = $("backtest-select").value;
  renderBacktests();
};
$("audit-filter").onchange = renderActivity;
$("quick-search").oninput = searchPages;
$("search-open").onclick = openSearch;
$("theme-toggle").onclick = () =>
  setTheme(
    document.documentElement.dataset.theme === "light" ? "dark" : "light",
  );
$("mobile-menu").onclick = openNav;
$("mobile-scrim").onclick = () => {
  closeNav();
  $("mobile-menu").focus();
};
mobile.addEventListener("change", closeNav);
document.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
    event.preventDefault();
    if (!$("auth-dialog").open) openSearch();
  }
  if ($("sidebar").classList.contains("open")) {
    if (event.key === "Escape") {
      closeNav();
      $("mobile-menu").focus();
    }
    if (event.key === "Tab") {
      const nodes = [...$("sidebar").querySelectorAll("a,button")].filter(
          (x) => !x.disabled,
        ),
        first = nodes[0],
        last = nodes.at(-1);
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  }
});
window.addEventListener("hashchange", () => navigate(true));
window.addEventListener("online", () => refresh(true).catch(() => {}));
window.addEventListener("offline", () => {
  state.connected = false;
  renderConnection(
    "You’re offline",
    "Reconnect to refresh prices and continue.",
  );
  renderFreshness();
});
document.addEventListener("visibilitychange", () => {
  if (!document.hidden && state.authenticated) refresh().catch(() => {});
});
async function startSession(initial = true) {
  try {
    const session = await request("/auth/session");
    state.authRequired = session.auth_required;
    state.authenticated = session.authenticated;
    if (!session.authenticated) {
      renderConnection(
        "Sign in to continue",
        "Use your workspace access key to unlock this session.",
      );
      showModal("auth-dialog");
      return;
    }
    await refresh(true);
  } catch (error) {
    state.connected = false;
    renderConnection("Workspace unavailable", error.message);
    if (!initial) throw error;
  }
}
try {
  setTheme(
    localStorage.getItem("optionlab-theme") === "dark" ? "dark" : "light",
  );
} catch {
  setTheme("light");
}
text(
  "today",
  new Date().toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "Asia/Kolkata",
  }),
);
closeNav();
navigate();
renderProposals();
renderPortfolio();
renderAgents();
renderBacktests();
renderActivity();
renderMarket();
startSession();
setInterval(() => {
  if (!document.hidden && state.authenticated) refresh().catch(() => {});
}, 10000);
let lastStatus = "";
setInterval(() => {
  if (document.hidden) return;
  renderFreshness();
  const status = state.proposals.map((p) => proposalStatus(p, now())).join();
  if (status !== lastStatus) {
    lastStatus = status;
    renderProposals();
    renderOverview();
    updateControls();
  }
}, 1000);
