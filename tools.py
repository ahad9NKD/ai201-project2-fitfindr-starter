"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

from __future__ import annotations

import os
import re

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - fallback for minimal test environments
    def load_dotenv():
        return None

try:
    from groq import Groq
except ImportError:  # pragma: no cover - fallback for minimal test environments
    Groq = None

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    if Groq is None:
        raise ImportError(
            "groq is not installed. Install dependencies from requirements.txt."
        )
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


def _normalize_text(value: object) -> str:
    return str(value or "").strip().lower()


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", _normalize_text(text))


def _size_matches(requested_size: str | None, listing_size: str) -> bool:
    if requested_size is None:
        return True

    requested = _normalize_text(requested_size)
    listing = _normalize_text(listing_size)
    if not requested:
        return True

    if requested == listing:
        return True
    if requested in listing or listing in requested:
        return True

    requested_tokens = set(_tokenize(requested))
    listing_tokens = set(_tokenize(listing))
    if requested_tokens & listing_tokens:
        return True

    if len(requested) == 1 and requested.isalpha():
        return requested in listing

    return False


def _listing_search_text(listing: dict) -> dict[str, str]:
    return {
        "title": _normalize_text(listing.get("title")),
        "description": _normalize_text(listing.get("description")),
        "category": _normalize_text(listing.get("category")),
        "style_tags": " ".join(_normalize_text(tag) for tag in listing.get("style_tags", [])),
        "colors": " ".join(_normalize_text(color) for color in listing.get("colors", [])),
        "brand": _normalize_text(listing.get("brand")),
        "platform": _normalize_text(listing.get("platform")),
    }


def _score_listing(description: str, listing: dict) -> int:
    query = _normalize_text(description)
    tokens = [token for token in _tokenize(query) if token not in {"the", "and", "for", "with", "size", "under"}]
    if not tokens:
        tokens = _tokenize(query)

    searchable = _listing_search_text(listing)
    score = 0

    if query and (query in searchable["title"] or query in searchable["description"]):
        score += 8

    field_weights = {
        "title": 5,
        "description": 3,
        "style_tags": 4,
        "category": 2,
        "colors": 2,
        "brand": 1,
        "platform": 1,
    }

    for token in dict.fromkeys(tokens):
        token_score = 0
        for field, weight in field_weights.items():
            if token in searchable[field]:
                token_score = max(token_score, weight)
        score += token_score

    return score


def _chat_completion(prompt: str, *, temperature: float) -> str:
    client = _get_groq_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are FitFindr, a styling assistant. "
                    "Be specific, concise, and helpful."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=temperature,
        max_tokens=220,
    )
    return response.choices[0].message.content.strip()


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    listings = load_listings()
    matching_listings: list[tuple[int, float, int, dict]] = []
    description_text = _normalize_text(description)

    for index, listing in enumerate(listings):
        if max_price is not None and float(listing.get("price", 0.0)) > max_price:
            continue
        if not _size_matches(size, listing.get("size", "")):
            continue

        score = _score_listing(description_text, listing)
        if score <= 0:
            continue

        matching_listings.append((score, float(listing.get("price", 0.0)), index, listing))

    matching_listings.sort(key=lambda item: (-item[0], item[1], item[2]))
    return [listing for _, _, _, listing in matching_listings]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    wardrobe_items = (wardrobe or {}).get("items", [])
    item_name = new_item.get("title", "this item")

    if not wardrobe_items:
        return (
            f"I found {item_name}, but your wardrobe is empty right now. "
            "Add a few tops, bottoms, and shoes first, and I can build a specific outfit."
        )

    wardrobe_summary = []
    for item in wardrobe_items:
        parts = [
            f"name: {item.get('name', 'unknown')}",
            f"category: {item.get('category', 'unknown')}",
            f"colors: {', '.join(item.get('colors', [])) or 'none'}",
            f"style_tags: {', '.join(item.get('style_tags', [])) or 'none'}",
        ]
        notes = item.get("notes")
        if notes:
            parts.append(f"notes: {notes}")
        wardrobe_summary.append(" | ".join(parts))

    prompt = (
        "Suggest 1-2 outfits using the new item and the wardrobe below.\n"
        f"New item:\n"
        f"- name: {new_item.get('title', 'Unknown item')}\n"
        f"- category: {new_item.get('category', 'unknown')}\n"
        f"- size: {new_item.get('size', 'unknown')}\n"
        f"- colors: {', '.join(new_item.get('colors', [])) or 'none'}\n"
        f"- style_tags: {', '.join(new_item.get('style_tags', [])) or 'none'}\n"
        f"- price: ${new_item.get('price', 'unknown')}\n"
        f"- platform: {new_item.get('platform', 'unknown')}\n\n"
        "Wardrobe items:\n"
        + "\n".join(f"- {entry}" for entry in wardrobe_summary)
        + "\n\n"
        "Requirements:\n"
        "- Refer to specific wardrobe items by name when possible.\n"
        "- Explain why the pairing works in one or two short sentences.\n"
        "- Keep it casual and actionable.\n"
        "- Do not mention that you are an AI."
    )

    try:
        return _chat_completion(prompt, temperature=0.7)
    except Exception as exc:
        return f"I couldn’t generate an outfit suggestion right now: {exc}"


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    if not outfit or not outfit.strip():
        return "I couldn’t build the fit card because the outfit suggestion is missing."

    prompt = (
        "Write a casual 2-4 sentence fit-card caption for a thrift find.\n"
        f"New item title: {new_item.get('title', 'Unknown item')}\n"
        f"Price: ${new_item.get('price', 'unknown')}\n"
        f"Platform: {new_item.get('platform', 'unknown')}\n"
        f"Category: {new_item.get('category', 'unknown')}\n"
        f"Colors: {', '.join(new_item.get('colors', [])) or 'none'}\n"
        f"Style tags: {', '.join(new_item.get('style_tags', [])) or 'none'}\n"
        f"Outfit suggestion: {outfit}\n\n"
        "Requirements:\n"
        "- Sound like a real social caption, not a product listing.\n"
        "- Mention the item name, price, and platform naturally once each.\n"
        "- Capture the outfit vibe in specific, vivid language.\n"
        "- Keep it concise but lively."
    )

    try:
        return _chat_completion(prompt, temperature=0.9)
    except Exception as exc:
        return f"I couldn’t create the fit card right now: {exc}"
