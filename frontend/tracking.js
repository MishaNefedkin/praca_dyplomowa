const API_BASE = window.location.origin;
const SESSION_KEY = "bw_session_id";

function uuid() {
  if (crypto.randomUUID) return crypto.randomUUID();
  return `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function getSessionId() {
  let sessionId = localStorage.getItem(SESSION_KEY);
  if (!sessionId) {
    sessionId = uuid();
    localStorage.setItem(SESSION_KEY, sessionId);
  }
  return sessionId;
}

async function track(eventType, eventData = {}, timeOnPage = null) {
  try {
    await fetch(`${API_BASE}/tracking/event`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: getSessionId(),
        page_url: window.location.pathname + window.location.hash,
        event_type: eventType,
        event_data: eventData,
        referrer: document.referrer || null,
        time_on_page: timeOnPage,
      }),
    });
  } catch (error) {
    console.warn("Tracking failed", error);
  }
}

const pageStartedAt = Date.now();
track("page_view", { title: document.title });

window.addEventListener("beforeunload", () => {
  const timeOnPage = Math.round((Date.now() - pageStartedAt) / 1000);
  navigator.sendBeacon?.(
    `${API_BASE}/tracking/event`,
    new Blob([
      JSON.stringify({
        session_id: getSessionId(),
        page_url: window.location.pathname + window.location.hash,
        event_type: "page_leave",
        event_data: { title: document.title },
        referrer: document.referrer || null,
        time_on_page: timeOnPage,
      }),
    ], { type: "application/json" }),
  );
});

document.addEventListener("click", (event) => {
  const cta = event.target.closest(".cta-track");
  if (cta) track("cta_click", { cta: cta.dataset.cta || cta.textContent.trim() });
});

document.querySelectorAll("input, textarea").forEach((field) => {
  field.addEventListener("focus", () => track("form_interaction", { field: field.name, action: "focus" }), { once: true });
});

document.getElementById("contact-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const status = document.getElementById("contact-status");
  const data = Object.fromEntries(new FormData(form).entries());
  status.textContent = "Wysyłanie...";

  try {
    const response = await fetch(`${API_BASE}/inquiries`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: data.name,
        email: data.email,
        phone: data.phone || null,
        message: data.message,
        session_id: getSessionId(),
        consent_scope: "contact_and_analytics",
      }),
    });
    if (!response.ok) throw new Error("Nie udało się wysłać formularza");
    form.reset();
    status.textContent = "Dziękujemy. Zapytanie zostało zapisane w systemie.";
    track("form_submit", { result: "success" });
  } catch (error) {
    status.textContent = error.message;
    track("form_submit", { result: "error", message: error.message });
  }
});
