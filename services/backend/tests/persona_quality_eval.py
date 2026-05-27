from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_affection_reply_is_natural_and_readable():
    response = client.post("/api/chat", json={"message": "我喜欢你", "session_id": "quality-affection"})

    assert response.status_code == 200
    reply = response.json()["reply"]
    assert 2 <= len(reply) <= 80
    assert any("\u4e00" <= char <= "\u9fff" for char in reply)
    assert "......" not in reply
    assert not reply.startswith("......")
    assert not reply.startswith("……嗯")
    assert "我在。慢慢说" not in reply
    assert "只是没什么需要说" not in reply
    assert "手在抖" not in reply
    assert not any(phrase in reply for phrase in ("作为 AI", "作为AI", "请问", "有什么可以帮助你"))
    assert any(marker in reply for marker in ("听见", "突然", "知道", "记得"))
