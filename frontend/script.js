const API_BASE = ""; // same origin

const logEl = document.getElementById("log");
const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");
const langSelect = document.getElementById("lang-select");
const catList = document.getElementById("cat-list");

// Free hosting (e.g. Render's free tier) puts the server to sleep after
// inactivity. The first request after that can take 30-60s to wake it back
// up, and a plain fetch can fail during that window. This helper retries
// automatically with increasing delays instead of giving up after one try.
async function fetchWithRetry(url, options, { retries = 6, baseDelayMs = 4000, onRetry } = {}) {
  let lastErr;
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const res = await fetch(url, options);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res;
    } catch (err) {
      lastErr = err;
      if (attempt < retries) {
        if (onRetry) onRetry(attempt + 1, retries);
        await new Promise(r => setTimeout(r, baseDelayMs));
      }
    }
  }
  throw lastErr;
}

async function loadMeta() {
  try {
    const res = await fetchWithRetry(`${API_BASE}/api/categories`, undefined, {
      onRetry: (n) => {
        catList.innerHTML = `<li>Waking up the server (free hosting) — retry ${n}… this can take up to a minute on first use.</li>`;
      },
    });
    const data = await res.json();

    catList.innerHTML = "";
    data.categories.forEach(cat => {
      const li = document.createElement("li");
      li.textContent = cat;
      li.addEventListener("click", () => {
        input.value = `Tell me about ${cat.toLowerCase()}`;
        input.focus();
      });
      catList.appendChild(li);
    });

    Object.entries(data.languages).forEach(([code, name]) => {
      const opt = document.createElement("option");
      opt.value = code;
      opt.textContent = name;
      langSelect.appendChild(opt);

    });
  } catch (err) {
    catList.innerHTML = "<li>Could not load topics — is the backend running?</li>";
  }
}

function clearEmptyState() {
  const empty = logEl.querySelector(".empty-state");
  if (empty) empty.remove();
}

function addEntry(who, text, metaHtml) {
  clearEmptyState();
  const entry = document.createElement("div");
  entry.className = `entry ${who}`;

  const whoEl = document.createElement("div");
  whoEl.className = "who";
  whoEl.textContent = who === "user" ? "You" : "Sahayak";

  const bodyEl = document.createElement("div");
  bodyEl.className = "body";
  const p = document.createElement("p");
  p.textContent = text;
  bodyEl.appendChild(p);

  if (metaHtml) {
    const meta = document.createElement("div");
    meta.className = "meta";
    meta.innerHTML = metaHtml;
    bodyEl.appendChild(meta);
  }

  entry.appendChild(whoEl);
  entry.appendChild(bodyEl);
  logEl.appendChild(entry);
  logEl.scrollTop = logEl.scrollHeight;
}

// ---------- Voice input (Speech-to-Text) ----------
const micBtn = document.getElementById("mic-btn");
const speakToggle = document.getElementById("speak-toggle");

// Maps our app language codes to BCP-47 locale tags the Web Speech API expects.
const VOICE_LOCALE = {
  en: "en-IN",
  hi: "hi-IN",
  mr: "mr-IN",
  bn: "bn-IN",
  ta: "ta-IN",
  te: "te-IN",
  gu: "gu-IN",
};

const SpeechRecognitionImpl = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
let listening = false;

if (SpeechRecognitionImpl) {
  recognition = new SpeechRecognitionImpl();
  recognition.continuous = false;
  recognition.interimResults = false;

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    input.value = transcript;
  };

  recognition.onend = () => {
    listening = false;
    micBtn.classList.remove("listening");
  };

  recognition.onerror = () => {
    listening = false;
    micBtn.classList.remove("listening");
  };
} else {
  micBtn.disabled = true;
  micBtn.title = "Voice input is not supported in this browser — try Chrome.";
}

micBtn.addEventListener("click", () => {
  if (!recognition || listening) return;
  const selectedLang = langSelect.value;
  recognition.lang = VOICE_LOCALE[selectedLang] || "en-IN";
  listening = true;
  micBtn.classList.add("listening");
  try {
    recognition.start();
  } catch (err) {
    listening = false;
    micBtn.classList.remove("listening");
  }
});

