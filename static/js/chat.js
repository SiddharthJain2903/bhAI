document.addEventListener("DOMContentLoaded", () => {
    const messagesContainer = document.getElementById("messagesContainer");
    const messageForm = document.getElementById("messageForm");
    const messageInput = document.getElementById("messageInput");
    const chatWindow = document.getElementById("chatWindow");
    const newChatBtn = document.getElementById("newChatBtn");
    const startChatBtn = document.getElementById("startChatBtn");

    // Auto-dismiss flash messages
    const flashContainer = document.getElementById("flashContainer");
    if (flashContainer) {
        setTimeout(() => { flashContainer.style.display = "none"; }, 4000);
    }

    function scrollToBottom() {
        if (messagesContainer) messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    scrollToBottom();

    function appendMessage(role, text) {
        const div = document.createElement("div");
        div.className = `message ${role}`;
        const bubble = document.createElement("div");
        bubble.className = "bubble";
        bubble.textContent = text;
        div.appendChild(bubble);
        messagesContainer.appendChild(div);
        scrollToBottom();
        return div;
    }

    function appendImageMessage(role, url) {
        const div = document.createElement("div");
        div.className = `message ${role}`;
        const bubble = document.createElement("div");
        bubble.className = "bubble image-bubble";
        const img = document.createElement("img");
        img.src = url;
        img.alt = "Generated image";
        img.className = "chat-image";
        bubble.appendChild(img);
        div.appendChild(bubble);
        messagesContainer.appendChild(div);
        scrollToBottom();
        return div;
    }

    function looksLikeImageRequest(text) {
        return /^\/image\s+/i.test(text.trim()) ||
               /\b(generate|create|draw|make|design)\b[^.]{0,20}\b(image|picture|photo|drawing|art|illustration)\b/i.test(text);
    }

    function showTyping(isImage = false) {
        const div = document.createElement("div");
        div.className = "message assistant typing";
        div.id = "typingIndicator";
        const label = isImage
            ? '<span class="typing-label">Generating image (can take up to 30s)…</span>'
            : "";
        div.innerHTML = `<div class="bubble">
            ${label}
            <span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>
        </div>`;
        messagesContainer.appendChild(div);
        scrollToBottom();
    }

    function hideTyping() {
        const el = document.getElementById("typingIndicator");
        if (el) el.remove();
    }

    // ---- Send message ----
    if (messageForm) {
        messageForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const text = messageInput.value.trim();
            if (!text) return;

            const chatId = chatWindow.dataset.chatId;
            const isImageRequest = looksLikeImageRequest(text);
            appendMessage("user", text);
            messageInput.value = "";
            showTyping(isImageRequest);

            try {
                const res = await fetch(`/chat/${chatId}/send`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ message: text }),
                });
                const data = await res.json();
                hideTyping();

                if (data.type === "image" && data.image_url) {
                    appendImageMessage("assistant", data.image_url);
                } else if (data.reply) {
                    appendMessage("assistant", data.reply);
                }
                if (data.chat_title) {
                    const link = document.querySelector(`.chat-history-item[data-chat-id="${chatId}"] .chat-item-title`);
                    if (link) link.textContent = data.chat_title;
                }
            } catch (err) {
                hideTyping();
                appendMessage("assistant", "⚠️ Network error — please try again.");
            }
        });
    }

    // ---- New chat ----
    async function createNewChat() {
        const res = await fetch("/chat/new", { method: "POST" });
        const data = await res.json();
        window.location.href = `/chat/${data.chat_id}`;
    }
    if (newChatBtn) newChatBtn.addEventListener("click", createNewChat);
    if (startChatBtn) startChatBtn.addEventListener("click", createNewChat);

    // ---- Delete chat ----
    document.querySelectorAll(".delete-chat-btn").forEach((btn) => {
        btn.addEventListener("click", async (e) => {
            e.preventDefault();
            e.stopPropagation();
            const chatId = btn.dataset.chatId;
            if (!confirm("Delete this chat? This can't be undone.")) return;

            await fetch(`/chat/${chatId}/delete`, { method: "POST" });

            const isActive = chatWindow && chatWindow.dataset.chatId === chatId;
            if (isActive) {
                window.location.href = "/";
            } else {
                btn.closest(".chat-history-item").remove();
            }
        });
    });
});
