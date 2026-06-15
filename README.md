# FitFindr

FitFindr is a small agent that finds a secondhand listing, suggests an outfit using the user’s wardrobe, and turns the result into a shareable fit card.

## How It Works

The agent does not call every tool blindly. It first parses the query into a description, optional size, and optional max price, then runs `search_listings(description, size, max_price)`. If that returns no matches, the run stops immediately with a helpful search tip; if it returns results, the agent selects the top listing, checks whether the wardrobe has any items, and only then calls `suggest_outfit(new_item, wardrobe)` followed by `create_fit_card(outfit, new_item)`.

That means the behavior changes based on input: a good search leads to styling and a fit card, while an impossible search ends early with a search-focused error message. An empty wardrobe also stops the flow before the fit card step so the agent never tries to style from nothing.

## Tool Inventory

### `search_listings(description, size, max_price) -> list[dict]`
- **Purpose:** Search the mock marketplace and return the most relevant matches.
- **Inputs:**
  - `description` (`str`): What the user wants, such as `"vintage graphic tee"`.
  - `size` (`str | None`): Optional size filter, such as `"M"` or `"US 8"`.
  - `max_price` (`float | None`): Optional upper price limit.
- **Outputs:** A list of listing dictionaries sorted by relevance. Each listing contains `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.
- **Failure behavior:** Returns `[]` if nothing matches. Example from testing: `designer ballgown`, `XXS`, `5` returned an empty list without raising an exception.

### `suggest_outfit(new_item, wardrobe) -> str`
- **Purpose:** Suggest a specific outfit using the selected listing and the user’s wardrobe.
- **Inputs:**
  - `new_item` (`dict`): The chosen listing from `search_listings`.
  - `wardrobe` (`dict`): A wardrobe object with an `items` list in the schema from `data/wardrobe_schema.json`.
- **Outputs:** A plain-language outfit suggestion string. When the wardrobe is populated, it should reference specific wardrobe items when possible.
- **Failure behavior:** If `wardrobe["items"]` is empty, it returns a helpful general styling message instead of crashing. Example from testing: with an empty wardrobe, it returned a string explaining that the wardrobe was empty and the user should add items first.

### `create_fit_card(outfit, new_item) -> str`
- **Purpose:** Turn the styling suggestion into a short caption-style fit card.
- **Inputs:**
  - `outfit` (`str`): The suggestion returned by `suggest_outfit`.
  - `new_item` (`dict`): The selected listing dictionary.
- **Outputs:** A social-style caption string that mentions the item, price, platform, and outfit vibe.
- **Failure behavior:** If `outfit` is empty or whitespace-only, it returns a descriptive error string instead of raising an exception. Example from testing: passing `""` returned `"I couldn’t build the fit card because the outfit suggestion is missing."`

## Planning Loop

The planning loop is a strict sequence with branches:

1. Parse the user query into `description`, `size`, and `max_price`.
2. Call `search_listings()` with those values.
3. If the result list is empty, store an error message in the session and stop.
4. If there are results, store `selected_item = results[0]`.
5. Check the wardrobe.
6. If `wardrobe["items"]` is empty, store an error message and stop before styling.
7. If the wardrobe has items, call `suggest_outfit(selected_item, wardrobe)`.
8. If the outfit text is missing, stop with a styling error.
9. Otherwise call `create_fit_card(outfit, selected_item)` and return the finished session.

This loop is what makes the agent feel responsive instead of mechanical: a broad query, a specific query, and a no-results query all produce different control flow.

## State Management

FitFindr uses a session dictionary as the single source of truth for one user interaction. The session stores:

- the original query
- parsed search filters
- `search_results`
- `selected_item`
- `wardrobe`
- `outfit_suggestion`
- `fit_card`
- `error`

The same `selected_item` object is passed from search to outfit generation to fit-card creation. The wardrobe is passed forward unchanged, which made it easy to test both `get_example_wardrobe()` and `get_empty_wardrobe()` without rewriting the agent.

## Error Handling

| Tool | Failure mode | Agent response |
|------|--------------|-----------------|
| `search_listings` | No results match the query | The agent says no listings matched and suggests broadening the description, size, or budget. Example: `designer ballgown size XXS under $5` stops immediately with a search-help message. |
| `suggest_outfit` | Wardrobe is empty | The agent explains that it found an item but needs wardrobe pieces first, then stops before generating a fit card. Example: `get_empty_wardrobe()` returns a useful general styling response instead of crashing. |
| `create_fit_card` | Outfit input is missing or incomplete | The agent returns a descriptive error string and does not fabricate a caption. Example: passing an empty string returns `"I couldn’t build the fit card because the outfit suggestion is missing."` |

## Running The App

```bash
python3 -m pytest tests -q
python3 app.py
```

Then open the URL printed in the terminal. If the environment is missing `gradio` or `groq`, install dependencies from `requirements.txt` in a full local environment first.

## Demo Notes

For the demo, show one happy-path query and one failure-path query.

- Happy path: `vintage graphic tee under $30`
- Failure path: `designer ballgown size XXS under $5`

While narrating the happy path, point out that `selected_item` flows into `suggest_outfit`, and the returned outfit text flows into `create_fit_card`.

## AI Usage

I used AI in two specific ways:

1. I gave Claude the `Tool 1`, `Tool 2`, and `Tool 3` sections from `planning.md` plus the architecture diagram, and asked it to draft implementation-ready tool logic. I kept the structure but overrode the generated code to match the repo’s actual helper functions and to make the empty-wardrobe and empty-outfit paths return explicit strings.
2. I gave ChatGPT the `Planning Loop`, `State Management`, and `A Complete Interaction` sections from `planning.md`, then asked it to turn them into precise session-flow prose. I kept the branching logic but rewrote the wording so it matched the actual session keys used in `agent.py`.

## Spec Reflection

The first version of the plan was too vague to implement safely, so I tightened it after testing the tools individually. The biggest useful correction was making the planning loop branch on `search_listings` results and the wardrobe contents instead of always calling all three tools.

Another important lesson was that failure handling needs to return usable text, not just “an error happened.” The tests forced me to make the no-results, empty-wardrobe, and empty-outfit paths specific enough that someone can understand what to fix next.

## Data Reference

The listings dataset comes from `data/listings.json`, and each record includes:

- `id` (`str`)
- `title` (`str`)
- `description` (`str`)
- `category` (`str`)
- `style_tags` (`list[str]`)
- `size` (`str`)
- `condition` (`str`)
- `price` (`float`)
- `colors` (`list[str]`)
- `brand` (`str | None`)
- `platform` (`str`)

The wardrobe schema lives in `data/wardrobe_schema.json`. Use `get_example_wardrobe()` for normal happy-path testing and `get_empty_wardrobe()` to verify the empty-wardrobe branch.
