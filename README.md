# FitFindr

FitFindr is an AI-powered thrift shopping agent. You describe what you're looking for — item type, size, price ceiling — and it searches a mock secondhand listings dataset, generates outfit ideas using your existing wardrobe, and produces a shareable social-media caption, all in one interaction.

## How to Run

```bash
# Activate the virtual environment (Windows)
.venv\Scripts\activate

# Add your Groq API key
echo GROQ_API_KEY=your_key_here > .env

# Launch the Gradio UI
python app.py
```

Open the URL shown in your terminal (usually `http://localhost:7860`).

To run the CLI test:
```bash
python agent.py
```

To run the full test suite:
```bash
pytest tests/
```

---

## Tool Inventory

### `search_listings(description, size, max_price)`

**Purpose:** Searches the 40-item mock secondhand listings dataset for items matching the user's query.

**Inputs:**
- `description` (`str`): Freeform keywords describing the desired item, e.g. `"vintage graphic tee"`. Scored against each listing's title, description, style tags, and category using whole-word regex matching.
- `size` (`str | None`): Size string to filter by, e.g. `"M"` or `"S/M"`. Case-insensitive substring match. Pass `None` to skip size filtering.
- `max_price` (`float | None`): Maximum item price, inclusive. Pass `None` for no price ceiling.

**Output:** A list of listing dicts sorted by relevance score (highest first). Each dict contains: `id`, `title`, `description`, `category`, `style_tags` (list), `size`, `condition`, `price` (float), `colors` (list), `brand`, `platform`. Returns an empty list if nothing matches — never raises an exception.

---

### `suggest_outfit(new_item, wardrobe)`

**Purpose:** Uses an LLM (Groq `llama-3.3-70b-versatile`) to suggest 1–2 complete outfits combining the thrifted item with pieces from the user's existing wardrobe.

**Inputs:**
- `new_item` (`dict`): A full listing dict from `search_listings` — the item being considered.
- `wardrobe` (`dict`): A dict with an `items` key holding a list of wardrobe item dicts. Each item has `id`, `name`, `category`, `colors` (list), `style_tags` (list), `notes`. May be empty — handled gracefully.

**Output:** A non-empty string with 1–2 outfit suggestions. If `wardrobe["items"]` is empty, the LLM provides general styling advice (types of pieces and aesthetics that suit the item) rather than naming specific wardrobe pieces.

---

### `create_fit_card(outfit, new_item)`

**Purpose:** Uses an LLM to generate a short, casual Instagram/TikTok-style caption for the thrift find.

**Inputs:**
- `outfit` (`str`): The outfit suggestion string from `suggest_outfit`. If this is empty or whitespace-only, the function returns an error string without calling the LLM.
- `new_item` (`dict`): The listing dict for the thrifted item — used to include the item name, price, and platform in the caption.

**Output:** A 2–4 sentence string in OOTD voice that mentions the item name, price, and platform each exactly once. If `outfit` is empty, returns a descriptive error message string instead of raising an exception. LLM temperature is set to 1.1 so outputs vary across calls.

---

## Planning Loop

The planning loop lives in `run_agent()` in `agent.py`. It runs one user query from start to finish and returns a session dict.

**Parse.** The agent first extracts three structured values from the natural language query using regex: a price ceiling (matches `$30` or `under 30`), a size token (matches `size M` or standalone tokens like `XL`, `S/M`), and a description (everything left after removing price, size, and a stop-word list). Stop phrases are applied longest-first — "looking for" is stripped as a unit before "for" is stripped individually, which avoids leaving stray words like "looking" in the keyword set and skewing scores.

**Search and branch.** `search_listings` is called with the three parsed values. If the result list is empty, the agent immediately sets `session["error"]` to a message that names the query and whichever filters were active (e.g. size and price), then returns the session early. `suggest_outfit` and `create_fit_card` are never called on an empty result — this was the key branching requirement and was verified by running the no-results test case and confirming `session["fit_card"]` remained `None`.

**Style and caption.** If results came back, `results[0]` (the top-scoring listing) is stored as `selected_item`. The agent calls `suggest_outfit` with that item and the session wardrobe, stores the string result as `outfit_suggestion`, then calls `create_fit_card` with the outfit string and item. Everything flows linearly — each tool's output is stored in the session and passed directly into the next call.

---

## State Management

All state for a single interaction lives in a dict created by `_new_session()` at the start of `run_agent()`. No values are re-fetched or recomputed between steps.

| Key | Set when | Used by |
|-----|----------|---------|
| `query` | Initialization | Display / debugging |
| `parsed` | After regex parsing | `search_listings` inputs |
| `search_results` | After `search_listings` | Selecting `selected_item` |
| `selected_item` | After search | `suggest_outfit`, `create_fit_card`, display |
| `wardrobe` | Initialization (loaded in `app.py`) | `suggest_outfit` |
| `outfit_suggestion` | After `suggest_outfit` | `create_fit_card`, display |
| `fit_card` | After `create_fit_card` | Display |
| `error` | If search returns empty | Early return |

`selected_item` is the exact same dict object as `search_results[0]` — not a copy. This was verified during testing with `assert session["selected_item"] is session["search_results"][0]`.

---

## Interaction Walkthrough

**User query:** `"looking for a vintage graphic tee under $30"`

