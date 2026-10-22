document.addEventListener("DOMContentLoaded", () => {
    const messagesContainer = document.getElementById("messagesContainer");
    const messageForm = document.getElementById("messageForm");
    const messageInput = document.getElementById("messageInput");
    const chatWindow = document.getElementById("chatWindow");
    const newChatBtn = document.getElementById("newChatBtn");
    const startChatBtn = document.getElementById("startChatBtn");
    const fileInput = document.getElementById("fileInput");
    const attachBtn = document.getElementById("attachBtn");
    const pendingAttachmentEl = document.getElementById("pendingAttachment");

    let pendingFile = null;

    // Auto-dismiss flash messages
    const flashContainer = document.getElementById("flashContainer");
    if (flashContainer) {
        setTimeout(() => { flashContainer.style.display = "none"; }, 4000);
    }

    function scrollToBottom() {
        if (messagesContainer) messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    scrollToBottom();

    function clearEmptyState() {
        const emptyState = messagesContainer.querySelector(".welcome-screen");
        if (emptyState) emptyState.remove();
    }

    function appendMessage(role, text) {
        clearEmptyState();
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

    // ---- Assistant replies: formatted Markdown, revealed gradually like an LLM typing ----
    function flattenForTyping(node, ops) {
        node.childNodes.forEach((child) => {
            if (child.nodeType === Node.TEXT_NODE) {
                ops.push({ t: "text", v: child.nodeValue });
            } else if (child.nodeType === Node.ELEMENT_NODE) {
                ops.push({ t: "open", el: child.cloneNode(false), table: child.tagName === "TABLE" });
                flattenForTyping(child, ops);
                ops.push({ t: "close" });
            }
        });
    }

    function appendAssistantReply(html, plainText) {
        clearEmptyState();
        const div = document.createElement("div");
        div.className = "message assistant";
        const bubble = document.createElement("div");
        bubble.className = "bubble md";
        div.appendChild(bubble);
        messagesContainer.appendChild(div);

        // No HTML from the server (shouldn't happen) -> fall back to plain text
        if (!html) {
            bubble.classList.remove("md");
            bubble.textContent = plainText || "";
            scrollToBottom();
            return div;
        }

        const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        if (reduceMotion) {
            bubble.innerHTML = html;
            scrollToBottom();
            return div;
        }

        const source = document.createElement("div");
        source.innerHTML = html;
        const ops = [];
        flattenForTyping(source, ops);

        let totalChars = 0;
        let depthInTable = 0;
        const openStack = [];
        ops.forEach((op) => {
            if (op.t === "open") {
                openStack.push(op.table);
                if (op.table) depthInTable++;
            } else if (op.t === "close") {
                if (openStack.pop()) depthInTable--;
            } else if (depthInTable === 0) {
                totalChars += op.v.length;
            }
        });
        // Longer replies type faster so nothing takes more than ~3 seconds
        const charsPerFrame = Math.max(1, Math.ceil(totalChars / 170));

        const stack = [bubble];
        let opIndex = 0;
        let charPos = 0;
        let currentText = null;
        let instant = 0; // >0 while inside a table: tables appear whole instead of cell by cell

        function step() {
            const nearBottom = messagesContainer.scrollHeight - messagesContainer.scrollTop - messagesContainer.clientHeight < 90;
            let budget = charsPerFrame;

            while (budget > 0 && opIndex < ops.length) {
                const op = ops[opIndex];
                if (op.t === "open") {
                    stack[stack.length - 1].appendChild(op.el);
                    stack.push(op.el);
                    if (op.table) instant++;
                    opIndex++;
                } else if (op.t === "close") {
                    const el = stack.pop();
                    if (el.tagName === "TABLE") instant--;
                    opIndex++;
                } else {
                    if (!currentText) {
                        currentText = document.createTextNode("");
                        stack[stack.length - 1].appendChild(currentText);
                        charPos = 0;
                    }
                    const remaining = op.v.length - charPos;
                    const take = instant > 0 ? remaining : Math.min(budget, remaining);
                    charPos += take;
                    if (instant === 0) budget -= take;
                    currentText.nodeValue = op.v.slice(0, charPos);
                    if (charPos >= op.v.length) {
                        currentText = null;
                        opIndex++;
                    }
                }
            }

            if (nearBottom) scrollToBottom();
            if (opIndex < ops.length) requestAnimationFrame(step);
        }
        step();
        return div;
    }

    function appendImageMessage(role, url) {
        clearEmptyState();
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

    function fileChipIcon(kind) {
        if (kind === "pdf") return "📄";
        if (kind === "docx") return "📝";
        return "📃";
    }

    function appendAttachmentMessage(role, attachment, caption) {
        clearEmptyState();
        const div = document.createElement("div");
        div.className = `message ${role}`;
        const bubble = document.createElement("div");
        bubble.className = "bubble";

        if (attachment.kind === "image") {
            bubble.classList.add("image-bubble");
            const img = document.createElement("img");
            img.src = attachment.url;
            img.alt = attachment.name;
            img.className = "chat-image";
            bubble.appendChild(img);
        } else {
            const link = document.createElement("a");
            link.href = attachment.url;
            link.target = "_blank";
            link.rel = "noopener";
            link.className = "file-chip";
            link.innerHTML = `<span class="file-chip-icon">${fileChipIcon(attachment.kind)}</span><span class="file-chip-name"></span>`;
            link.querySelector(".file-chip-name").textContent = attachment.name;
            bubble.appendChild(link);
        }

        if (caption && !caption.startsWith("(uploaded ")) {
            const captionEl = document.createElement("div");
            captionEl.className = "attachment-caption";
            captionEl.textContent = caption;
            bubble.appendChild(captionEl);
        }

        div.appendChild(bubble);
        messagesContainer.appendChild(div);
        scrollToBottom();
        return div;
    }

    function looksLikeImageRequest(text) {
        return /^\/image\s+/i.test(text.trim()) ||
               /\b(generate|create|draw|make|design|give|show|send|produce|paint|sketch|need)\b[^.]{0,25}\b(image|picture|photo|photograph|drawing|painting|artwork|illustration|poster|wallpaper|sketch)\b/i.test(text);
    }

    function showTyping(label) {
        const div = document.createElement("div");
        div.className = "message assistant typing";
        div.id = "typingIndicator";
        const labelHtml = label ? `<span class="typing-label">${label}</span>` : "";
        div.innerHTML = `<div class="bubble">
            ${labelHtml}
            <span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>
        </div>`;
        messagesContainer.appendChild(div);
        scrollToBottom();
    }

    function hideTyping() {
        const el = document.getElementById("typingIndicator");
        if (el) el.remove();
    }

    // ---- Attach-file UI ----
    function clearPendingFile() {
        pendingFile = null;
        if (fileInput) fileInput.value = "";
        if (pendingAttachmentEl) {
            pendingAttachmentEl.style.display = "none";
            pendingAttachmentEl.innerHTML = "";
        }
    }

    function showPendingFile(file) {
        pendingFile = file;
        if (!pendingAttachmentEl) return;
        pendingAttachmentEl.style.display = "flex";
        pendingAttachmentEl.innerHTML = `
            <span class="pending-attachment-icon">📎</span>
            <span class="pending-attachment-name"></span>
            <button type="button" class="pending-attachment-remove" title="Remove attachment">✕</button>
        `;
        pendingAttachmentEl.querySelector(".pending-attachment-name").textContent = file.name;
        pendingAttachmentEl.querySelector(".pending-attachment-remove").addEventListener("click", clearPendingFile);
    }

    if (attachBtn && fileInput) {
        attachBtn.addEventListener("click", () => fileInput.click());
        fileInput.addEventListener("change", () => {
            if (fileInput.files && fileInput.files[0]) {
                showPendingFile(fileInput.files[0]);
            }
        });
    }

    // ---- Send message (text, or text + attached file) ----
    if (messageForm) {
        messageForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const text = messageInput.value.trim();
            const file = pendingFile;

            if (!text && !file) return;

            const chatId = chatWindow.dataset.chatId;
            messageInput.value = "";
            clearPendingFile();

            try {
                let res;
                if (file) {
                    appendAttachmentMessage("user", {
                        kind: file.type.startsWith("image/") ? "image" : "other",
                        name: file.name,
                        url: URL.createObjectURL(file), // local preview only, until server responds
                    }, text);
                    showTyping(file.type.startsWith("image/") ? "Looking at the image…" : "Reading the file…");

                    const formData = new FormData();
                    formData.append("file", file);
                    if (text) formData.append("message", text);

                    res = await fetch(`/chat/${chatId}/send`, { method: "POST", body: formData });
                } else {
                    const isImageRequest = looksLikeImageRequest(text);
                    appendMessage("user", text);
                    showTyping(isImageRequest ? "Generating image (can take up to 30s)…" : null);

                    res = await fetch(`/chat/${chatId}/send`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ message: text }),
                    });
                }

                const data = await res.json();
                hideTyping();

                if (!res.ok) {
                    appendMessage("assistant", `⚠️ ${data.error || "Something went wrong."}`);
                } else if (data.type === "image" && data.image_url) {
                    appendImageMessage("assistant", data.image_url);
                } else if (data.reply) {
                    appendAssistantReply(data.reply_html, data.reply);
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
