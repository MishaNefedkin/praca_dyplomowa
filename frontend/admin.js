const API_BASE = window.location.origin;
const TOKEN_KEY = "bw_admin_token";
const PAGE_LIMIT = 25;
const listState = {
  clients: { offset: 0, query: "" },
  inquiries: { offset: 0 },
  offers: { offset: 0 },
  activity: { offset: 0 },
};

function token() {
  return localStorage.getItem(TOKEN_KEY);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token() ? { Authorization: `Bearer ${token()}` } : {}),
      ...(options.headers || {}),
    },
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || "Request failed");
  }
  return response.json();
}

function table(rows, columns, actions = null) {
  if (!rows.length) return "<p class='muted'>Brak danych.</p>";
  const head = columns.map((column) => `<th>${escapeHtml(column.label)}</th>`).join("") + (actions ? "<th>Akcje</th>" : "");
  const body = rows
    .map((row) => {
      const cells = columns.map((column) => `<td>${escapeHtml(column.render ? column.render(row) : row[column.key])}</td>`).join("");
      return `<tr>${cells}${actions ? `<td>${actions(row)}</td>` : ""}</tr>`;
    })
    .join("");
  return `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

function buildListPath(path, params) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, value);
    }
  });
  return `${path}?${query.toString()}`;
}

function renderPager(elementId, stateKey, rows) {
  const state = listState[stateKey];
  const currentPage = Math.floor(state.offset / PAGE_LIMIT) + 1;
  document.getElementById(elementId).innerHTML = `
    <button class="button secondary" data-page="${stateKey}" data-direction="previous" ${state.offset === 0 ? "disabled" : ""}>Poprzednia</button>
    <span>Strona ${escapeHtml(currentPage)}</span>
    <button class="button secondary" data-page="${stateKey}" data-direction="next" ${rows.length < PAGE_LIMIT ? "disabled" : ""}>Następna</button>
  `;
}

function showApp(isLoggedIn) {
  document.getElementById("login-panel").classList.toggle("hidden", isLoggedIn);
  document.getElementById("admin-content").classList.toggle("hidden", !isLoggedIn);
  if (isLoggedIn) loadDashboard();
}

async function loadDashboard() {
  const status = document.getElementById("admin-status");
  status.textContent = "Ładowanie danych...";

  let kpi;
  let topPages;
  let alerts;
  let clients;
  let inquiries;
  let offers;
  let logs;

  try {
    [kpi, topPages, alerts, clients, inquiries, offers, logs] = await Promise.all([
      api("/analytics/kpi"),
      api("/analytics/top-pages"),
      api("/analytics/alerts"),
      api(buildListPath("/clients", { limit: PAGE_LIMIT, offset: listState.clients.offset, q: listState.clients.query })),
      api(buildListPath("/inquiries", { limit: PAGE_LIMIT, offset: listState.inquiries.offset, status: document.getElementById("inquiry-filter").value })),
      api(buildListPath("/offers", { limit: PAGE_LIMIT, offset: listState.offers.offset })),
      api(buildListPath("/tracking/logs", { limit: PAGE_LIMIT, offset: listState.activity.offset })),
    ]);
    status.textContent = "";
  } catch (error) {
    status.textContent = `Nie udało się załadować danych: ${error.message}`;
    if (error.message.includes("Could not validate credentials")) {
      localStorage.removeItem(TOKEN_KEY);
      showApp(false);
    }
    return;
  }

  document.getElementById("kpi-grid").innerHTML = [
    ["Klienci", kpi.clients_count],
    ["Nowe zapytania", kpi.new_inquiries_count],
    ["Wysłane oferty", kpi.sent_offers_count],
    ["Konwersja", `${kpi.inquiry_to_offer_conversion_rate}%`],
    ["Aktywność 24h", kpi.activities_last_24h],
  ].map(([label, value]) => `<article class="metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></article>`).join("");

  document.getElementById("top-pages").innerHTML = topPages.map((page) => `<p><strong>${escapeHtml(page.visits)}</strong> ${escapeHtml(page.page_url)}</p>`).join("") || "<p class='muted'>Brak wizyt.</p>";
  document.getElementById("alerts").innerHTML = alerts.map((alert) => `<p>${escapeHtml(alert.message)}</p>`).join("") || "<p class='muted'>Brak alertów.</p>";

  document.getElementById("clients-table").innerHTML = table(
    clients,
    [
      { key: "id", label: "ID" },
      { key: "name", label: "Nazwa" },
      { key: "email", label: "Email" },
      { key: "phone", label: "Telefon" },
      { key: "created_at", label: "Utworzono", render: (row) => new Date(row.created_at).toLocaleString() },
    ],
    (row) => `<button data-client="${row.id}" class="link-button">Timeline</button> <button data-export="${row.id}" class="link-button">Eksport</button> <button data-anonymize="${row.id}" class="link-button danger">Anonimizuj</button>`,
  );
  renderPager("clients-pager", "clients", clients);

  document.getElementById("inquiries-table").innerHTML = table(inquiries, [
    { key: "id", label: "ID" },
    { key: "client_id", label: "Klient" },
    { key: "status", label: "Status" },
    { key: "message", label: "Wiadomość" },
    { key: "created_at", label: "Data", render: (row) => new Date(row.created_at).toLocaleString() },
  ]);
  renderPager("inquiries-pager", "inquiries", inquiries);

  document.getElementById("offers-table").innerHTML = table(offers, [
    { key: "id", label: "ID" },
    { key: "inquiry_id", label: "Zapytanie" },
    { key: "value", label: "Wartość" },
    { key: "status", label: "Status" },
    { key: "created_at", label: "Data", render: (row) => new Date(row.created_at).toLocaleString() },
  ]);
  renderPager("offers-pager", "offers", offers);

  document.getElementById("activity-table").innerHTML = table(logs, [
    { key: "id", label: "ID" },
    { key: "client_id", label: "Klient" },
    { key: "session_id", label: "Sesja" },
    { key: "page_url", label: "Strona" },
    { key: "event_type", label: "Typ" },
    { key: "time_on_page", label: "Czas" },
    { key: "logged_at", label: "Data", render: (row) => new Date(row.logged_at).toLocaleString() },
  ]);
  renderPager("activity-pager", "activity", logs);
}