**Step 1 — Tool called: `search_listings`**
- Input: `description="vintage graphic tee"`, `size=None`, `max_price=30.0`
- Why this tool: The agent always starts here to get concrete listings before doing anything else. Without a real item to work with, styling advice has nothing to reference.
- Output: 20 matching listings sorted by score. Top result: `Y2K Baby Tee — Butterfly Print` ($18, Depop) — it scores 3 points because "vintage", "graphic", and "tee" all appear in its title, description, or style tags.

**Step 2 — Tool called: `suggest_outfit`**
- Input: `new_item={"title": "Y2K Baby Tee — Butterfly Print", "price": 18.0, "colors": ["white", "pink", "purple"], "style_tags": ["y2k", "vintage", "graphic tee", "cottagecore"], ...}`, `wardrobe=<example wardrobe with 10 items>`
- Why this tool: Now that there's a real item, the agent can ask the LLM for outfit ideas using the user's actual wardrobe pieces — something that can't happen without `search_listings` running first.
- Output: `"Outfit 1: Pair the Y2K Baby Tee with your baggy straight-leg jeans (dark wash) and platform sneakers for a streetwear-meets-Y2K look. Outfit 2: Tuck it into your wide-leg khaki trousers and add your suede mules for a softer, cottagecore-adjacent vibe."`

**Step 3 — Tool called: `create_fit_card`**
- Input: `outfit=<the outfit suggestion string from step 2>`, `new_item=<same Y2K Baby Tee dict>`
- Why this tool: The outfit suggestion is functional but reads like instructions. `create_fit_card` turns it into something casual and shareable — the kind of caption a real person would post with a thrift haul photo.
- Output: `"Found this Y2K Baby Tee — Butterfly Print for $18 on Depop and it literally goes with everything in my closet. Styled it with dark-wash baggy jeans and platform sneakers and I haven't taken it off. Thrift finds just hit different."`

**Final output to user:** Three panels populate — the top listing's details (title, price, platform, condition, colors, tags, description), the outfit suggestion, and the fit card caption ready to copy.

---

## Error Handling and Fail Points

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| `search_listings` | No listings match the query, size, and price filters | Sets `session["error"]` to a message naming the query and active filters (e.g. `"No listings found for 'designer ballgown' (size XXS, under $5). Try broader keywords, a different size, or a higher price."`), returns immediately — `suggest_outfit` and `create_fit_card` are never called |
| `suggest_outfit` | Wardrobe is empty (`wardrobe["items"] == []`) | Detects the empty list, builds a different LLM prompt asking for general styling advice — what types of bottoms, shoes, and outerwear pair well with the item — and returns that as a non-empty string. No exception is raised and the interaction continues to `create_fit_card`. |
| `create_fit_card` | `outfit` string is empty or whitespace-only | Guard clause at the top of the function returns the string `"Couldn't generate a fit card — the outfit suggestion was empty. Try running suggest_outfit again before calling create_fit_card."` without calling the LLM. No exception is raised. |

---

## Spec Reflection

**One way `planning.md` helped during implementation:**

Having the exact return shape of `search_listings` written out before coding made it much easier to write `suggest_outfit` and `create_fit_card` correctly on the first try. Because the spec already said "each dict contains: id, title, description, category, style_tags (list), size, condition, price (float), colors (list), brand, platform," both downstream tools could reference those exact field names without checking the data format first. The spec effectively served as the contract between tools, which meant they could be implemented and tested in isolation without one tool needing to know how another was built.

**One divergence from the spec, and why:**

The spec described the planning loop's query parser as using "regex to extract description, size, and price" but didn't specify how to handle overlapping stop phrases. The initial implementation stripped "for" before "looking for," which left "looking" as a stray keyword in the description. That word then got scored against every listing that contained "looking" in its text, pushing wrong results to the top — a khaki trouser ended up as the top hit for "vintage graphic tee." The fix was to apply all stop phrases in longest-first order so multi-word phrases are consumed before their component words can be stripped individually. This detail wasn't in the spec because it only surfaced during end-to-end testing, not planning.

---

## AI Usage

**Instance 1 — `search_listings` implementation.**
I gave Claude the Tool 1 block from `planning.md` (inputs with types, return value field list, failure mode) and the `load_listings()` docstring from `data_loader.py`, and asked it to implement the function. Claude produced working filter logic and a scoring loop using `kw in searchable` (substring matching). Before accepting it I verified it handled all three filter combinations and returned an empty list on no results rather than raising. I then changed the scoring from substring to whole-word regex (`re.search(r'\b...\b', searchable)`) after observing in end-to-end testing that short keywords were spuriously matching inside longer words and inflating scores for unrelated listings.

**Instance 2 — Planning loop (`run_agent`) implementation.**
I gave Claude the full Architecture ASCII diagram from `planning.md` plus the Planning Loop and State Management spec sections, and asked it to implement `run_agent()`. Claude produced a loop that matched the diagram — linear tool calls with an early return on empty results. Before using it I confirmed the code checked `if not results:` before proceeding to `suggest_outfit`, which was the critical correctness requirement. I rewrote the price regex from `r'\$?\b(\d+)\b'` (which could match bare numbers ambiguously) to `r'\$(\d+)\b|\bunder\s+(\d+)\b'` — requiring either a dollar sign or the word "under" — because the looser pattern was risky in queries that contain other numbers. I also added the stop-phrase list and rewrote the description-cleaning logic myself after finding that the generated parser left "looking" as a stray keyword that degraded search ranking.
