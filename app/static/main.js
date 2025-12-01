const messagesDiv = document.getElementById("messages");
const statusDiv = document.getElementById("status");
const inputEl = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-button");

let messages = [];

// Add a message bubble to the UI
function addMessage(role, content) {
  const div = document.createElement("div");
  div.classList.add("message");
  div.classList.add(role === "user" ? "user" : "assistant");
  div.textContent = content;
  messagesDiv.appendChild(div);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

async function sendMessage() {
  const text = inputEl.value.trim();
  if (!text) return;

  // Add user message to UI + history
  addMessage("user", text);
  messages.push({ role: "user", content: text });

  inputEl.value = "";
  inputEl.focus();

  sendBtn.disabled = true;
  statusDiv.textContent = "Thinking...";

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ messages }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const msg = errorData.error || `Error: ${response.status}`;
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

// Button click
sendBtn.addEventListener("click", sendMessage);

// Enter key
inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});
