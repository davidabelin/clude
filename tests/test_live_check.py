"""Regression checks for the deployed-service acceptance client."""

from scripts import clude_live_check


class _ReplayResponse:
    status_code = 200
    text = '<script id="replay-data" type="application/json"></script>'


class _Client:
    def __init__(self, name):
        self.name = name
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        return _ReplayResponse()


def test_live_check_declines_final_comments_before_opening_replay(monkeypatch):
    first, second = _Client("first"), _Client("second")
    declined = []

    def decline(client, base, table_id):
        declined.append((client.name, base, table_id))
        closed = len(declined) == 2
        return {
            "final_comments": {"closed": closed, "seconds": 20},
            "over": {"replay": "/replay/web-2/7" if closed else None},
        }

    monkeypatch.setattr(clude_live_check, "decline_final_comment", decline)
    result = clude_live_check.verify_replay(
        "https://example.test",
        "table-id",
        {"first": first, "second": second},
        {"final_comments": {"closed": False, "seconds": 20}, "over": {"replay": None}},
    )

    assert [row[0] for row in declined] == ["first", "second"]
    assert result["over"]["replay"] == "/replay/web-2/7"
    assert first.urls == ["https://example.test/replay/web-2/7"]
