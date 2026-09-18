import re
import random
import urllib.parse

import requests
from bs4 import BeautifulSoup

URL_REGEX = re.compile(r'https?://[^\s<>"\']+')

# Explicit command: "/image a cat riding a bicycle"
IMAGE_COMMAND_REGEX = re.compile(r'^/image\s+(.+)', re.IGNORECASE)

# Loose natural-language fallback: "generate an image of a sunset", "draw me a dragon",
# "give me an image saying hi", "send a picture of a dog"
IMAGE_NATURAL_REGEX = re.compile(
    r'\b(generate|create|draw|make|design|give|show|send|produce|paint|sketch|need)\b'
    r'[^.]{0,25}\b(image|picture|photo|photograph|drawing|painting|artwork|illustration|poster|wallpaper|sketch)\b'
    r'(?:\s+(?:of|showing|depicting|saying|that says|with|for))?\s*(.*)',
    re.IGNORECASE,
)

IMAGE_MARKER = "[bhai-image]"
IMAGE_PLACEHOLDER_FOR_LLM = "(I generated an image here for the user.)"


def extract_urls(text):
    """Return a list of http(s) URLs found in the given text."""
    return URL_REGEX.findall(text)


def fetch_page_text(url, max_chars=3000, timeout=10):
    """
    Download a web page and return its readable text content, stripped of
    scripts/styles/nav/etc. Pure HTML parsing — no AI/ML involved.
    Returns a short error string instead of raising, so the chat flow never crashes.
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; bhAI-chatbot/1.0)"}
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
            tag.decompose()

        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        cleaned = "\n".join(lines)

        if not cleaned:
            return "[This page had no readable text content.]"
        return cleaned[:max_chars]

    except requests.exceptions.RequestException as e:
        return f"[Could not fetch this link: {e}]"
    except Exception as e:
        return f"[Error while reading this link: {e}]"


def detect_image_request(text):
    """
    Returns the extracted image prompt if the user's message looks like an
    image request, otherwise None. The explicit "/image ..." command is
    always the most reliable trigger.
    """
    text = text.strip()

    m = IMAGE_COMMAND_REGEX.match(text)
    if m:
        return m.group(1).strip().strip('"\'')

    m2 = IMAGE_NATURAL_REGEX.search(text)
    if m2:
        prompt = m2.group(3).strip().strip('"\'')
        if prompt:
            return prompt
        # Trigger words matched but nothing followed (e.g. "make me an image") —
        # fall back to the whole message minus the trigger phrase itself.
        return text

    return None


def build_image_url(prompt, width=1024, height=1024):
    """
    Builds a Pollinations.ai image URL for the given prompt. Pollinations is
    free, requires no API key, and generates the image on-demand the moment
    a browser requests this URL — so we never need to download/host it ourselves.
    """
    encoded_prompt = urllib.parse.quote(prompt)
    seed = random.randint(1, 999_999)  # avoids the browser/CDN caching the same image every time
    return (
        f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        f"?width={width}&height={height}&nologo=true&seed={seed}"
    )