document.getElementById("login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.currentTarget).entries());
  const status = document.getElementById("login-status");
  try {
    const result = await api("/auth/login", { method: "POST", body: JSON.stringify(data) });
    localStorage.setItem(TOKEN_KEY, result.access_token);
    status.textContent = "";
    showApp(true);
  } catch (error) {
    status.textContent = error.message;
  }
});

document.getElementById("logout").addEventListener("click", () => {
  localStorage.removeItem(TOKEN_KEY);
  showApp(false);
});

document.getElementById("inquiry-filter").addEventListener("change", () => {
  listState.inquiries.offset = 0;
  loadDashboard();
});

document.getElementById("client-search-form").addEventListener("submit", (event) => {
  event.preventDefault();
  listState.clients.query = document.getElementById("client-search").value.trim();
  listState.clients.offset = 0;
  loadDashboard();
});

document.getElementById("client-search-reset").addEventListener("click", () => {
  document.getElementById("client-search").value = "";
  listState.clients.query = "";
  listState.clients.offset = 0;
  loadDashboard();
});

document.getElementById("offer-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.currentTarget).entries());
  await api("/offers", {
    method: "POST",
    body: JSON.stringify({ inquiry_id: Number(data.inquiry_id), value: Number(data.value), status: data.status }),
  });
  event.currentTarget.reset();
  loadDashboard();
});

document.addEventListener("click", async (event) => {
  const timelineButton = event.target.closest("[data-client]");
  const exportButton = event.target.closest("[data-export]");
  const anonymizeButton = event.target.closest("[data-anonymize]");
  const pageButton = event.target.closest("[data-page]");
  if (pageButton) {
    const state = listState[pageButton.dataset.page];
    const direction = pageButton.dataset.direction;
    state.offset = direction === "next" ? state.offset + PAGE_LIMIT : Math.max(0, state.offset - PAGE_LIMIT);
    loadDashboard();
  }
  if (timelineButton) {
    const rows = await api(`/clients/${timelineButton.dataset.client}/timeline`);
    document.getElementById("client-timeline").innerHTML = `<h3>Timeline klienta #${escapeHtml(timelineButton.dataset.client)}</h3>` +
      rows.map((item) => `<p><strong>${escapeHtml(new Date(item.timestamp).toLocaleString())}</strong> ${escapeHtml(item.title)}</p>`).join("");
  }
  if (exportButton) {
    const exported = await api(`/clients/${exportButton.dataset.export}/export`);
    document.getElementById("client-timeline").innerHTML = `<h3>Eksport danych klienta #${escapeHtml(exportButton.dataset.export)}</h3><pre>${escapeHtml(JSON.stringify(exported, null, 2))}</pre>`;
  }
  if (anonymizeButton && confirm("Zanonimizować dane klienta?")) {
    await api(`/clients/${anonymizeButton.dataset.anonymize}/anonymize`, { method: "DELETE" });
    loadDashboard();
  }
});

showApp(Boolean(token()));
