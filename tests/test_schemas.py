from app.schemas import User


def test_user_model_serialization() -> None:
    user = User(username="something", avatar_url="https://my-picture")
    data = user.model_dump()
    assert data == {
        "username": "something",
        "avatar_url": "https://my-picture",
    }
