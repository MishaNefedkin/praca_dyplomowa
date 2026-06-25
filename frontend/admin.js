const API_BASE = window.location.origin;
const TOKEN_KEY = "bw_admin_token";
const PAGE_LIMIT = 25;
const listState = {
  clients: { offset: 0, query: "" },
  inquiries: { offset: 0 },
  offers: { offset: 0 },
  activity: { offset: 0 },
  audit: { offset: 0 },
  users: { offset: 0 },
};
let currentUser = null;

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

function formatStatus(value) {
  const labels = {
    new: "Nowe",
    in_progress: "W trakcie",
    offer_sent: "Oferta wysłana",
    closed: "Zamknięte",
    draft: "Szkic",
    sent: "Wysłana",
    accepted: "Zaakceptowana",
    rejected: "Odrzucona",
  };
  return labels[value] || value;
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
    const apiError = new Error(error.detail || "Request failed");
    apiError.status = response.status;
    throw apiError;
  }
  return response.json();
}

async function optionalApi(path, fallback) {
  try {
    return await api(path);
  } catch (error) {
    if (error.status === 403) return fallback;
    throw error;
  }
}

function hasRole(...roles) {
  return currentUser && roles.includes(currentUser.role);
}

function setElementHidden(id, hidden) {
  document.getElementById(id).classList.toggle("hidden", hidden);
}

function setNavLinkHidden(hash, hidden) {
  const link = document.querySelector(`.sidebar a[href="${hash}"]`);
  if (link) link.classList.toggle("hidden", hidden);
}

function applyRoleUi() {
  const canReadAnalytics = hasRole("admin", "manager");
  const canReadProtectedLogs = hasRole("admin", "manager");
  const canWriteCrm = hasRole("admin", "sales");
  const canWriteOffers = hasRole("admin", "sales");
  const canManageUsers = hasRole("admin");

  setElementHidden("dashboard", !canReadAnalytics);
  setElementHidden("activity", !canReadProtectedLogs);
  setElementHidden("audit", !canReadProtectedLogs);
  setElementHidden("client-form", !canWriteCrm);
  setElementHidden("inquiry-form", !canWriteCrm);
  setElementHidden("offer-form", !canWriteOffers);
  setElementHidden("users", !canManageUsers);
  setNavLinkHidden("#dashboard", !canReadAnalytics);
  setNavLinkHidden("#activity", !canReadProtectedLogs);
  setNavLinkHidden("#audit", !canReadProtectedLogs);
  setNavLinkHidden("#users", !canManageUsers);
}

