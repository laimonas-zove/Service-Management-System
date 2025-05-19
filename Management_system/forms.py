from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, SubmitField, TelField, EmailField,
                     DateField, IntegerField, SelectField, DecimalField, TextAreaField,
                     HiddenField, SelectMultipleField, FormField, FieldList)
from wtforms.validators import DataRequired, Optional, EqualTo
from wtforms.widgets.core import CheckboxInput, ListWidget

from .models import Client, MachineType, Location

class UserSettingsForm(FlaskForm):
    phone_number = StringField('Phone Number', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired()])
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[Optional()])
    confirm_password = PasswordField('Confirm Password')
    submit = SubmitField('Save Changes')

class LoginForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log In")

class RegistrationForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    surname = StringField("Surname", validators=[DataRequired()])
    phone_number = TelField("Phone Number", validators=[DataRequired()])
    email = EmailField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    confirm_password = PasswordField("Repeat Password", validators=[DataRequired()])
    submit = SubmitField("Register")

class TokenSendForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired()])
    submit = SubmitField("Send")

class ResetPasswordForm(FlaskForm):
    password = PasswordField("Password", validators=[DataRequired()])
    confirm_password = PasswordField("Repeat Password", validators=[DataRequired()])
    submit = SubmitField("Reset Password")

class MachineForm(FlaskForm):
    serial_number = StringField("Serial Number", validators=[DataRequired()])
    type = SelectField("Machine Type", coerce=int, validators=[DataRequired()])
    start_of_operation = DateField("Start of Operation",validators=[DataRequired()])
    warranty = IntegerField("Years of Warranty", validators=[DataRequired()])
    client = SelectField("Client", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Submit")

    def __init__(self, *args, **kwargs):
        super(MachineForm, self).__init__(*args, **kwargs)
        self.type.choices = [
            (type.id, f"{type.name}")
            for type in MachineType.query.all()]

        self.client.choices = [
            (client.id, f"{client.company} - {client.city}")
            for client in Client.query.all()]

class ClientForm(FlaskForm):
    company = StringField("Company Name", validators=[DataRequired()])
    address = StringField("Company Address", validators=[DataRequired()])
    city = StringField("City", validators=[DataRequired()])
    contact_person = StringField("Contact Person", validators=[DataRequired()])
    phone_number = TelField("Phone Number", validators=[DataRequired()])
    email = EmailField("Email", validators=[DataRequired()])
    submit = SubmitField("Submit")

class ServiceForm(FlaskForm):
    date = DateField("Date", validators=[DataRequired()])
    serial_number = StringField("Machine S/n", validators=[DataRequired()])
    bn_count = IntegerField("Banknote count", validators=[DataRequired()])
    note = TextAreaField("Note")
    submit = SubmitField("Submit")

class InventoryEntryForm(FlaskForm):
    location_id = HiddenField("Location ID")
    quantity = IntegerField("Quantity", validators=[Optional()])

    class Meta:
        csrf = False

class PartForm(FlaskForm):
    part_number = StringField("Part Number", validators=[DataRequired()])
    name_en = StringField("Name EN", validators=[DataRequired()])
    name_lt = StringField("Name LT", validators=[DataRequired()])
    price = DecimalField("Price", validators=[DataRequired()])
    machine_types = SelectMultipleField(
        "Compatible Machine Types",
        coerce=int,
        option_widget=CheckboxInput(),
        widget=ListWidget(prefix_label=False),
        validators=[DataRequired()]
    )
    inventory_entries = FieldList(FormField(InventoryEntryForm), min_entries=0)
    submit = SubmitField("Submit")

    def __init__(self, *args, **kwargs):
        super(PartForm, self).__init__(*args, **kwargs)
        self.machine_types.choices = [(machine_type.id, machine_type.name) for
                                      machine_type in MachineType.query.all()]

        locations = Location.query.all()
        if not self.inventory_entries.data:
            for location in locations:
                self.inventory_entries.append_entry({
                    'location_id': location.id,
                    'quantity': 0
                })

class ReplacedPartForm(FlaskForm):
    date = DateField("Date", validators=[DataRequired()])
    part_number = StringField("Part Number", validators=[DataRequired()])
    quantity = IntegerField("Quantity", validators=[DataRequired()])
    serial_number = StringField("Serial Number", validators=[DataRequired()])
    location = SelectField('Location', validators=[DataRequired()], choices=[])
    submit = SubmitField("Submit")

class PartsReportForm(FlaskForm):
    client = SelectField('Client', coerce=int, validators=[DataRequired()])
    date_from = DateField("Date From", validators=[DataRequired()])
    date_to = DateField("Date To", validators=[DataRequired()])
    submit = SubmitField("Submit")

    def __init__(self, *args, **kwargs):
        super(PartsReportForm, self).__init__(*args, **kwargs)
        self.client.choices = [
            (client.id, f"{client.company} - {client.city}")
            for client in Client.query.all()]

class ServiceReportForm(FlaskForm):
    client = SelectField('Client', coerce=int, validators=[DataRequired()])
    submit = SubmitField("Submit")

    def __init__(self, *args, **kwargs):
        super(ServiceReportForm, self).__init__(*args, **kwargs)
        self.client.choices = [
            (client.id, f"{client.company} - {client.city}")
            for client in Client.query.all()]

class TaskForm(FlaskForm):
    task = TextAreaField("Task", validators=[DataRequired()])
    submit = SubmitField("Submit")

class VisitForm(FlaskForm):
    client = SelectField('Client', coerce=int, validators=[DataRequired()])
    date = DateField('Visit Date', validators=[DataRequired()])
    purpose = TextAreaField('Purpose')
    submit = SubmitField('Save')

    def __init__(self, *args, **kwargs):
        super(VisitForm, self).__init__(*args, **kwargs)
        self.client.choices = [
            (client.id, f"{client.company} - {client.city}")
            for client in Client.query.all()]

