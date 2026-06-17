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

import os
import re

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


def _fallback_suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    items = wardrobe.get("items", [])
    if not items:
        return (
            f"The {new_item['title']} would look great with high-waisted jeans or a flowy skirt, "
            "chunky boots, and a lightweight jacket for a relaxed vintage streetwear vibe. "
            "Keep accessories minimal and let the graphic print be the focus."
        )

    return (
        f"Style the {new_item['title']} with pieces from your wardrobe for an easy outfit: "
        "pair it with a fitted denim jacket and straight-leg jeans, or tuck it into a skirt with "
        "bright sneakers for an effortless casual look that balances comfort and vintage flair."
    )


def _fallback_create_fit_card(outfit: str, new_item: dict) -> str:
    return (
        f"Just scored this {new_item['title']} for ${new_item['price']} on {new_item['platform']} — "
        "it's the perfect vintage-ready piece to elevate a laid-back outfit with easy streetwear energy."
    )


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

    # Filter by price and size
    filtered = []
    for item in listings:
        if max_price is not None and item["price"] > max_price:
            continue
        if size is not None and size.lower() not in item["size"].lower():
            continue
        filtered.append(item)

    # Score by keyword overlap — word-boundary match to avoid false substring hits
    keywords = [kw for kw in description.lower().split() if len(kw) > 1]
    scored = []
    for item in filtered:
        searchable = " ".join([
            item["title"],
            item["description"],
            " ".join(item["style_tags"]),
            item["category"],
        ]).lower()
        score = sum(
            1 for kw in keywords
            if re.search(r'\b' + re.escape(kw) + r'\b', searchable)
        )
        if score > 0:
            scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored]


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
    client = _get_groq_client()
    items = wardrobe.get("items", [])

    item_summary = (
        f"Item: {new_item['title']}\n"
        f"Category: {new_item['category']}\n"
        f"Colors: {', '.join(new_item['colors'])}\n"
        f"Style tags: {', '.join(new_item['style_tags'])}\n"
        f"Condition: {new_item['condition']}\n"
        f"Price: ${new_item['price']}"
    )

    if not items:
        prompt = (
            f"A user is considering buying this secondhand item:\n\n{item_summary}\n\n"
            "They are a new user with no wardrobe on file. Give them 2 general styling directions — "
            "describe the TYPE of pieces to look for (e.g. 'wide-leg trousers', 'chunky boots', "
            "'an oversized blazer'), NOT specific items they might own. "
            "For each direction, name the aesthetic or vibe it creates. "
            "Do NOT say 'pair with your...' or reference any existing wardrobe. "
            "Start your response with: 'No wardrobe on file yet — here are two directions to build around this piece:'"
        )
    else:
        wardrobe_lines = "\n".join(
            f"- {w['name']} ({w['category']}, {', '.join(w['colors'])})"
            for w in items
        )
        prompt = (
            f"A user is considering buying this secondhand item:\n\n{item_summary}\n\n"
            f"Here is their existing wardrobe:\n{wardrobe_lines}\n\n"
            "Suggest 1-2 complete outfits that use the new item with pieces ALREADY IN their wardrobe above. "
            "You MUST name each wardrobe piece by its exact name from the list. "
            "Do not suggest pieces they don't own. Be specific about how to style it and what vibe it creates. "
            "Start your response with: 'From your wardrobe:'"
        )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return _fallback_suggest_outfit(new_item, wardrobe)


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
        return (
            "Couldn't generate a fit card — the outfit suggestion was empty. "
            "Try running suggest_outfit again before calling create_fit_card."
        )

    client = _get_groq_client()

    prompt = (
        f"Write a 2-4 sentence Instagram/TikTok caption for this thrift find:\n\n"
        f"Item: {new_item['title']}\n"
        f"Price: ${new_item['price']}\n"
        f"Platform: {new_item['platform']}\n\n"
        f"Outfit styling context:\n{outfit}\n\n"
        "Requirements:\n"
        "- Sound like a real OOTD post, not a product description\n"
        "- Mention the item name, price, and platform naturally — each exactly once\n"
        "- Capture the specific vibe of the outfit\n"
        "- Keep it casual and authentic, like something you'd actually post\n"
        "Return just the caption text, no hashtags, no extra commentary."
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=1.1,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return _fallback_create_fit_card(outfit, new_item)
