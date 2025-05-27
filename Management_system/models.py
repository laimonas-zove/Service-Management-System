from flask import redirect, Response
from flask_admin import BaseView, expose
from flask_login import UserMixin, current_user
from typing import Optional
from . import db, login_manager, admin, lang_url_for
from sqlalchemy.orm import configure_mappers
from flask_admin.contrib.sqla import ModelView
from datetime import datetime


class Client(db.Model):
    """Represents a client company with associated machines and visits."""
    __tablename__ = "clients"

    id = db.Column(db.Integer, primary_key=True, index=True)
    company = db.Column(db.String, nullable=False)
    address = db.Column(db.String, nullable=False)
    city = db.Column(db.String, nullable=False)
    contact_person = db.Column(db.String, nullable=False)
    phone_number = db.Column(db.String, unique=True, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)

    machines = db.relationship("Machine", back_populates="client")
    visits = db.relationship("Visit", back_populates="client")

    def __str__(self) -> str:
        return f"{self.company} - {self.city}"

class Machine(db.Model):
    """Represents a machine owned by a client."""
    __tablename__ = "machines"

    id = db.Column(db.Integer, primary_key=True, index=True)
    serial_number = db.Column(db.String, unique=True, nullable=False)
    start_of_operation = db.Column(db.Date, nullable=False)
    end_of_warranty = db.Column(db.Date, nullable=False)
    machine_type_id = db.Column(db.Integer, db.ForeignKey("machine_types.id"), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    client = db.relationship("Client", back_populates="machines")
    machine_type = db.relationship("MachineType", back_populates="machines")
    services = db.relationship("Service", back_populates="machine")
    parts_replaced = db.relationship("PartsReplaced", back_populates="machine")
    debts = db.relationship("Debt", back_populates="machine")

    def __str__(self) -> str:
        return self.serial_number

class Service(db.Model):
    """Represents a service record for a machine."""
    __tablename__ = "services"

    id = db.Column(db.Integer, primary_key=True, index=True)
    date = db.Column(db.Date, nullable=False)
    machine_id = db.Column(db.Integer, db.ForeignKey("machines.id"), nullable=False)
    bn_count = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    note = db.Column(db.String)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    machine = db.relationship("Machine", back_populates="services")
    user = db.relationship("User", back_populates="services")

class User(UserMixin, db.Model):
    """Represents a user of the system."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, index=True)
    name = db.Column(db.String, nullable=False)
    surname = db.Column(db.String, nullable=False)
    phone_number = db.Column(db.String, unique=True, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_verified = db.Column(db.Boolean, nullable=False, default=True)

    services = db.relationship("Service", back_populates="user", passive_deletes=True)
    parts_replaced = db.relationship("PartsReplaced", back_populates="user", passive_deletes=True)
    created_tasks = db.relationship("Task", back_populates="created_by_user", foreign_keys="Task.user_id", passive_deletes=True)

    def __str__(self) -> str:
        return self.name
class PartsReplaced(db.Model):
    """Tracks parts replaced during service of a machine."""
    __tablename__ = "parts_replaced"

    id = db.Column(db.Integer, primary_key=True, index=True)
    date = db.Column(db.Date, nullable=False)
    part_id = db.Column(db.Integer, db.ForeignKey("parts.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    machine_id = db.Column(db.Integer, db.ForeignKey("machines.id"), nullable=False)
    warranty = db.Column(db.Boolean, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    inventory_id = db.Column(db.Integer, db.ForeignKey("inventory.id"), nullable=False)

    part = db.relationship("Part", back_populates="parts_replaced")
    machine = db.relationship("Machine", back_populates="parts_replaced")
    inventory = db.relationship("Inventory", back_populates="parts_replaced")
    user = db.relationship("User", back_populates='parts_replaced')

part_machine_types = db.Table(
    "part_machine_types",
    db.Column("part_id", db.Integer, db.ForeignKey("parts.id"), primary_key=True),
    db.Column("machine_type_id", db.Integer, db.ForeignKey("machine_types.id"), primary_key=True)
)

class Part(db.Model):
    """Represents a replaceable part used in machines."""
    __tablename__ = "parts"

    id = db.Column(db.Integer, primary_key=True, index=True)
    part_number = db.Column(db.String, unique=True, nullable=False)
    name_en = db.Column(db.String, nullable=False)
    name_lt = db.Column(db.String, nullable=False)
    price = db.Column(db.Float, nullable=False)

    parts_replaced = db.relationship("PartsReplaced", back_populates="part")
    inventory = db.relationship("Inventory", back_populates="part")
    debts = db.relationship("Debt", back_populates="part")
    machine_types = db.relationship("MachineType", secondary=part_machine_types, back_populates="parts")

    def __str__(self) -> str:
        return self.part_number

class Inventory(db.Model):
    """Tracks the quantity of parts stored at specific locations."""
    __tablename__ = "inventory"

    id = db.Column(db.Integer, primary_key=True, index=True)
    part_id = db.Column(db.Integer, db.ForeignKey("parts.id"), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey("locations.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    part = db.relationship("Part", back_populates="inventory")
    location = db.relationship("Location", back_populates="inventory")
    parts_replaced = db.relationship("PartsReplaced", back_populates="inventory")

    def __str__(self) -> str:
        return self.location.location_en


class Location(db.Model):
    """Represents a physical location where parts are stored."""
    __tablename__ = "locations"

    id = db.Column(db.Integer, primary_key=True, index=True)
    location_en = db.Column(db.String, nullable=False)
    location_lt = db.Column(db.String, nullable=False)

    inventory = db.relationship("Inventory", back_populates="location")


class Debt(db.Model):
    """Tracks parts that were used but not yet accounted."""
    __tablename__ = "debts"

    id = db.Column(db.Integer, primary_key=True, index=True)
    part_id = db.Column(db.Integer, db.ForeignKey("parts.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    machine_id = db.Column(db.Integer, db.ForeignKey("machines.id"), nullable=False)

    part = db.relationship("Part", back_populates="debts")
    machine = db.relationship("Machine", back_populates="debts")

class MachineType(db.Model):
    """Defines the types of machines."""
    __tablename__ = "machine_types"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)

    machines = db.relationship("Machine", back_populates="machine_type")
    parts = db.relationship("Part", secondary="part_machine_types", back_populates="machine_types")

    def __str__(self) -> str:
        return self.name

class Task(db.Model):
    """Represents a task assigned by a user."""
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    task = db.Column(db.String, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    is_completed = db.Column(db.Boolean, nullable=True, default=False)
    completed_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_by_user = db.relationship("User", foreign_keys=[user_id], back_populates="created_tasks")
    completed_by_user = db.relationship("User", foreign_keys=[completed_by_user_id])

class Visit(db.Model):
    """Represents a client visit record."""
    __tablename__ = "visits"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    purpose = db.Column(db.Text)

    client = db.relationship("Client", back_populates="visits")

class OneTimeLink(db.Model):
    """Stores one-time-use links for actions like registration or password reset."""
    __tablename__ = "one_time_links"

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String, unique=True, nullable=False)
    purpose = db.Column(db.String, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)
    email = db.Column(db.Integer, nullable=False)

@login_manager.user_loader
def load_user(user_id: str) -> Optional[User]:
    """Loads a user from the database using the user ID stored in session."""
    return User.query.get(int(user_id))

class AdminModelView(ModelView):
    """Base admin view that restricts access not authenticated users."""
    def is_accessible(self) -> bool:
        """
        Determine if the current user has access to the admin view.

        Returns:
            bool: True if user is authenticated and an admin, False otherwise.
        """
        return (current_user.is_authenticated and current_user.is_admin)

class RedirectHomeView(BaseView):
    """Custom admin view that redirects to the index page."""
    @expose('/')
    def index(self) -> Response:
        """
        Redirect to the localized index route.

        Returns:
            Response: A Flask redirect response to the index page.
        """
        return redirect(lang_url_for('index'))

    def is_accessible(self) -> bool:
        """
        Determine if the current user can access the redirect view.

        Returns:
            bool: True if user is authenticated and an admin, False otherwise.
        """
        return (current_user.is_authenticated and current_user.email == "admin@admin.lt"
                or current_user.is_admin)
    
class UserAdminView(AdminModelView):
    """Admin view configuration of fields"""
    form_columns = [
        'name',
        'surname',
        'phone_number',
        'email',
        'password',
        'is_admin',
        'is_active',
        'is_verified'
    ]

class MachineAdminView(AdminModelView):
    """Admin view configuration of fields"""
    form_columns = [
        'client',
        'machine_type',
        'serial_number',
        'start_of_operation',
        'end_of_warranty',
        'is_active'
    ]

class ClientAdminView(AdminModelView):
    """Admin view configuration of fields"""
    form_columns = [
        'company',
        'address',
        'city',
        'contact_person',
        'phone_number',
        'email'
    ]

class PartAdminView(AdminModelView):
    """Admin view configuration of fields"""
    form_columns = [
        'part_number',
        'name_en',
        'name_lt',
        'price'
    ]

class LocationAdminView(AdminModelView):
    """Admin view configuration of fields"""
    form_columns = [
        'location_en',
        'location_lt'
    ]


configure_mappers()
admin.add_view(RedirectHomeView(name='Index'))
admin.add_view(UserAdminView(User, db.session))
admin.add_view(MachineAdminView(Machine, db.session))
admin.add_view(ClientAdminView(Client, db.session))
admin.add_view(PartAdminView(Part, db.session))
admin.add_view(LocationAdminView(Location, db.session))

tables = [Service, PartsReplaced, MachineType, OneTimeLink, Task]
for table in tables:
    admin.add_view(AdminModelView(table, db.session))
