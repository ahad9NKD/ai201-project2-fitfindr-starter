import agent


def test_run_agent_happy_path_passes_state_between_tools(monkeypatch):
    selected_item = {
        "id": "lst_006",
        "title": "Graphic Tee — 2003 Tour Bootleg Style",
        "description": "Vintage-style bootleg tee with faded graphic.",
        "category": "tops",
        "style_tags": ["graphic tee", "vintage", "grunge"],
        "size": "M",
        "condition": "good",
        "price": 24.0,
        "colors": ["black"],
        "brand": None,
        "platform": "depop",
    }
    received = {}

    def fake_search_listings(description, size=None, max_price=None):
        received["search_args"] = (description, size, max_price)
        return [selected_item]

    def fake_suggest_outfit(new_item, wardrobe):
        received["selected_item_id"] = id(new_item)
        received["wardrobe_id"] = id(wardrobe)
        assert new_item is selected_item
        return "Pair it with baggy jeans and chunky sneakers."

    def fake_create_fit_card(outfit, new_item):
        received["outfit_arg"] = outfit
        received["fit_card_item_id"] = id(new_item)
        assert outfit == "Pair it with baggy jeans and chunky sneakers."
        assert new_item is selected_item
        return "fit card caption"

    monkeypatch.setattr(agent, "search_listings", fake_search_listings)
    monkeypatch.setattr(agent, "suggest_outfit", fake_suggest_outfit)
    monkeypatch.setattr(agent, "create_fit_card", fake_create_fit_card)

    wardrobe = {"items": [{"id": "w_001", "name": "Baggy jeans"}]}
    session = agent.run_agent("vintage graphic tee under $30, size M", wardrobe)

    assert session["error"] is None
    assert session["parsed"] == {
        "description": "vintage graphic tee",
        "size": "M",
        "max_price": 30.0,
    }
    assert session["search_results"] == [selected_item]
    assert session["selected_item"] is selected_item
    assert session["outfit_suggestion"] == "Pair it with baggy jeans and chunky sneakers."
    assert session["fit_card"] == "fit card caption"
    assert received["search_args"] == ("vintage graphic tee", "M", 30.0)
    assert received["selected_item_id"] == id(selected_item)
    assert received["fit_card_item_id"] == id(selected_item)
    assert received["outfit_arg"] == "Pair it with baggy jeans and chunky sneakers."


def test_run_agent_no_results_stops_before_outfit(monkeypatch):
    called = {"suggest_outfit": False, "create_fit_card": False}

    def fake_search_listings(description, size=None, max_price=None):
        return []

    def fake_suggest_outfit(new_item, wardrobe):
        called["suggest_outfit"] = True
        return "should not be used"

    def fake_create_fit_card(outfit, new_item):
        called["create_fit_card"] = True
        return "should not be used"

    monkeypatch.setattr(agent, "search_listings", fake_search_listings)
    monkeypatch.setattr(agent, "suggest_outfit", fake_suggest_outfit)
    monkeypatch.setattr(agent, "create_fit_card", fake_create_fit_card)

    session = agent.run_agent("designer ballgown size XXS under $5", {"items": []})

    assert session["error"] is not None
    assert "No listings matched" in session["error"]
    assert session["search_results"] == []
    assert session["selected_item"] is None
    assert session["outfit_suggestion"] is None
    assert session["fit_card"] is None
    assert called["suggest_outfit"] is False
    assert called["create_fit_card"] is False
