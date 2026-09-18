import requests
from flask import current_app

SYSTEM_PROMPT = (
    "You are bhAI — a friendly, witty personal AI assistant. Your name is a play on "
    "the Hindi word 'bhai' (brother/friend) and also stands for 'Bharatiya AI'. "
    "You are helpful, concise, and warm. You can naturally mix in light Hinglish if "
    "the user does, but always stay clear, accurate, and useful."
)


def get_bot_response(message_history):
    """
    message_history: list of dicts like [{"role": "user", "content": "..."}, ...]
    Returns the assistant's reply as a plain string.
    """
    provider = current_app.config["LLM_PROVIDER"]
    if provider == "ollama":
        return _ollama_response(message_history)
    return _groq_response(message_history)


def _groq_response(message_history):
    api_key = current_app.config["GROQ_API_KEY"]
    model = current_app.config["GROQ_MODEL"]

    if not api_key:
        return (
            "⚠️ No Groq API key found. Get a free one at "
            "https://console.groq.com/keys and put it in your .env file as "
            "GROQ_API_KEY=..."
        )

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + message_history,
        "temperature": 0.7,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except requests.exceptions.HTTPError:
        return (
            "⚠️ Groq rejected the request — double-check that GROQ_API_KEY in your "
            ".env file is correct and still active."
        )
    except requests.exceptions.RequestException as e:
        return f"⚠️ Couldn't reach Groq right now ({e}). Check your internet connection."
    except Exception as e:
        return f"⚠️ Something unexpected happened: {e}"


def _ollama_response(message_history):
    url = current_app.config["OLLAMA_URL"]
    model = current_app.config["OLLAMA_MODEL"]
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + message_history,
        "stream": False,
    }
    try:
        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "").strip() or "Hmm, I didn't get a reply. Try again?"
    except requests.exceptions.ConnectionError:
        return (
            "⚠️ Can't reach Ollama. Make sure it's installed and running "
            f"(`ollama serve`) and that you've pulled the model (`ollama pull {model}`)."
        )
    except Exception as e:
        return f"⚠️ Something went wrong talking to Ollama: {e}"
