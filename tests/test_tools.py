from tools import create_fit_card, search_listings, suggest_outfit


class _FakeMessage:
    def __init__(self, content: str):
        self.content = content


class _FakeChoice:
    def __init__(self, content: str):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str):
        self.choices = [_FakeChoice(content)]


class _RecordingCompletions:
    def __init__(self, responses: list[str]):
        self._responses = list(responses)
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        index = min(len(self.calls) - 1, len(self._responses) - 1)
        return _FakeResponse(self._responses[index])


class _RecordingChat:
    def __init__(self, responses: list[str]):
        self.completions = _RecordingCompletions(responses)


class _RecordingClient:
    def __init__(self, responses: list[str]):
        self.chat = _RecordingChat(responses)


def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0
    assert all(item["price"] <= 50 for item in results)
    assert all("id" in item and "title" in item for item in results)


def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=35)
    assert results
    assert all(item["price"] <= 35 for item in results)


def test_suggest_outfit_empty_wardrobe(monkeypatch):
    def _fail_if_called():
        raise AssertionError("LLM should not be called for an empty wardrobe")

    monkeypatch.setattr("tools._get_groq_client", _fail_if_called)

    message = suggest_outfit(
        new_item={
            "title": "Vintage Band Tee",
            "category": "tops",
            "colors": ["black"],
            "style_tags": ["vintage", "graphic tee"],
            "price": 24.0,
            "platform": "depop",
        },
        wardrobe={"items": []},
    )

    assert "wardrobe is empty" in message.lower()


def test_suggest_outfit_happy_path(monkeypatch):
    client = _RecordingClient(["Pair it with the baggy jeans and sneakers."])
    monkeypatch.setattr("tools._get_groq_client", lambda: client)

    result = suggest_outfit(
        new_item={
            "title": "Vintage Band Tee",
            "category": "tops",
            "colors": ["black"],
            "style_tags": ["vintage", "graphic tee"],
            "price": 24.0,
            "platform": "depop",
        },
        wardrobe={
            "items": [
                {
                    "id": "w_001",
                    "name": "Baggy straight-leg jeans",
                    "category": "bottoms",
                    "colors": ["indigo"],
                    "style_tags": ["baggy", "streetwear"],
                    "notes": "High-waisted",
                }
            ]
        },
    )

    assert result == "Pair it with the baggy jeans and sneakers."
    call = client.chat.completions.calls[0]
    assert call["model"] == "llama-3.3-70b-versatile"
    assert call["temperature"] == 0.7
    assert "Vintage Band Tee" in call["messages"][1]["content"]
    assert "Baggy straight-leg jeans" in call["messages"][1]["content"]


def test_create_fit_card_empty_outfit(monkeypatch):
    def _fail_if_called():
        raise AssertionError("LLM should not be called for an empty outfit")

    monkeypatch.setattr("tools._get_groq_client", _fail_if_called)

    message = create_fit_card(
        outfit="   ",
        new_item={
            "title": "Vintage Band Tee",
            "price": 24.0,
            "platform": "depop",
        },
    )

    assert "outfit suggestion is missing" in message.lower()


def test_create_fit_card_happy_path_and_temperature(monkeypatch):
    client = _RecordingClient(
        [
            "first caption about the fit",
            "second caption about the fit",
        ]
    )
    monkeypatch.setattr("tools._get_groq_client", lambda: client)

    first = create_fit_card(
        outfit="Pair it with baggy jeans and chunky sneakers.",
        new_item={
            "title": "Vintage Band Tee",
            "price": 24.0,
            "platform": "depop",
            "category": "tops",
            "colors": ["black"],
            "style_tags": ["graphic tee"],
        },
    )
    second = create_fit_card(
        outfit="Pair it with baggy jeans and chunky sneakers.",
        new_item={
            "title": "Vintage Band Tee",
            "price": 24.0,
            "platform": "depop",
            "category": "tops",
            "colors": ["black"],
            "style_tags": ["graphic tee"],
        },
    )

    assert first == "first caption about the fit"
    assert second == "second caption about the fit"
    assert first != second
    call = client.chat.completions.calls[0]
    assert call["temperature"] == 0.9
    assert "Vintage Band Tee" in call["messages"][1]["content"]
    assert "Pair it with baggy jeans and chunky sneakers." in call["messages"][1]["content"]
