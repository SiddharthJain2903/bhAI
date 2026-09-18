# bhAI 🤖 — Your Personal AI (Bharatiya AI)

A full-stack personal chatbot web app: user accounts, login, persistent chat
history, and a dynamic (no page-reload) chat UI — built with Flask and
100% free tools.

**Stack:** Flask · Flask-Login (auth) · Flask-SQLAlchemy (SQLite database) ·
Flask-Bcrypt (password hashing) · Groq API (free LLM) · vanilla JS/CSS (no
frontend build step needed).

---

## 1. Prerequisites

| Tool | Why | Link |
|---|---|---|
| Python 3.10+ | Runs the app | https://www.python.org/downloads/ (when installing, tick **"Add Python to PATH"**) |
| VS Code | Your IDE | https://code.visualstudio.com/ |
| VS Code "Python" extension (by Microsoft) | Linting, run/debug, venv detection | Install from the Extensions tab (`Ctrl+Shift+X`) inside VS Code |
| A free Groq account + API key | Powers bhAI's replies, no cost | https://console.groq.com/keys |
| Git (optional but recommended) | Version control | https://git-scm.com/download/win |

You do **not** need to pay for anything. Groq's free tier is generous for
personal use, and the entire rest of the stack (Flask, SQLite, etc.) is
open source and runs on your own machine.

---

## 2. Get the project into VS Code

1. Unzip the `bhAI` folder anywhere you like, e.g. `C:\Users\<you>\Projects\bhAI`.
2. Open VS Code → **File → Open Folder...** → select the `bhAI` folder.
3. You should see this structure in the Explorer sidebar:

```
bhAI/
├── app.py              # entry point (Flask app factory)
├── config.py            # reads settings from .env
├── models.py             # User / Chat / Message database tables
├── auth.py               # register / login / logout routes
├── chat.py                # dashboard, new/delete chat, send-message API
├── llm.py                  # talks to Groq (or Ollama) to get AI replies
├── requirements.txt
├── .env.example
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   └── chat.html
└── static/
    ├── css/style.css
    └── js/chat.js
```

---

## 3. Create a virtual environment (in VS Code's terminal)

Open the integrated terminal: **Terminal → New Terminal** (or `` Ctrl+` ``).
Make sure it's a PowerShell or Command Prompt terminal, then run:

```powershell
python -m venv venv
venv\Scripts\activate
```

You'll know it worked because your terminal prompt now starts with `(venv)`.

> If PowerShell blocks the activation script with an execution-policy error,
> run this once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
> and try `venv\Scripts\activate` again.

**Tell VS Code to use this venv:** Press `Ctrl+Shift+P` → type
`Python: Select Interpreter` → choose the one that shows `.\venv\Scripts\python.exe`.
This makes VS Code's IntelliSense/debugging use the right environment.

Now install dependencies:

```powershell
pip install -r requirements.txt
```

---

## 4. Get your free Groq API key

1. Go to https://console.groq.com/keys and sign in (free, just an email/Google login).
2. Click **Create API Key**, give it any name, copy the key (starts with `gsk_...`).
3. Keep it safe — you won't be able to see it again after closing the dialog.

---

## 5. Configure your environment

In VS Code, duplicate `.env.example` and rename the copy to `.env`
(right-click the file → Copy, then rename). Open `.env` and fill it in:

```env
SECRET_KEY=paste-a-random-string-here
DATABASE_URL=sqlite:///bhai.db
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your_real_key_here
GROQ_MODEL=llama-3.1-8b-instant
```

To generate a random `SECRET_KEY`, run this in the terminal:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Paste the output as your `SECRET_KEY` value.

> `.env` is already listed in `.gitignore`, so it will never get committed
> to Git/GitHub by accident — your API key stays private.

---

## 6. Run bhAI

In the VS Code terminal (with `(venv)` active):

```powershell
python app.py
```

You should see something like:

```
 * Running on http://127.0.0.1:5000
```

Open that URL in your browser → you'll land on the bhAI login page.
Click **Create an account**, sign up, and you're straight into the chat UI.

**To stop the server:** click the terminal and press `Ctrl+C`.

### Optional: Run/Debug with VS Code's built-in runner
Instead of the terminal, you can just open `app.py` and press `F5`
(or the ▶ Run button top-right) — VS Code will use the selected venv
interpreter automatically and you get full breakpoint debugging.

---

## 7. How it works (quick tour)

- **Accounts & login** — `auth.py` handles register/login/logout.
  Passwords are hashed with bcrypt (never stored in plain text).
- **Chat history** — every chat and every message is saved to a local
  SQLite file `bhai.db` (auto-created on first run) via the models in
  `models.py`. Refresh the page, log out and back in, restart your PC —
  your history is still there.
- **Dynamic UI** — `static/js/chat.js` sends your message to
  `/chat/<id>/send` with `fetch()`, shows a typing indicator, and injects
  the reply into the page — no reloads, feels like a real chat app.
- **The "brain"** — `llm.py` sends your conversation to Groq's free
  `llama-3.1-8b-instant` model and returns bhAI's reply. bhAI has a system
  prompt giving it its friendly "bro/friend" personality.

---

## 8. Switching to a fully offline/local model (optional)

If you'd rather not depend on the internet or a cloud API at all, bhAI also
supports **Ollama** (100% free, runs entirely on your PC):

1. Install Ollama for Windows: https://ollama.com/download
2. Open a terminal and pull a small free model:
   ```powershell
   ollama pull llama3.2
   ```
3. In your `.env`, change:
   ```env
   LLM_PROVIDER=ollama
   OLLAMA_MODEL=llama3.2
   ```
4. Make sure Ollama is running (it usually starts automatically after
   install), then run `python app.py` as usual.

No code changes needed — `llm.py` already supports both providers.

---

## 9. Common issues

| Problem | Fix |
|---|---|
| `'python' is not recognized` | Reinstall Python and tick "Add to PATH", then restart VS Code |
| `ModuleNotFoundError: flask` | Your venv isn't activated — run `venv\Scripts\activate` again, and make sure VS Code's selected interpreter is the venv one |
| Bot replies with a ⚠️ warning about Groq | Check `GROQ_API_KEY` in `.env` is correct and has no extra spaces/quotes |
| Port 5000 already in use | Change the port in `app.py`'s last line, e.g. `app.run(debug=True, port=5050)` |
| Styles look broken | Hard-refresh the browser (`Ctrl+F5`) to clear cached CSS |

---

## 10. Ideas to extend it later

- Streaming responses (token-by-token) instead of waiting for the full reply
- Markdown rendering for code blocks in bot replies
- Voice input/output
- Export a chat as PDF/text
- Deploy for free on Render.com or PythonAnywhere so you can access bhAI from your phone

Enjoy bhAI — your own bhai, always ready to help. 🇮🇳
