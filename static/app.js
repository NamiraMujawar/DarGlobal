// Author: Namira Mujawar | Project date: 2026-11-18
const form = document.querySelector("#chat-form");
const questionInput = document.querySelector("#question");
const messages = document.querySelector("#messages");
const welcome = document.querySelector("#welcome");
const sendButton = document.querySelector("#send-button");
const modelStatus = document.querySelector("#model-status");
const messageTemplate = document.querySelector("#message-template");
const conversationList = document.querySelector("#conversation-list");
let activeConversationId = null;

function setModelStatus(label, mode = "") {
  modelStatus.classList.toggle("is-demo", mode === "demo");
  modelStatus.classList.toggle("is-live", mode === "openrouter");
  const dot = document.createElement("span");
  dot.className = "status-dot";
  modelStatus.replaceChildren(dot, document.createTextNode(label));
}

function renderConversations(conversations) {
  conversationList.replaceChildren();
  if (!conversations.length) {
    const empty = document.createElement("p");
    empty.className = "history-empty";
    empty.textContent = "Your saved conversations will appear here.";
    conversationList.append(empty);
    return;
  }

  for (const conversation of conversations) {
    const item = document.createElement("div");
    item.className = "conversation-item";
    item.classList.toggle("is-active", conversation.id === activeConversationId);

    const open = document.createElement("button");
    open.className = "conversation-open";
    open.type = "button";
    open.textContent = conversation.title || "New conversation";
    open.title = conversation.title || "New conversation";
    open.setAttribute("aria-current", conversation.id === activeConversationId ? "page" : "false");
    open.addEventListener("click", () => {
      selectConversation(conversation.id).catch(() => {
        addMessage("assistant", "I couldn't open that conversation. Please try again.", [], true);
      });
    });

    const remove = document.createElement("button");
    remove.className = "conversation-delete";
    remove.type = "button";
    remove.textContent = "×";
    remove.setAttribute("aria-label", `Delete conversation: ${conversation.title || "New conversation"}`);
    remove.addEventListener("click", (event) => {
      event.stopPropagation();
      deleteConversation(conversation.id).catch(() => {
        addMessage("assistant", "I couldn't delete that conversation. Please try again.", [], true);
      });
    });

    item.append(open, remove);
    conversationList.append(item);
  }
}

