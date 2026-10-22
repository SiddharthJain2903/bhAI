import os
import uuid

from flask import Blueprint, render_template, request, jsonify, current_app, send_from_directory, abort, url_for
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from models import db, Chat, Message
from llm import get_bot_response
from render import render_markdown
from tools import (
    extract_urls,
    fetch_page_text,
    detect_image_request,
    generate_image,
    IMAGE_MARKER,
    IMAGE_PLACEHOLDER_FOR_LLM,
    classify_file,
    extract_file_text,
    analyze_image_with_gemini,
)

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


@chat_bp.route("/uploads/<int:message_id>")
@login_required
def download_attachment(message_id):
    """Serves an uploaded attachment back to its owner only — never a public file URL."""
    msg = Message.query.get_or_404(message_id)
    if msg.chat.user_id != current_user.id or not msg.attachment_path:
        abort(404)
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], msg.attachment_path)


def _build_llm_history(chat):
    """
    Builds the message list sent to the LLM. Past generated-image markers are
    swapped for a plain description — sending the LLM its own raw
    "[bhai-image]<url>" marker text causes it to start imitating that literal
    format instead of replying normally.
    """
    history = []
    for m in chat.messages:
        content = m.content
        if m.role == "assistant" and content.startswith(IMAGE_MARKER):
            content = IMAGE_PLACEHOLDER_FOR_LLM
        history.append({"role": m.role, "content": content})
    return history


def _save_upload(chat, uploaded_file):
    """Saves an uploaded file to disk under a per-user/per-chat folder and returns (kind, safe_name, disk_path, relative_path)."""
    kind = classify_file(uploaded_file.filename)
    if kind is None:
        return None, None, None, None

    safe_name = secure_filename(uploaded_file.filename) or "file"
    unique_name = f"{uuid.uuid4().hex}_{safe_name}"

    user_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], str(current_user.id), str(chat.id))
    os.makedirs(user_dir, exist_ok=True)

    disk_path = os.path.join(user_dir, unique_name)
    uploaded_file.save(disk_path)
    relative_path = os.path.join(str(current_user.id), str(chat.id), unique_name)

    return kind, safe_name, disk_path, relative_path


def _handle_file_message(chat, uploaded_file, user_text):
    kind, safe_name, disk_path, relative_path = _save_upload(chat, uploaded_file)
    if kind is None:
        return jsonify({"error": "That file type isn't supported yet. Try an image, PDF, Word (.docx), or text file."}), 400

    display_text = user_text or f"(uploaded {safe_name})"
    user_msg = Message(
        chat_id=chat.id,
        role="user",
        content=display_text,
        attachment_name=safe_name,
        attachment_path=relative_path,
        attachment_kind=kind,
    )
    db.session.add(user_msg)

    if chat.title == "New Chat":
        title_source = user_text or safe_name
        chat.title = title_source[:40] + ("..." if len(title_source) > 40 else "")

    db.session.commit()

    if kind == "image":
        # Gemini looks at the actual image and answers directly — no separate
        # extraction step needed, and no local text-only model could do this part.
        bot_reply = analyze_image_with_gemini(disk_path, user_text)
    else:
        # PDF / Word / text: parsed locally (free, no API), then handed to the
        # normal chat model as extra context for this turn only — never stored
        # in the database, so it doesn't bloat future history.
        extracted = extract_file_text(disk_path, kind)
        instruction = user_text or "Give a helpful summary of this file's contents and call out anything important."
        history = _build_llm_history(chat)
        history[-1]["content"] = (
            f"{instruction}\n\n[System note: the user attached a file named '{safe_name}'. "
            f"Here is its extracted text content — use it to answer:]\n{extracted}"
        )
        bot_reply = get_bot_response(history)

    bot_msg = Message(chat_id=chat.id, role="assistant", content=bot_reply)
    db.session.add(bot_msg)
    db.session.commit()

    return jsonify({
        "type": "file_reply",
        "reply": bot_reply,
        "reply_html": render_markdown(bot_reply),
        "chat_title": chat.title,
        "attachment": {
            "name": safe_name,
            "kind": kind,
            "url": url_for("chat.download_attachment", message_id=user_msg.id),
        },
    })


@chat_bp.route("/chat/<int:chat_id>/send", methods=["POST"])
@login_required
def send_message(chat_id):
    chat = Chat.query.filter_by(id=chat_id, user_id=current_user.id).first_or_404()

    # ---- File upload path (multipart/form-data with a "file" part) ----
    uploaded_file = request.files.get("file")
    if uploaded_file and uploaded_file.filename:
        user_text = (request.form.get("message") or "").strip()
        return _handle_file_message(chat, uploaded_file, user_text)

    # ---- Plain JSON message (existing behaviour, unchanged) ----
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
    image_prompt = detect_image_request(user_text)
    if image_prompt:
        image_src = generate_image(image_prompt)
        bot_msg = Message(chat_id=chat.id, role="assistant", content=f"{IMAGE_MARKER}{image_src}")
        db.session.add(bot_msg)
        db.session.commit()
        return jsonify({"type": "image", "image_url": image_src, "chat_title": chat.title})

    # ---- Normal text path (with optional link reading) ----
    history = _build_llm_history(chat)

    urls = extract_urls(user_text)
    if urls:
        target_url = urls[0]
        page_text = fetch_page_text(target_url)
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

    return jsonify({"type": "text", "reply": bot_reply, "reply_html": render_markdown(bot_reply), "chat_title": chat.title})