async function loadCurrentUser() {
  currentUser = await api("/auth/me");
  applyRoleUi();
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

function setStatus(message) {
  document.getElementById("admin-status").textContent = message;
}

function renderActionError(error) {
  setStatus(`Operacja nie powiodła się: ${error.message}`);
}

function statusSelect(type, id, currentValue, values) {
  const options = values
    .map((value) => `<option value="${escapeHtml(value)}" ${value === currentValue ? "selected" : ""}>${escapeHtml(formatStatus(value))}</option>`)
    .join("");
  return `<select class="status-select" data-status-type="${escapeHtml(type)}" data-status-id="${escapeHtml(id)}">${options}</select>`;
}

async function showApp(isLoggedIn) {
  document.getElementById("login-panel").classList.toggle("hidden", isLoggedIn);
  document.getElementById("admin-content").classList.toggle("hidden", !isLoggedIn);
  if (isLoggedIn) {
    try {
      await loadCurrentUser();
      loadDashboard();
    } catch (error) {
      localStorage.removeItem(TOKEN_KEY);
      currentUser = null;
      showApp(false);
    }
  }
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
  let auditLogs;
  let users;

  try {
    [kpi, topPages, alerts, clients, inquiries, offers, logs, auditLogs, users] = await Promise.all([
      hasRole("admin", "manager") ? optionalApi("/analytics/kpi", null) : Promise.resolve(null),
      hasRole("admin", "manager") ? optionalApi("/analytics/top-pages", []) : Promise.resolve([]),
      hasRole("admin", "manager") ? optionalApi("/analytics/alerts", []) : Promise.resolve([]),
      api(buildListPath("/clients", { limit: PAGE_LIMIT, offset: listState.clients.offset, q: listState.clients.query })),
      api(buildListPath("/inquiries", { limit: PAGE_LIMIT, offset: listState.inquiries.offset, status: document.getElementById("inquiry-filter").value })),
      api(buildListPath("/offers", { limit: PAGE_LIMIT, offset: listState.offers.offset })),
      hasRole("admin", "manager") ? optionalApi(buildListPath("/tracking/logs", { limit: PAGE_LIMIT, offset: listState.activity.offset }), []) : Promise.resolve([]),
      hasRole("admin", "manager") ? optionalApi(buildListPath("/audit/logs", { limit: PAGE_LIMIT, offset: listState.audit.offset }), []) : Promise.resolve([]),
      hasRole("admin") ? optionalApi("/auth/users", []) : Promise.resolve([]),
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

  if (kpi) {
    document.getElementById("kpi-grid").innerHTML = [
      ["Klienci", kpi.clients_count],
      ["Nowe zapytania", kpi.new_inquiries_count],
      ["Wysłane oferty", kpi.sent_offers_count],
      ["Konwersja", `${kpi.inquiry_to_offer_conversion_rate}%`],
      ["Aktywność 24h", kpi.activities_last_24h],
    ].map(([label, value]) => `<article class="metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></article>`).join("");

    document.getElementById("top-pages").innerHTML = topPages.map((page) => `<p><strong>${escapeHtml(page.visits)}</strong> ${escapeHtml(page.page_url)}</p>`).join("") || "<p class='muted'>Brak wizyt.</p>";
    document.getElementById("alerts").innerHTML = alerts.map((alert) => `<p>${escapeHtml(alert.message)}</p>`).join("") || "<p class='muted'>Brak alertów.</p>";
  }

  const clientActions = (row) => {
    const actions = [`<button data-client="${row.id}" class="link-button">Timeline</button>`];
    if (hasRole("admin", "manager")) {
      actions.push(`<button data-export="${row.id}" class="link-button">Eksport</button>`);
    }
    if (hasRole("admin")) {
      actions.push(`<button data-anonymize="${row.id}" class="link-button danger">Anonimizuj</button>`);
    }
    return actions.join(" ");
  };

  document.getElementById("clients-table").innerHTML = table(
    clients,
    [
      { key: "id", label: "ID" },
      { key: "name", label: "Nazwa" },
      { key: "email", label: "Email" },
      { key: "phone", label: "Telefon" },
      { key: "created_at", label: "Utworzono", render: (row) => new Date(row.created_at).toLocaleString() },
    ],
    clientActions,
  );
  renderPager("clients-pager", "clients", clients);

  document.getElementById("inquiries-table").innerHTML = table(
    inquiries,
    [
      { key: "id", label: "ID" },
      { key: "client_id", label: "Klient" },
      { key: "status", label: "Status", render: (row) => formatStatus(row.status) },
      { key: "message", label: "Wiadomość" },
      { key: "created_at", label: "Data", render: (row) => new Date(row.created_at).toLocaleString() },
    ],
    hasRole("admin", "sales") ? (row) => statusSelect("inquiry", row.id, row.status, ["new", "in_progress", "offer_sent", "closed"]) : null,
  );
  renderPager("inquiries-pager", "inquiries", inquiries);

  document.getElementById("offers-table").innerHTML = table(
    offers,
    [
      { key: "id", label: "ID" },
      { key: "inquiry_id", label: "Zapytanie" },
      { key: "value", label: "Wartość" },
      { key: "status", label: "Status", render: (row) => formatStatus(row.status) },
      { key: "created_at", label: "Data", render: (row) => new Date(row.created_at).toLocaleString() },
    ],
    hasRole("admin", "sales") ? (row) => statusSelect("offer", row.id, row.status, ["draft", "sent", "accepted", "rejected"]) : null,
  );
  renderPager("offers-pager", "offers", offers);

  if (hasRole("admin")) {
    document.getElementById("users-table").innerHTML = table(users, [
      { key: "id", label: "ID" },
      { key: "login", label: "Login" },
      { key: "role", label: "Rola" },
      { key: "created_at", label: "Utworzono", render: (row) => new Date(row.created_at).toLocaleString() },
    ]);
  }

  if (hasRole("admin", "manager")) {
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

    document.getElementById("audit-table").innerHTML = table(auditLogs, [
      { key: "id", label: "ID" },
      { key: "actor_login", label: "Użytkownik" },
      { key: "action", label: "Akcja" },
      { key: "entity_type", label: "Obiekt" },
      { key: "entity_id", label: "ID obiektu" },
      { key: "created_at", label: "Data", render: (row) => new Date(row.created_at).toLocaleString() },
    ]);
    renderPager("audit-pager", "audit", auditLogs);
  }
}

document.getElementById("login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.currentTarget).entries());
  const status = document.getElementById("login-status");
  try {
    const result = await api("/auth/login", { method: "POST", body: JSON.stringify(data) });
    localStorage.setItem(TOKEN_KEY, result.access_token);
    status.textContent = "";
    await showApp(true);
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
  const query = document.getElementById("client-search").value.trim();
  if (query.length === 1) {
    setStatus("Wpisz co najmniej 2 znaki, aby wyszukać klienta.");
    return;
  }
  listState.clients.query = query;
  listState.clients.offset = 0;
  loadDashboard();
});

document.getElementById("client-search-reset").addEventListener("click", () => {
  document.getElementById("client-search").value = "";
  listState.clients.query = "";
  listState.clients.offset = 0;
  loadDashboard();
});

document.getElementById("client-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.currentTarget).entries());
  try {
    await api("/clients", {
      method: "POST",
      body: JSON.stringify({
        name: data.name.trim(),
        email: data.email.trim(),
        phone: data.phone.trim() || null,
      }),
    });
    event.currentTarget.reset();
    listState.clients.offset = 0;
    setStatus("Klient został dodany.");
    loadDashboard();
  } catch (error) {
    renderActionError(error);
  }
});

document.getElementById("inquiry-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.currentTarget).entries());
  try {
    await api("/inquiries/admin", {
      method: "POST",
      body: JSON.stringify({
        client_id: Number(data.client_id),
        message: data.message.trim(),
        status: data.status,
      }),
    });
    event.currentTarget.reset();
    listState.inquiries.offset = 0;
    setStatus("Zapytanie zostało dodane.");
    loadDashboard();
  } catch (error) {
    renderActionError(error);
  }
});

document.getElementById("offer-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.currentTarget).entries());
  try {
    await api("/offers", {
      method: "POST",
      body: JSON.stringify({ inquiry_id: Number(data.inquiry_id), value: Number(data.value), status: data.status }),
    });
    event.currentTarget.reset();
    setStatus("");
    loadDashboard();
  } catch (error) {
    renderActionError(error);
  }
});

document.getElementById("user-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.currentTarget).entries());
  try {
    await api("/auth/users", {
      method: "POST",
      body: JSON.stringify({
        login: data.login.trim(),
        password: data.password,
        role: data.role,
      }),
    });
    event.currentTarget.reset();
    setStatus("Użytkownik został dodany.");
    loadDashboard();
  } catch (error) {
    renderActionError(error);
  }
});

