from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

from models import db, Chat, Message
from llm import get_bot_response
from tools import extract_urls, fetch_page_text, detect_image_request, build_image_url, IMAGE_MARKER, IMAGE_PLACEHOLDER_FOR_LLM

chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/")
@login_required
def dashboard():
    chats = Chat.query.filter_by(user_id=current_user.id).order_by(Chat.created_at.desc()).all()
    active_chat = chats[0] if chats else None
    return render_template("chat.html", chats=chats, active_chat=active_chat)


@chat_bp.route("/chat/<int:chat_id>")
@login_required
def view_chat(chat_id):
    chats = Chat.query.filter_by(user_id=current_user.id).order_by(Chat.created_at.desc()).all()
    active_chat = Chat.query.filter_by(id=chat_id, user_id=current_user.id).first_or_404()
    return render_template("chat.html", chats=chats, active_chat=active_chat)


@chat_bp.route("/chat/new", methods=["POST"])
@login_required
def new_chat():
    chat = Chat(user_id=current_user.id, title="New Chat")
    db.session.add(chat)
    db.session.commit()
    return jsonify({"chat_id": chat.id, "title": chat.title})


@chat_bp.route("/chat/<int:chat_id>/delete", methods=["POST"])
@login_required
def delete_chat(chat_id):
    chat = Chat.query.filter_by(id=chat_id, user_id=current_user.id).first_or_404()
    db.session.delete(chat)
    db.session.commit()
    return jsonify({"success": True})


@chat_bp.route("/chat/<int:chat_id>/send", methods=["POST"])
@login_required
def send_message(chat_id):
    chat = Chat.query.filter_by(id=chat_id, user_id=current_user.id).first_or_404()
    data = request.get_json(silent=True) or {}
    user_text = (data.get("message") or "").strip()

    if not user_text:
        return jsonify({"error": "Empty message"}), 400

    user_msg = Message(chat_id=chat.id, role="user", content=user_text)
    db.session.add(user_msg)

    if chat.title == "New Chat":
        chat.title = user_text[:40] + ("..." if len(user_text) > 40 else "")

    db.session.commit()

    # ---- Image generation path ----
    # Triggered by "/image <prompt>" or natural phrases like "generate an image of..."
    image_prompt = detect_image_request(user_text)
    if image_prompt:
        image_url = build_image_url(image_prompt)
        bot_msg = Message(chat_id=chat.id, role="assistant", content=f"{IMAGE_MARKER}{image_url}")
        db.session.add(bot_msg)
        db.session.commit()
        return jsonify({"type": "image", "image_url": image_url, "chat_title": chat.title})

    # ---- Normal text path (with optional link reading) ----
    # Never send the raw "[bhai-image]<url>" marker to the LLM — otherwise it
    # starts imitating that literal text instead of writing a normal reply.
    history = []
    for m in chat.messages:
        content = m.content
        if m.role == "assistant" and content.startswith(IMAGE_MARKER):
            content = IMAGE_PLACEHOLDER_FOR_LLM
        history.append({"role": m.role, "content": content})

    urls = extract_urls(user_text)
    if urls:
        target_url = urls[0]
        page_text = fetch_page_text(target_url)
        # Only the copy sent to the LLM is augmented — what's stored in the
        # database stays as the user's original message.
        history[-1]["content"] = (
            f"{user_text}\n\n"
            f"[System note: the user shared this link: {target_url}. "
            f"Here is the extracted text content from that page — use it to "
            f"answer the user's message:]\n{page_text}"
        )

    bot_reply = get_bot_response(history)
    bot_msg = Message(chat_id=chat.id, role="assistant", content=bot_reply)
    db.session.add(bot_msg)
    db.session.commit()

    return jsonify({"type": "text", "reply": bot_reply, "chat_title": chat.title})
