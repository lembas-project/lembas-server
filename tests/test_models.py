from app.models import User


def test_user_model_serialization():
    user = User(login="something", name="Someone Awesome", avatar_url="https://my-picture")
    data = user.model_dump()
    assert data == {
        "username": "something",
        "name": "Someone Awesome",
        "avatar_url": "https://my-picture",
    }
