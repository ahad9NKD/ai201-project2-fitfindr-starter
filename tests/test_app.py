import app


def test_handle_query_empty_query():
    listing_text, outfit_text, fit_card_text = app.handle_query("", "Example wardrobe")

    assert listing_text == "Please enter a search query."
    assert outfit_text == ""
    assert fit_card_text == ""


def test_handle_query_formats_success(monkeypatch):
    fake_session = {
        "error": None,
        "selected_item": {
            "title": "Vintage Band Tee",
            "price": 24.0,
            "platform": "depop",
            "condition": "good",
        },
        "outfit_suggestion": "Pair it with baggy jeans.",
        "fit_card": "thrifted caption",
    }

    monkeypatch.setattr(app, "run_agent", lambda query, wardrobe: fake_session)

    listing_text, outfit_text, fit_card_text = app.handle_query(
        "vintage graphic tee under $30",
        "Example wardrobe",
    )

    assert listing_text == "Vintage Band Tee — $24.00, depop, Good condition"
    assert outfit_text == "Pair it with baggy jeans."
    assert fit_card_text == "thrifted caption"


def test_handle_query_returns_error_first_panel(monkeypatch):
    fake_session = {
        "error": "No listings matched your search.",
        "selected_item": None,
        "outfit_suggestion": None,
        "fit_card": None,
    }

    monkeypatch.setattr(app, "run_agent", lambda query, wardrobe: fake_session)

    listing_text, outfit_text, fit_card_text = app.handle_query(
        "designer ballgown size XXS under $5",
        "Example wardrobe",
    )

    assert listing_text == "No listings matched your search."
    assert outfit_text == ""
    assert fit_card_text == ""
