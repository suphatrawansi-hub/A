const conversation = document.querySelector("#conversation");
const messages = document.querySelector("#messages");
const welcome = document.querySelector("#welcome");
const form = document.querySelector("#chat-form");
const input = document.querySelector("#message-input");
const sendButton = document.querySelector("#send-button");
const resetButton = document.querySelector("#reset-button");
const statusText = document.querySelector("#status-text");
const statusIndicator = document.querySelector("#status-indicator");
const connectionLabel = document.querySelector("#connection-label");

function addMessage(role, text, pending = false) {
  welcome.hidden = true;
  const article = document.createElement("article");
  article.className = `message message-${role}${pending ? " message-pending" : ""}`;

  if (role === "assistant") {
    const avatar = document.createElement("span");
    avatar.className = "message-avatar";
    avatar.textContent = "E";
    avatar.setAttribute("aria-hidden", "true");
    article.append(avatar);
  }

  const body = document.createElement("div");
  body.className = "message-body";
  const label = document.createElement("span");
  label.className = "message-label";
  label.textContent = role === "user" ? "คุณ" : "เอรุ";
  const content = document.createElement("p");
  content.className = "message-text";
  content.textContent = text;
  body.append(label, content);
  article.append(body);
  messages.append(article);
  conversation.scrollTop = conversation.scrollHeight;
  return article;
}

async function loadStatus() {
  try {
    const response = await fetch("/api/status");
    const data = await response.json();
    const label = data.configured ? "พร้อมคุย" : "รอตั้งค่า API key";
    statusText.textContent = label;
    connectionLabel.textContent = label;
    statusIndicator.classList.toggle("status-offline", !data.configured);
  } catch {
    statusText.textContent = "เชื่อมต่อไม่ได้";
    connectionLabel.textContent = "ออฟไลน์";
    statusIndicator.classList.add("status-offline");
  }
}

async function loadHistory() {
  try {
    const response = await fetch("/api/history");
    const data = await response.json();
    data.messages.forEach((message) => addMessage(message.role, message.text));
  } catch {
    addMessage("assistant", "โหลดบทสนทนาไม่สำเร็จ ลองรีเฟรชหน้าอีกทีนะ");
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message || sendButton.disabled) return;

  addMessage("user", message);
  input.value = "";
  input.style.height = "auto";
  sendButton.disabled = true;
  const pending = addMessage("assistant", "เอรุกำลังคิดอยู่...", true);

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    const data = await response.json();
    pending.remove();
    addMessage("assistant", response.ok ? data.reply : data.error);
  } catch {
    pending.remove();
    addMessage("assistant", "เชื่อมต่อไม่สำเร็จ ลองส่งใหม่อีกทีนะ");
  } finally {
    sendButton.disabled = false;
    input.focus();
  }
});

input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 160)}px`;
});

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

document.querySelectorAll(".suggestion").forEach((button) => {
  button.addEventListener("click", () => {
    input.value = button.textContent;
    form.requestSubmit();
  });
});

resetButton.addEventListener("click", async () => {
  if (!window.confirm("เริ่มบทสนทนาใหม่ไหม? ประวัติรอบนี้จะถูกล้าง")) return;
  await fetch("/api/reset", { method: "POST" });
  messages.replaceChildren();
  welcome.hidden = false;
  input.focus();
});

Promise.all([loadStatus(), loadHistory()]);