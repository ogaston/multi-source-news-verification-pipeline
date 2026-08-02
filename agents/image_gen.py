"""DeepInfra FLUX cover-image generation for verified articles."""

from __future__ import annotations

import base64
import re
from pathlib import Path

import httpx

from common.config import (
    ARTICLE_IMAGES_DIR,
    DEEPINFRA_API_KEY,
    DEEPINFRA_BASE_URL,
    DEEPINFRA_IMAGE_MODEL,
    DEEPINFRA_IMAGE_SIZE,
    PUBLIC_API_URL,
)

# Aesthetic cue only — never request characters, IP, or lettering from the show.
_STYLE_BLOCK = (
    "Render as an original editorial illustration inspired only by the aesthetic "
    "of Samurai Jack: bold silhouettes, flat color planes, stark high contrast, "
    "sparse backgrounds, dramatic negative space, and sharp geometric shapes. "
    "The aesthetic similarity must stop there — do not include Samurai Jack, "
    "samurai warriors, katanas, feudal Japan, anime mascots, or any show characters "
    "or branding. Depict a unique, authentic scene grounded in the real news event "
    "(local architecture, climate, and people when relevant). "
    "Landscape composition filling a 4:3 frame. "
    "Absolutely no text, letters, numbers, captions, speech bubbles, logos, "
    "watermarks, or readable signage."
)
_WHITESPACE_RE = re.compile(r"\s+")


def build_event_summary(
    title: str,
    *,
    category: str | None = None,
    place: str | None = None,
) -> str:
    """Build a short English scene description from article metadata."""
    event = _WHITESPACE_RE.sub(" ", (title or "").strip())
    if not event:
        event = "A news event"
    bits = [f"Contemporary news scene: {event}"]
    if place:
        bits.append(f"set in {place.strip()}")
    if category:
        bits.append(f"topic {category.strip()}")
    return ", ".join(bits)


def build_image_prompt(
    title: str,
    *,
    category: str | None = None,
    place: str | None = None,
) -> str:
    summary = build_event_summary(title, category=category, place=place)
    return f"{summary}. {_STYLE_BLOCK}"


def public_image_url(article_id: str) -> str:
    return f"{PUBLIC_API_URL}/media/articles/{article_id}.jpg"


def image_path_for(article_id: str, *, images_dir: str | Path | None = None) -> Path:
    root = Path(images_dir or ARTICLE_IMAGES_DIR)
    return root / f"{article_id}.jpg"


def generate_article_image(
    *,
    article_id: str,
    title: str,
    category: str | None = None,
    place: str | None = None,
    api_key: str | None = None,
    model: str = DEEPINFRA_IMAGE_MODEL,
    size: str = DEEPINFRA_IMAGE_SIZE,
    images_dir: str | Path | None = None,
    timeout: float = 120.0,
) -> str | None:
    """
    Generate a cover image via DeepInfra FLUX and write it to disk.

    Returns the public absolute URL on success, or None on soft failure.
    """
    key = api_key if api_key is not None else DEEPINFRA_API_KEY
    if not key:
        print("[image-gen] DEEPINFRA_API_KEY is not set; skipping", flush=True)
        return None

    prompt = build_image_prompt(title, category=category, place=place)
    url = f"{DEEPINFRA_BASE_URL}/images/generations"
    payload = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "n": 1,
        "response_format": "b64_json",
    }
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    print(f"[image-gen] calling {model} for article {article_id}...", flush=True)
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            body = response.json()
    except Exception as exc:
        print(f"[image-gen] request failed for {article_id}: {exc}", flush=True)
        return None

    try:
        b64 = body["data"][0]["b64_json"]
        raw = base64.b64decode(b64)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        print(f"[image-gen] bad response for {article_id}: {exc}", flush=True)
        return None

    path = image_path_for(article_id, images_dir=images_dir)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    except OSError as exc:
        print(f"[image-gen] write failed for {article_id}: {exc}", flush=True)
        return None

    public_url = public_image_url(article_id)
    print(f"[image-gen] saved {path} -> {public_url}", flush=True)
    return public_url
