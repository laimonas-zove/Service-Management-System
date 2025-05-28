import pytest
from unittest.mock import patch, MagicMock
from datetime import date
from Management_system import app
from Management_system.utils import create_default_admin, strip_tags, send_email, generate_link, log_user_action, log_mail_sender, get_month_range


def test_create_default_admin_creates_admin():
    with app.app_context(), \
         patch("Management_system.utils.models.User.query") as mock_query, \
         patch("Management_system.utils.db.session.add") as mock_add, \
         patch("Management_system.utils.db.session.commit") as mock_commit, \
         patch("Management_system.utils.bcrypt.generate_password_hash", return_value=b'hashed'):

        mock_query.filter_by.return_value.first.return_value = None

        create_default_admin()

        mock_add.assert_called_once()
        mock_commit.assert_called_once()

def test_create_default_admin_admin_exists():
    with app.app_context(), \
         patch("Management_system.utils.models.User.query") as mock_query, \
         patch("Management_system.utils.db.session.add") as mock_add, \
         patch("Management_system.utils.db.session.commit") as mock_commit:

        mock_query.filter_by.return_value.first.return_value = MagicMock()

        create_default_admin()

        mock_add.assert_not_called()
        mock_commit.assert_not_called()

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_unauthorized_callback(client):
    with client.session_transaction() as session:
        session.clear()

    response = client.get("/en/user_settings", follow_redirects=False)

    assert response.status_code == 302
    assert "/en/login" in response.headers["Location"]

    with client.session_transaction() as session:
        assert "next" in session
        assert session["next"].endswith("/en/user_settings")

def test_404_handler(client):
    response = client.get("/en/pagedoesnotexist")
    assert response.status_code == 404
    assert b"404" in response.data
    assert b"en" in response.data

def test_strip_tags_removes_html():
    html = "<p>Some <strong>Text</strong></p>"
    result = strip_tags(html)
    assert result == "Some Text"

def test_strip_tags_plain_text():
    text = "Some Text"
    result = strip_tags(text)
    assert result == "Some Text"

def test_strip_tags_empty_str():
    result = strip_tags("")
    assert result == ""


def test_send_email_success():
    with app.app_context(), \
         patch("Management_system.utils.mail.send") as mock_send, \
         patch("Management_system.utils.log_mail_sender") as mock_log:

        send_email("Subject", "admin@test.lt", "<p>Hello</p>")

        mock_send.assert_called_once()
        mock_log.assert_called_once_with(["admin@test.lt"], "Subject", "Sent")

def test_send_email_failed():
    with app.app_context(), \
         patch("Management_system.utils.mail.send", side_effect=Exception("SMTP error")), \
         patch("Management_system.utils.log_mail_sender") as mock_log:

        send_email("Subject", ["admin@test.lt"], "<p>Some Text</p>")

        mock_log.assert_called_once()
        args, _ = mock_log.call_args

        assert args[0] == ["admin@test.lt"]
        assert args[1] == "Subject"
        assert "Failed to send" in args[2]
        assert "SMTP error" in args[2]


def test_generate_link_adds_token_to_db():
    with app.app_context(), \
         patch("Management_system.utils.db.session.add") as mock_add, \
         patch("Management_system.utils.db.session.commit") as mock_commit, \
         patch("Management_system.utils.uuid.uuid4", return_value="test-uuid"), \
         patch("Management_system.utils.OneTimeLink") as mock_OneTimeLink:

        token = generate_link("reset_password", "admin@test.lt")

        assert token == "test-uuid"
        mock_OneTimeLink.assert_called_once()
        mock_add.assert_called_once_with(mock_OneTimeLink())
        mock_commit.assert_called_once()

def test_log_user_action_info_level():
    with patch("Management_system.utils.user_logger.info") as mock_info:
        log_user_action("Laimonas", "Login", "Success")

        mock_info.assert_called_once_with("USER: Laimonas | ACTION: Login | DETAILS: (Success)")

def test_log_user_action_warning_level():
    with patch("Management_system.utils.user_logger.warning") as mock_warning:
        log_user_action("Laimonas", "Failed Login", "Wrong password", level="warning")

        mock_warning.assert_called_once_with("USER: Laimonas | ACTION: Failed Login | DETAILS: (Wrong password)")

def test_log_user_action_without_details():
    with patch("Management_system.utils.user_logger.info") as mock_info:
        log_user_action("Laimonas", "View Dashboard")

        mock_info.assert_called_once_with("USER: Laimonas | ACTION: View Dashboard | DETAILS: ")


def test_log_mail_sender_single_email():
    with patch("Management_system.utils.mail_logger.info") as mock_log:
        log_mail_sender("admin@interatlas.lt", "Subject", "Sent")

        mock_log.assert_called_once_with(
            "TO: admin@interatlas.lt | SUBJECT: Subject | STATUS: Sent"
        )

def test_log_mail_sender_multiple_emails():
    with patch("Management_system.utils.mail_logger.info") as mock_log:
        log_mail_sender(["admin@interatlas.lt", "laimonas@interatlas.lt"], "Subject", "Failed")

        mock_log.assert_called_once_with(
            "TO: ['admin@interatlas.lt', 'laimonas@interatlas.lt'] | SUBJECT: Subject | STATUS: Failed"
        )

def test_get_month_range():
    start, end = get_month_range(2025, 5)
    assert start == date(2025, 5, 1)
    assert end == date(2025, 5, 31)