async function loadConversations(selectId = null) {
  const response = await fetch("/api/conversations");
  if (!response.ok) throw new Error("Could not load saved conversations.");
  const result = await response.json();
  let items = result.conversations;
  if (!items.length) {
    const created = await fetch("/api/conversations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    if (!created.ok) throw new Error("Could not create a conversation.");
    items = [(await created.json()).conversation];
  }

  const targetId = selectId || (items.some((item) => item.id === activeConversationId)
    ? activeConversationId
    : items[0].id);
  renderConversations(items);
  if (targetId !== activeConversationId || messages.childElementCount === 0) {
    await selectConversation(targetId, items);
  }
}

async function selectConversation(conversationId, knownConversations = null) {
  const response = await fetch(`/api/conversations/${encodeURIComponent(conversationId)}`);
  if (!response.ok) throw new Error("Could not open this conversation.");
  const result = await response.json();
  const conversation = result.conversation;
  activeConversationId = conversation.id;
  messages.replaceChildren();
  for (const message of conversation.messages) {
    addMessage(message.role, message.content, message.sources);
  }
  welcome.hidden = conversation.messages.length > 0;
  questionInput.value = "";
  resizeInput();
  const responseItems = knownConversations || (
    await (await fetch("/api/conversations")).json()
  ).conversations;
  renderConversations(responseItems);
}

async function createConversation() {
  const response = await fetch("/api/conversations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
  if (!response.ok) throw new Error("Could not create a conversation.");
  const conversation = (await response.json()).conversation;
  await loadConversations(conversation.id);
  questionInput.focus();
}

async function deleteConversation(conversationId) {
  if (!window.confirm("Delete this conversation and its saved messages?")) return;
  const response = await fetch(`/api/conversations/${encodeURIComponent(conversationId)}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    addMessage("assistant", "I couldn't delete that conversation. Please try again.", [], true);
    return;
  }
  if (conversationId === activeConversationId) {
    activeConversationId = null;
    messages.replaceChildren();
    welcome.hidden = false;
  }
  await loadConversations();
}

function resizeInput() {
  questionInput.style.height = "auto";
  questionInput.style.height = `${Math.min(questionInput.scrollHeight, 140)}px`;
}

function renderCitations(sourceList, sources) {
  sourceList.replaceChildren();
  for (const source of sources) {
    const link = document.createElement("a");
    link.className = "citation";
    link.href = source.url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    const title = document.createElement("span");
    title.textContent = `${source.source} · ${source.title}`;
    link.append(title);
    sourceList.append(link);
  }
}

function renderAssistantText(element, text) {
  const content = text.replace(/\s*\[S\d+\]/g, "");
  const contactPattern =
    /crm@darglobal\.co\.uk|support@wasalt\.com|https:\/\/darglobal\.co\.uk\/get-in-touch|https:\/\/support\.wasalt\.com\/?/gi;
  const fragment = document.createDocumentFragment();
  let cursor = 0;
  let match;

  while ((match = contactPattern.exec(content)) !== null) {
    fragment.append(document.createTextNode(content.slice(cursor, match.index)));
    const value = match[0];
    const link = document.createElement("a");
    const isEmail = value.includes("@");
    link.href = isEmail ? `mailto:${value.toLowerCase()}` : value;
    if (!isEmail) {
      link.target = "_blank";
      link.rel = "noopener noreferrer";
    }
    link.textContent = value;
    fragment.append(link);
    cursor = contactPattern.lastIndex;
  }

  fragment.append(document.createTextNode(content.slice(cursor)));
  element.replaceChildren(fragment);
}

function setChatBusy(isBusy) {
  sendButton.disabled = isBusy;
  questionInput.disabled = isBusy;
  document.querySelector("#new-chat").disabled = isBusy;
  conversationList.querySelectorAll("button").forEach((button) => {
    button.disabled = isBusy;
  });
}

function addMessage(role, text, sources = [], error = false) {
  const fragment = messageTemplate.content.cloneNode(true);
  const article = fragment.querySelector(".message");
  const avatar = fragment.querySelector(".message-avatar");
  const heading = fragment.querySelector(".message-heading");
  const body = fragment.querySelector(".message-text");
  const sourceList = fragment.querySelector(".message-sources");

  article.classList.toggle("is-user", role === "user");
  article.classList.toggle("is-error", error);
  avatar.textContent = role === "user" ? "G" : "✳";
  heading.textContent = role === "user" ? "YOU" : "ASSISTANT";
  if (role === "assistant") renderAssistantText(body, text);
  else body.textContent = text;

  renderCitations(sourceList, sources);
  messages.append(fragment);
  article.scrollIntoView({ behavior: "smooth", block: "nearest" });
  return article;
}

async function ask(question) {
  if (!activeConversationId) {
    await createConversation();
  }
  welcome.hidden = true;
  addMessage("user", question);
  let loading = addMessage("assistant", "Looking up reliable company information…");
  let streamingMessage = null;
  let completed = false;
  loading.querySelector(".message-text").classList.add("typing");
  setChatBusy(true);
  try {
    const response = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: question,
        conversation_id: activeConversationId,
      }),
    });
    if (!response.ok) {
      let result = {};
      try {
        result = await response.json();
      } catch {
        result.error = "The server returned an invalid response.";
      }
      loading.remove();
      addMessage("assistant", result.error || "The request could not be completed.", [], true);
      return;
    }
    if (!response.body) throw new Error("Streaming is unavailable in this browser.");
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    const handleEvent = (line) => {
      if (!line.startsWith("data:")) return;
      const event = JSON.parse(line.slice(5).trim());
      if (event.type === "delta") {
        if (!streamingMessage) {
          loading.remove();
          streamingMessage = addMessage("assistant", "");
        }
        const body = streamingMessage.querySelector(".message-text");
        body.textContent = body.textContent + event.text.replace(/\s*\[S\d+\]/g, "");
      } else if (event.type === "done") {
        if (!streamingMessage) {
          loading.remove();
          streamingMessage = addMessage("assistant", "");
        }
        const body = streamingMessage.querySelector(".message-text");
        body.classList.remove("typing");
        renderAssistantText(body, event.answer);
        renderCitations(streamingMessage.querySelector(".message-sources"), event.sources);
        setModelStatus(
          event.mode === "openrouter"
            ? "AI connected"
            : event.mode === "local"
              ? "Local answer"
              : "Source preview",
          event.mode,
        );
        completed = true;
      }
    };
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
      const frames = buffer.split("\n\n");
      buffer = frames.pop() || "";
      for (const frame of frames) {
        for (const line of frame.split("\n")) handleEvent(line);
      }
      if (done) break;
    }
    if (buffer.trim()) {
      for (const line of buffer.split("\n")) handleEvent(line);
    }
    if (!completed) throw new Error("The chat stream ended before the answer was complete.");
    await loadConversations(activeConversationId);
  } catch {
    if (loading.isConnected) loading.remove();
    if (streamingMessage && !completed) streamingMessage.remove();
    addMessage("assistant", "I couldn't reach the chat service. Check that the Python app is running, then try again.", [], true);
  } finally {
    setChatBusy(false);
    questionInput.focus();
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const question = questionInput.value.trim();
  if (!question || sendButton.disabled) return;
  questionInput.value = "";
  resizeInput();
  ask(question);
});

questionInput.addEventListener("input", resizeInput);
questionInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

for (const button of document.querySelectorAll("[data-prompt]")) {
  button.addEventListener("click", () => {
    questionInput.value = button.dataset.prompt;
    form.requestSubmit();
  });
}

document.querySelector("#new-chat").addEventListener("click", () => {
  createConversation().catch(() => {
    addMessage("assistant", "I couldn't start a new conversation. Please try again.", [], true);
  });
});

async function loadHealth() {
  try {
    const healthResponse = await fetch("/api/health");
    if (!healthResponse.ok) throw new Error("Status unavailable");
    const health = await healthResponse.json();
    const configured = health.model_configured;
    setModelStatus(configured ? "AI ready" : "Assistant ready", configured ? "openrouter" : "demo");
  } catch {
    setModelStatus("Reconnecting");
  }
}

loadHealth();
loadConversations().catch(() => {
  setModelStatus("History unavailable");
  addMessage("assistant", "Saved chat history is unavailable. Refresh the page or check the app server.", [], true);
});
