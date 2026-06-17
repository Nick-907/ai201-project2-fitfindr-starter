# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
It scans the mock listings dataset and returns secondhand items that match the user's description, filtered by size and price ceiling. Think of it as the search bar — it's always the first thing called when a user says they're looking for something.

**Input parameters:**
- `description` (str): A freeform text description of what the user wants, like "vintage graphic tee" or "oversized denim jacket" — used for keyword scoring against listing titles, descriptions, and style tags.
- `size` (str): The size to filter by (e.g., "M", "L"), or None to skip size filtering entirely — matching is case-insensitive so "s/m" still catches "S/M".
- `max_price` (float): The highest price the user is willing to pay (inclusive), or None if there's no budget constraint.

**What it returns:**
A list of listing dicts sorted best-match-first, where each dict contains: `id`, `title`, `description`, `category`, `style_tags` (list), `size`, `condition`, `price`, `colors` (list), `brand`, and `platform`. Returns an empty list if nothing matches — never raises an exception.

**What happens if it fails or returns nothing:**
If the list comes back empty, the agent tells the user no listings matched their criteria and asks them to try broader keywords, a different size, or a higher price — it does not attempt to call suggest_outfit or create_fit_card on an empty result.

---

### Tool 2: suggest_outfit

**What it does:**
Given a thrifted item the user is considering and their existing wardrobe, it calls an LLM to suggest 1–2 complete outfits that incorporate both. It's triggered immediately after search_listings returns a result the user wants to explore.

**Input parameters:**
- `new_item` (dict): The full listing dict for the item the user picked (passed straight from search_listings output), so the LLM knows the item's style, category, and colors.
- `wardrobe` (dict): A dict with an `items` key holding a list of the user's existing clothing — can be the example wardrobe or an empty one if the user is starting from scratch.

**What it returns:**
A non-empty string containing 1–2 outfit suggestions written in plain English, naming specific wardrobe pieces and describing how they pair with the new item.

**What happens if it fails or returns nothing:**
If the wardrobe is empty, the tool falls back to general styling advice for the item (vibe, what it pairs well with generically) rather than failing — if the LLM call itself errors, the agent returns a message saying styling suggestions are unavailable and still passes the item info to create_fit_card.

---

### Tool 3: create_fit_card

**What it does:**
It takes the outfit suggestion and the item details and asks an LLM to generate a short, casual caption — the kind of thing you'd actually post on Instagram or TikTok with a thrift haul. It's the last step in every interaction, called right after suggest_outfit completes.

**Input parameters:**
- `outfit` (str): The outfit suggestion string returned by suggest_outfit — this is the styling context the LLM uses to capture the vibe of the caption.
- `new_item` (dict): The listing dict for the thrifted item, so the caption can naturally mention the item name, price, and platform.

**What it returns:**
A 2–4 sentence string written in a casual, authentic OOTD voice that mentions the item name, price, and platform once each and captures the specific vibe of the outfit.

**What happens if it fails or returns nothing:**
If `outfit` is empty or whitespace-only, the tool skips the LLM call and returns a descriptive error string rather than raising an exception, so the agent can still surface something useful to the user.

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
The agent always starts with search_listings using the description, size, and price pulled from the user's message — if that returns results, it picks the best match and calls suggest_outfit with that item plus the session wardrobe, then immediately calls create_fit_card with the outfit string and item to close the loop. If search_listings returns empty, the loop stops there and the agent responds with a "nothing found" message; if suggest_outfit fails or returns empty, create_fit_card is still called but with a fallback outfit string so the user always gets some output.

---

## State Management

**How does information from one tool get passed to the next?**
Within a session, the agent keeps a small in-memory state dict that holds the current `listings` (the full results from search_listings), the `selected_item` (whichever listing the user picks or the top result), the `wardrobe` (loaded once at session start from the example wardrobe), and the `outfit` string from suggest_outfit. Each tool call reads from and writes to this dict, so the selected_item flows into suggest_outfit and then both the outfit string and selected_item flow into create_fit_card without any re-fetching.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | The agent tells the user nothing matched and asks them to broaden their search (looser keywords, different size, or higher price) — the loop stops and the other two tools are not called. |
| suggest_outfit | Wardrobe is empty | The tool switches to general styling advice for the item (what categories and aesthetics pair well) instead of referencing specific wardrobe pieces, so the user still gets useful output rather than an error. |
| create_fit_card | Outfit input is missing or incomplete | The tool returns a descriptive error string (not an exception) noting that the caption couldn't be generated, and the agent surfaces that message to the user rather than crashing. |

---

## Architecture

