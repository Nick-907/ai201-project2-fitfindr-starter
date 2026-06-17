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

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     Use ASCII art or a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html).
     Do NOT embed an image — graders need to read your diagram directly in the file;
     an embedded image or screenshot cannot be evaluated.
     You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**

**Milestone 4 — Planning loop and state management:**

---

## A Complete Interaction (Step by Step)

FitFindr is a shopping and styling agent that helps users find secondhand clothing and see how it fits into their existing wardrobe. When a user describes what they want, the agent searches listings, then uses the returned item to generate an outfit suggestion against the user's wardrobe, and finally produces a shareable fit card — each tool's output feeding directly into the next. If any tool fails or returns nothing (no matching listings, an empty wardrobe, or incomplete outfit data), the agent surfaces a plain-language message and stops rather than passing bad data downstream.

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
<!-- What does the agent do first? Which tool is called? With what input? -->

**Step 2:**
<!-- What happens next? What was returned from step 1? What tool is called now? -->

**Step 3:**
<!-- Continue until the full interaction is complete -->

**Final output to user:**
<!-- What does the user actually see at the end? -->
