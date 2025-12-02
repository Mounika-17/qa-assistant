const messagesDiv = document.getElementById("messages");
const statusDiv = document.getElementById("status");
const inputEl = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-button");

let messages = [];

function cleanMarkdown(md) {
  if (!md) return "";
  let s = md.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  s = s.trim();
  s = s.replace(/\n{3,}/g, "\n\n");
  return s;
}

/**
 * Render markdown into a sanitized HTML string.
 * If marked() produces a single <p> wrapper, unwrap it (use innerHTML of the <p>)
 * to avoid extra paragraph spacing.
 */
function renderSanitizedMarkdown(md) {
  const cleaned = cleanMarkdown(md || "");
  const rawHtml = marked.parse(cleaned);

  // Use a temporary DOM node to inspect and possibly unwrap
  const tmp = document.createElement("div");
  tmp.innerHTML = rawHtml.trim();

  // if there is exactly one element and it's a <p>, unwrap it
  if (tmp.childElementCount === 1 && tmp.firstElementChild.tagName.toLowerCase() === "p") {
    tmp.innerHTML = tmp.firstElementChild.innerHTML;
  }

  // Sanitize final HTML
  const safe = DOMPurify.sanitize(tmp.innerHTML, { USE_PROFILES: { html: true } });
  return safe;
}

function addMessage(role, content) {
  const row = document.createElement("div");
  row.classList.add("message-row", role === "user" ? "user" : "assistant");

  const bubble = document.createElement("div");
  bubble.classList.add("message", role === "user" ? "user" : "assistant");

  const contentDiv = document.createElement("div");
  contentDiv.classList.add("content");

  try {
    const safeHtml = renderSanitizedMarkdown(content || "");
    contentDiv.innerHTML = safeHtml;
  } catch (e) {
    contentDiv.textContent = content;
  }

  bubble.appendChild(contentDiv);
  row.appendChild(bubble);
  messagesDiv.appendChild(row);

  // scroll
  messagesDiv.scrollTo({ top: messagesDiv.scrollHeight, behavior: "smooth" });

  // highlight
  try { if (window.hljs) window.hljs.highlightAll(); } catch (e) {}
}

async function sendMessage() {
  const text = inputEl.value.trim();
  if (!text) return;

  addMessage("user", text);
  messages.push({ role: "user", content: text });

  inputEl.value = "";
  inputEl.focus();

  sendBtn.disabled = true;
  statusDiv.textContent = "Thinking...";

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      const msg = err.error || `Error: ${response.status}`;
      addMessage("assistant", msg);
      statusDiv.textContent = "";
      sendBtn.disabled = false;
      return;
    }

    const data = await response.json();
    const reply = data.reply || "";

    addMessage("assistant", reply);
    messages.push({ role: "assistant", content: reply });

    statusDiv.textContent = "";
  } catch (err) {
    console.error(err);
    addMessage("assistant", "Error connecting to server. Please try again.");
    statusDiv.textContent = "";
  } finally {
    sendBtn.disabled = false;
  }
}

sendBtn.addEventListener("click", sendMessage);
inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});