document.addEventListener("change", async (event) => {
  const control = event.target.closest("[data-status-type]");
  if (!control) return;

  const endpoint = control.dataset.statusType === "inquiry" ? `/inquiries/${control.dataset.statusId}` : `/offers/${control.dataset.statusId}`;
  try {
    await api(endpoint, { method: "PUT", body: JSON.stringify({ status: control.value }) });
    setStatus("Status został zaktualizowany.");
    loadDashboard();
  } catch (error) {
    renderActionError(error);
    loadDashboard();
  }
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
    try {
      const rows = await api(`/clients/${timelineButton.dataset.client}/timeline`);
      document.getElementById("client-timeline").innerHTML = `<h3>Timeline klienta #${escapeHtml(timelineButton.dataset.client)}</h3>` +
        rows.map((item) => `<p><strong>${escapeHtml(new Date(item.timestamp).toLocaleString())}</strong> ${escapeHtml(item.title)}</p>`).join("");
      setStatus("");
    } catch (error) {
      renderActionError(error);
    }
  }
  if (exportButton) {
    try {
      const exported = await api(`/clients/${exportButton.dataset.export}/export`);
      document.getElementById("client-timeline").innerHTML = `<h3>Eksport danych klienta #${escapeHtml(exportButton.dataset.export)}</h3><pre>${escapeHtml(JSON.stringify(exported, null, 2))}</pre>`;
      setStatus("");
      loadDashboard();
    } catch (error) {
      renderActionError(error);
    }
  }
  if (anonymizeButton && confirm("Zanonimizować dane klienta?")) {
    try {
      await api(`/clients/${anonymizeButton.dataset.anonymize}/anonymize`, { method: "DELETE" });
      setStatus("");
      loadDashboard();
    } catch (error) {
      renderActionError(error);
    }
  }
});

showApp(Boolean(token()));
