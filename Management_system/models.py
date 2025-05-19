from flask import redirect
from flask_admin import BaseView, expose
from flask_login import UserMixin, current_user

from . import db, login_manager, admin, lang_url_for
from flask_admin.contrib.sqla import ModelView
from datetime import datetime



class Client(db.Model):
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


class Machine(db.Model):
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


class Service(db.Model):
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
    one_time_links = db.relationship("OneTimeLink", back_populates="user", cascade="all, delete-orphan")


class PartsReplaced(db.Model):
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


class Inventory(db.Model):
    __tablename__ = "inventory"

    id = db.Column(db.Integer, primary_key=True, index=True)
    part_id = db.Column(db.Integer, db.ForeignKey("parts.id"), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey("locations.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    part = db.relationship("Part", back_populates="inventory")
    location = db.relationship("Location", back_populates="inventory")
    parts_replaced = db.relationship("PartsReplaced", back_populates="inventory")


class Location(db.Model):
    __tablename__ = "locations"

    id = db.Column(db.Integer, primary_key=True, index=True)
    location_en = db.Column(db.String, nullable=False)
    location_lt = db.Column(db.String, nullable=False)

    inventory = db.relationship("Inventory", back_populates="location")


class Debt(db.Model):
    __tablename__ = "debts"

    id = db.Column(db.Integer, primary_key=True, index=True)
    part_id = db.Column(db.Integer, db.ForeignKey("parts.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    machine_id = db.Column(db.Integer, db.ForeignKey("machines.id"), nullable=False)

    part = db.relationship("Part", back_populates="debts")
    machine = db.relationship("Machine", back_populates="debts")

class MachineType(db.Model):
    __tablename__ = "machine_types"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)

    machines = db.relationship("Machine", back_populates="machine_type")
    parts = db.relationship("Part", secondary="part_machine_types", back_populates="machine_types")

class Task(db.Model):
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
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    purpose = db.Column(db.Text)

    client = db.relationship("Client", back_populates="visits")

class OneTimeLink(db.Model):
    __tablename__ = "one_time_links"
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String, unique=True, nullable=False)
    purpose = db.Column(db.String, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    user = db.relationship("User", back_populates="one_time_links")

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class AdminModelView(ModelView):
    def is_accessible(self):
        return (current_user.is_authenticated and current_user.email == "admin@admin.lt"
                or current_user.is_admin)

class RedirectHomeView(BaseView):
    @expose('/')
    def index(self):
        return redirect(lang_url_for('index'))

    def is_accessible(self):
        return (current_user.is_authenticated and current_user.email == "admin@admin.lt"
                or current_user.is_admin)

admin.add_view(RedirectHomeView(name='Index'))

tables = [Machine, Client, Service, User, PartsReplaced, Part, Location,
          Debt, MachineType, Task, Visit]
for table in tables:
    admin.add_view(AdminModelView(table, db.session))

