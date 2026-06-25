const API_BASE = window.location.origin;
const TOKEN_KEY = "bw_admin_token";

function token() {
  return localStorage.getItem(TOKEN_KEY);
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
  const head = columns.map((column) => `<th>${column.label}</th>`).join("") + (actions ? "<th>Akcje</th>" : "");
  const body = rows
    .map((row) => {
      const cells = columns.map((column) => `<td>${column.render ? column.render(row) : row[column.key] ?? ""}</td>`).join("");
      return `<tr>${cells}${actions ? `<td>${actions(row)}</td>` : ""}</tr>`;
    })
    .join("");
  return `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

function showApp(isLoggedIn) {
  document.getElementById("login-panel").classList.toggle("hidden", isLoggedIn);
  document.getElementById("admin-content").classList.toggle("hidden", !isLoggedIn);
  if (isLoggedIn) loadDashboard();
}

async function loadDashboard() {
  const [kpi, topPages, alerts, clients, inquiries, offers, logs] = await Promise.all([
    api("/analytics/kpi"),
    api("/analytics/top-pages"),
    api("/analytics/alerts"),
    api("/clients"),
    api(`/inquiries${document.getElementById("inquiry-filter").value ? `?status=${document.getElementById("inquiry-filter").value}` : ""}`),
    api("/offers"),
    api("/tracking/logs"),
  ]);

  document.getElementById("kpi-grid").innerHTML = [
    ["Klienci", kpi.clients_count],
    ["Nowe zapytania", kpi.new_inquiries_count],
    ["Wysłane oferty", kpi.sent_offers_count],
    ["Konwersja", `${kpi.inquiry_to_offer_conversion_rate}%`],
    ["Aktywność 24h", kpi.activities_last_24h],
  ].map(([label, value]) => `<article class="metric"><span>${label}</span><strong>${value}</strong></article>`).join("");

  document.getElementById("top-pages").innerHTML = topPages.map((page) => `<p><strong>${page.visits}</strong> ${page.page_url}</p>`).join("") || "<p class='muted'>Brak wizyt.</p>";
  document.getElementById("alerts").innerHTML = alerts.map((alert) => `<p>${alert.message}</p>`).join("") || "<p class='muted'>Brak alertów.</p>";

  document.getElementById("clients-table").innerHTML = table(
    clients,
    [
      { key: "id", label: "ID" },
      { key: "name", label: "Nazwa" },
      { key: "email", label: "Email" },
      { key: "phone", label: "Telefon" },
      { key: "created_at", label: "Utworzono", render: (row) => new Date(row.created_at).toLocaleString() },
    ],
    (row) => `<button data-client="${row.id}" class="link-button">Timeline</button> <button data-anonymize="${row.id}" class="link-button danger">Anonimizuj</button>`,
  );

  document.getElementById("inquiries-table").innerHTML = table(inquiries, [
    { key: "id", label: "ID" },
    { key: "client_id", label: "Klient" },
    { key: "status", label: "Status" },
    { key: "message", label: "Wiadomość" },
    { key: "created_at", label: "Data", render: (row) => new Date(row.created_at).toLocaleString() },
  ]);

  document.getElementById("offers-table").innerHTML = table(offers, [
    { key: "id", label: "ID" },
    { key: "inquiry_id", label: "Zapytanie" },
    { key: "value", label: "Wartość" },
    { key: "status", label: "Status" },
    { key: "created_at", label: "Data", render: (row) => new Date(row.created_at).toLocaleString() },
  ]);

  document.getElementById("activity-table").innerHTML = table(logs, [
    { key: "id", label: "ID" },
    { key: "client_id", label: "Klient" },
    { key: "session_id", label: "Sesja" },
    { key: "page_url", label: "Strona" },
    { key: "event_type", label: "Typ" },
    { key: "time_on_page", label: "Czas" },
    { key: "logged_at", label: "Data", render: (row) => new Date(row.logged_at).toLocaleString() },
  ]);
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

document.getElementById("inquiry-filter").addEventListener("change", loadDashboard);

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
  const anonymizeButton = event.target.closest("[data-anonymize]");
  if (timelineButton) {
    const rows = await api(`/clients/${timelineButton.dataset.client}/timeline`);
    document.getElementById("client-timeline").innerHTML = `<h3>Timeline klienta #${timelineButton.dataset.client}</h3>` +
      rows.map((item) => `<p><strong>${new Date(item.timestamp).toLocaleString()}</strong> ${item.title}</p>`).join("");
  }
  if (anonymizeButton && confirm("Zanonimizować dane klienta?")) {
    await api(`/clients/${anonymizeButton.dataset.anonymize}/anonymize`, { method: "DELETE" });
    loadDashboard();
  }
});

showApp(Boolean(token()));