```
User query: "vintage graphic tee under $30, baggy jeans + chunky sneakers"
    │
    ▼
Planning Loop
    │  extracts: description="vintage graphic tee", size=None, max_price=30.0
    │
    ├─► search_listings(description, size, max_price)
    │       │                               ┌─── Session State ───────────────────┐
    │       │ results = []                  │  wardrobe   (loaded at session start)│
    │       ├──► [STOP] "No listings found  │  listings   (set after search)       │
    │       │    for those filters. Try     │  selected_item (set after search)    │
    │       │    broader keywords or a      │  outfit     (set after suggest)      │
    │       │    higher price." → return    │  fit_card   (set after create)       │
    │       │                               └─────────────────────────────────────┘
    │       │ results = [item1, item2, ...]         ▲         ▲         ▲
    │       ▼                                       │         │         │
    │   Session: listings = results                 │         │         │
    │            selected_item = results[0] ────────┘         │         │
    │                                                          │         │
    ├─► suggest_outfit(selected_item, wardrobe) ───────────────┘         │
    │       │                                                             │
    │       │ wardrobe['items'] == []                                     │
    │       ├──► [FALLBACK] LLM prompt for general styling advice         │
    │       │    (no wardrobe pieces named, no error raised)              │
    │       │                                                             │
    │       │ wardrobe has items                                          │
    │       ├──► LLM prompt with wardrobe pieces + new_item               │
    │       │                                                             │
    │       ▼                                                             │
    │   Session: outfit = "Pair with your wide-leg jeans and..."          │
    │                                                                     │
    └─► create_fit_card(outfit, selected_item) ───────────────────────────┘
            │
            │ outfit == "" or whitespace
            ├──► [STOP] return "Couldn't generate a fit card —
            │    outfit suggestion was empty." (no exception raised)
            │
            │ outfit has content
            ├──► LLM prompt for casual OOTD caption
            │
            ▼
        Session: fit_card = "Thrifted this $24 band tee off Depop..."
            │
            ▼
    Return to user: listings summary + outfit suggestion + fit card caption
```

---

## AI Tool Plan

**Milestone 3 — Individual tool implementations:**

For `search_listings`, I'll give Claude the Tool 1 block (inputs, return value, failure mode) and the `data_loader.py` docstring, then ask it to implement the function using `load_listings()` — specifically to filter by `max_price` and `size` first, then score by keyword overlap against `title`, `description`, and `style_tags`, drop zero-score results, and sort descending. Before accepting the output I'll check that it handles all three filter combinations (both params, one param, neither) and run it against at least three queries — one that should return results, one that returns empty due to price, and one with a size that doesn't exist in the data.

For `suggest_outfit`, I'll paste the Tool 2 block plus the wardrobe schema from `data_loader.py` into Claude and ask it to write the function with two branches: an empty-wardrobe prompt path and a wardrobe-items prompt path. I'll verify the generated code actually checks `len(wardrobe['items']) == 0` before building the prompt, and I'll run it once with the example wardrobe and once with an empty one to confirm both paths return a non-empty string.

For `create_fit_card`, I'll give Claude the Tool 3 block and ask it to implement the guard clause first (empty/whitespace outfit → return error string, no exception), then build the LLM prompt that includes item name, price, platform, and the outfit string, requesting a casual 2–4 sentence OOTD caption at a higher temperature. I'll test it with a real outfit string and confirm the caption mentions name, price, and platform exactly once, then test the guard clause with an empty string to confirm it returns an error message without crashing.

**Milestone 4 — Planning loop and state management:**

I'll give Claude the Architecture diagram from this file plus the State Management section and ask it to implement the planning loop in `agent.py` as a function that: (1) calls `search_listings` with extracted params, (2) checks if results is empty and returns early with the "no listings found" message if so, (3) sets `selected_item = results[0]` in session state, (4) calls `suggest_outfit`, (5) calls `create_fit_card`, and (6) returns the assembled session. I'll verify the generated loop matches the diagram's control flow by tracing through it manually with a mock that returns an empty list from `search_listings` and confirming the other two tools are never called in that case.

---

## A Complete Interaction (Step by Step)

FitFindr is a shopping and styling agent that helps users find secondhand clothing and see how it fits into their existing wardrobe. When a user describes what they want, the agent searches listings, then uses the returned item to generate an outfit suggestion against the user's wardrobe, and finally produces a shareable fit card — each tool's output feeding directly into the next. If any tool fails or returns nothing (no matching listings, an empty wardrobe, or incomplete outfit data), the agent surfaces a plain-language message and stops rather than passing bad data downstream.

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
The agent parses the query and calls `search_listings(description="vintage graphic tee", size=None, max_price=30.0)`. Size is None because the user didn't specify one. The function loads all listings, drops anything over $30, scores the rest by how many of the words "vintage", "graphic", "tee" appear in each listing's title, description, and style_tags, then returns the matches sorted highest-score-first — let's say it returns 4 results, with a $24 band tee from Depop at the top. The agent sets `session["listings"] = results` and `session["selected_item"] = results[0]`.

**Step 2:**
With a result in hand, the agent calls `suggest_outfit(new_item=selected_item, wardrobe=session["wardrobe"])`. The wardrobe was loaded from `get_example_wardrobe()` at session start and has 10 items including wide-leg jeans and white low-top sneakers, which maps well to what the user described. The LLM receives a prompt listing those wardrobe items alongside the new band tee's category (tops), colors (black, white), and style_tags (vintage, graphic, streetwear), and responds with something like: "Outfit 1: Tuck the band tee into your wide-leg jeans and add the white low-top sneakers for an easy streetwear look. Outfit 2: Leave it untucked over biker shorts with chunky boots for a grungier vibe." The agent stores this in `session["outfit"]`.

**Step 3:**
The agent calls `create_fit_card(outfit=session["outfit"], new_item=selected_item)`. The outfit string is non-empty so the guard clause passes, and the LLM generates a casual 2–4 sentence OOTD caption at a higher temperature — something like: "Grabbed this vintage band tee for $24 off Depop and it goes with literally everything. Styled it tucked into wide-legs with my low-tops and I haven't taken it off since. Thrift finds > retail, always." The agent stores this in `session["fit_card"]`.

**Final output to user:**
The user sees three things in the response: (1) a short listing summary showing the top results with title, price, condition, and platform; (2) the outfit suggestions from step 2, giving them concrete styling ideas using their actual wardrobe pieces; and (3) the fit card caption from step 3, ready to copy and post. If they want to explore a different result from the list, they can ask and the agent re-runs steps 2 and 3 with that item as `selected_item`.