// ---------- Voice output (Text-to-Speech) ----------
function speak(text, langCode) {
  if (!speakToggle.checked || !("speechSynthesis" in window)) return;
  // Strip the meta line breaks — just read the natural-language reply.
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = VOICE_LOCALE[langCode] || "en-IN";
  window.speechSynthesis.cancel(); // don't queue overlapping replies
  window.speechSynthesis.speak(utterance);
}

// ---------- Grievance filing ----------
const grievancePanel = document.getElementById("grievance-panel");
const openGrievanceBtn = document.getElementById("open-grievance");
const cancelGrievanceBtn = document.getElementById("grievance-cancel");
const submitGrievanceBtn = document.getElementById("grievance-submit");
const grievanceCategorySelect = document.getElementById("grievance-category");
const grievanceDesc = document.getElementById("grievance-desc");
const grievanceContact = document.getElementById("grievance-contact");

async function loadGrievanceCategories() {
  try {
    const res = await fetch(`${API_BASE}/api/grievance/categories`);
    const data = await res.json();
    grievanceCategorySelect.innerHTML = "";
    data.categories.forEach(cat => {
      const opt = document.createElement("option");
      opt.value = cat;
      opt.textContent = cat;
      grievanceCategorySelect.appendChild(opt);
    });
  } catch (err) {
    grievanceCategorySelect.innerHTML = '<option value="Other">Other</option>';
  }
}

openGrievanceBtn.addEventListener("click", () => {
  grievancePanel.classList.add("open");
});

cancelGrievanceBtn.addEventListener("click", () => {
  grievancePanel.classList.remove("open");
});

submitGrievanceBtn.addEventListener("click", async () => {
  const description = grievanceDesc.value.trim();
  if (!description) {
    grievanceDesc.focus();
    return;
  }

  submitGrievanceBtn.disabled = true;
  submitGrievanceBtn.textContent = "Submitting…";

  try {
    const lang = langSelect.value === "auto" ? "en" : langSelect.value;
    const res = await fetch(`${API_BASE}/api/grievance`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        category: grievanceCategorySelect.value,
        description,
        contact: grievanceContact.value.trim() || null,
        lang,
      }),
    });
    const data = await res.json();

    addEntry("bot", data.message, `<span class="tag">Grievance filed</span><span class="tag">${grievanceCategorySelect.value}</span>`);
    speak(data.message, lang);

    grievanceDesc.value = "";
    grievanceContact.value = "";
    grievancePanel.classList.remove("open");
  } catch (err) {
    addEntry("bot", "Sorry — could not file the grievance. Make sure the backend is running and try again.");
  } finally {
    submitGrievanceBtn.disabled = false;
    submitGrievanceBtn.textContent = "Submit";
  }
});

loadGrievanceCategories();

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const message = input.value.trim();
  if (!message) return;

  addEntry("user", message);
  input.value = "";
  sendBtn.disabled = true;
  sendBtn.textContent = "…";

  try {
    const res = await fetchWithRetry(
      `${API_BASE}/api/chat`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, lang: langSelect.value }),
      },
      {
        onRetry: (n) => {
          sendBtn.textContent = `Waking up (${n})…`;
        },
      }
    );
    const data = await res.json();

    const metaBits = [];
    metaBits.push(`<span class="tag">lang: ${data.detected_lang}</span>`);
    if (data.category) metaBits.push(`<span class="tag">${data.category}</span>`);
    metaBits.push(`<span class="tag">match: ${(data.confidence * 100).toFixed(0)}%</span>`);
    if (data.is_machine_translated) metaBits.push(`<span class="tag">machine-translated</span>`);

    addEntry("bot", data.reply, metaBits.join(""));
    speak(data.reply, data.detected_lang);
  } catch (err) {
    addEntry("bot", "Sorry — could not reach the backend. Make sure the FastAPI server is running.");
  } finally {
    sendBtn.disabled = false;
    sendBtn.textContent = "Ask";
  }
});

loadMeta();