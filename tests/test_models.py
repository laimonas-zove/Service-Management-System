from unittest.mock import MagicMock, patch
from flask import Response
from Management_system import Client, Machine, User, Part, Inventory, MachineType, app, db
from Management_system.models import load_user, AdminModelView, RedirectHomeView

def test_client_str():
    client = Client(company="Brinks", city="Vilnius")
    result = str(client)
    assert result == "Brinks - Vilnius"

def test_machine_str():
    machine = Machine(serial_number="1234567")
    result = str(machine)
    assert result == "1234567"

def test_user_str():
    user = User(name="Laimonas")
    result = str(user)
    assert result == "Laimonas"

def test_part_str():
    part = Part(part_number="503507011")
    result = str(part)
    assert result == "503507011"

def test_inventory_str():
    inventory = Inventory()
    
    mock_location = MagicMock()
    mock_location.location_en = "Warehouse"
    inventory.location = mock_location

    result = str(inventory)
    assert result == "Warehouse"

def test_machine_type_str():
    machine_type = MachineType(name="BPS C1")
    result = str(machine_type)
    assert result == "BPS C1"


def test_load_user_returns_user():
    mock_user = MagicMock()
    with app.app_context(), \
         patch("Management_system.models.db.session.get", return_value=mock_user):
        
        result = load_user("1")
        assert result == mock_user

def test_load_user_returns_none():
    with app.app_context(), \
         patch("Management_system.models.db.session.get", return_value=None):
        
        result = load_user("999")
        assert result is None

def test_is_accessible_allowed():
    class FakeUser:
        is_authenticated = True
        is_admin = True
    with patch("Management_system.models.current_user", new=FakeUser()):
        view_1 = AdminModelView(User, db.session)
        view_2 = RedirectHomeView(User, db.session)
        assert view_1.is_accessible() is True
        assert view_2.is_accessible() is True

def test_is_accessible_not_authenticated():
    class FakeUser:
        is_authenticated = False
        is_admin = True
    with patch("Management_system.models.current_user", new=FakeUser()):
        view_1 = AdminModelView(User, db.session)
        view_2 = RedirectHomeView(User, db.session)
        assert view_1.is_accessible() is False
        assert view_2.is_accessible() is False

def test_is_accessible_not_admin():
    class FakeUser:
        is_authenticated = True
        is_admin = False
    with patch("Management_system.models.current_user", new=FakeUser()):
        view_1 = AdminModelView(User, db.session)
        view_2 = RedirectHomeView(User, db.session)
        assert view_1.is_accessible() is False
        assert view_2.is_accessible() is False

def test_redirect_home_view_redirects_to_index():
    class FakeUser:
        is_authenticated = True
        is_admin = True
    view = RedirectHomeView()

    with app.test_request_context(), \
         patch("Management_system.models.current_user", new=FakeUser()), \
         patch("Management_system.models.lang_url_for", return_value="/en/index") as mock_url_for:

        response: Response = view.index()

        assert response.status_code == 302
        assert response.location == "/en/index"
        mock_url_for.assert_called_once_with("index")

