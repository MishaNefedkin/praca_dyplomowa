const API_BASE = window.location.origin;
const SESSION_KEY = "bw_session_id";
let memorySessionId = null;

function uuid() {
  if (window.crypto?.randomUUID) return window.crypto.randomUUID();
  return `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function getSessionId() {
  try {
    let sessionId = localStorage.getItem(SESSION_KEY);
    if (!sessionId) {
      sessionId = uuid();
      localStorage.setItem(SESSION_KEY, sessionId);
    }
    return sessionId;
  } catch (error) {
    if (!memorySessionId) {
      memorySessionId = uuid();
    }
    return memorySessionId;
  }
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
const PHONE_ALLOWED_PATTERN = /^[0-9+()\s-]*$/;
const PHONE_DISALLOWED_PATTERN = /[^0-9+()\s-]/g;
const MIN_PHONE_DIGITS = 6;
const PHONE_ERROR_MESSAGE = "Numer telefonu może zawierać tylko cyfry, spacje, +, -, nawiasy i co najmniej 6 cyfr.";

function sanitizePhone(value) {
  return String(value || "").replace(PHONE_DISALLOWED_PATTERN, "");
}

function phoneDigitCount(value) {
  return sanitizePhone(value).replace(/\D/g, "").length;
}

function validatePhoneField(field) {
  field.value = sanitizePhone(field.value);
  const isValid = !field.value || phoneDigitCount(field.value) >= MIN_PHONE_DIGITS;
  field.setCustomValidity(isValid ? "" : PHONE_ERROR_MESSAGE);
  return isValid;
}

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

document.querySelectorAll('input[name="phone"]').forEach((field) => {
  field.addEventListener("beforeinput", (event) => {
    if (event.data && !PHONE_ALLOWED_PATTERN.test(event.data)) {
      event.preventDefault();
    }
  });
  field.addEventListener("paste", (event) => {
    const pasted = event.clipboardData?.getData("text") || "";
    if (pasted && !PHONE_ALLOWED_PATTERN.test(pasted)) {
      event.preventDefault();
      const start = field.selectionStart ?? field.value.length;
      const end = field.selectionEnd ?? field.value.length;
      field.setRangeText(sanitizePhone(pasted), start, end, "end");
      validatePhoneField(field);
    }
  });
  field.addEventListener("input", () => {
    validatePhoneField(field);
  });
  field.addEventListener("blur", () => validatePhoneField(field));
});

document.getElementById("contact-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const status = document.getElementById("contact-status");
  const data = Object.fromEntries(new FormData(form).entries());
  const phoneField = form.querySelector('input[name="phone"]');
  if (phoneField && !validatePhoneField(phoneField)) {
    status.textContent = PHONE_ERROR_MESSAGE;
    phoneField.reportValidity();
    return;
  }
  if (!form.reportValidity()) {
    return;
  }
  data.phone = phoneField?.value || data.phone;
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
        consent_granted: data.consent === "on",
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
