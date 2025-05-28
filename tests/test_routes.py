import pytest
from flask import g
from werkzeug.exceptions import Forbidden, NotFound
from unittest.mock import patch, MagicMock
from Management_system import app
from Management_system.routes import page_not_found

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def mock_user():
    user = MagicMock()
    user.name = "TestUser"
    user.email = "user@test.lt"
    user.phone_number = "+37060000000"
    user.password = "$2b$12$sf3kmsej334jd"
    user.is_verified = True
    return user

@pytest.fixture
def mock_form():
    form = MagicMock()
    form.validate_on_submit.return_value = True
    form.current_password.data = "wrongpassword"
    form.email.data = "user@test.lt"
    form.phone_number.data = "+37060000000"
    form.new_password.data = ""
    form.confirm_password.data = ""
    return form

def test_redirect_to_default_language(client):
    response = client.get('/')
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/en/login")

def test_login_route(client):
    response = client.get('/en/login')
    assert response.status_code == 200
    assert b"<form" in response.data

def test_post_incorrect_password(client, mock_user, mock_form):
    with patch("Management_system.routes.current_user", mock_user), \
         patch("Management_system.routes.UserSettingsForm", return_value=mock_form), \
         patch("Management_system.routes.bcrypt.check_password_hash", return_value=False), \
         patch("Management_system.routes.log_user_action") as mock_log:

        response = client.post("/en/user_settings", data={})
        
        assert response.status_code == 302


def test_404_handler_direct_call():
    with app.test_request_context("/fake404"):
        setattr(g, "tr", {"404_text": "Page not found"})

        html, status_code = page_not_found(NotFound())
        assert status_code == 404
        assert "404" in html

def test_403_error_handler(client):
    with app.test_request_context("/fake403"):
        html, status_code = app.handle_user_exception(Forbidden())

        assert status_code == 403
