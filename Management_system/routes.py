import os
from datetime import datetime

from flask import (
    render_template, redirect, flash, request, abort,
    send_from_directory, g, url_for, session
)
from flask_login import (
    login_user, logout_user, login_required, current_user
)
from sqlalchemy import extract, or_, and_, func, case
from dateutil.relativedelta import relativedelta

from . import app, db, bcrypt, lang_url_for
from .forms import (
    LoginForm, RegistrationForm, MachineForm, ClientForm, ServiceForm,
    PartForm, ReplacedPartForm, PartsReportForm, ServiceReportForm,
    TaskForm, VisitForm, ResetPasswordForm, TokenSendForm, UserSettingsForm
)
from .models import (
    User, Machine, Client, Service, Part, PartsReplaced, Inventory,
    Location, MachineType, Task, Visit, OneTimeLink
)
from .utils import localization, send_email, generate_link, log_user_action


@app.route('/<lang>/user_settings', methods=['GET', 'POST'])
@login_required
@localization
def user_settings(lang):
    form = UserSettingsForm(obj=current_user)
    logout_required = False
    changes = []

    if form.validate_on_submit():
        if not bcrypt.check_password_hash(current_user.password, form.current_password.data):
            log_user_action(
                current_user.name,
                "User_Settings",
                "Incorrect Password",
                level="warning"
            )
            flash(g.tr['flash_wrong_password'], 'error')
            return render_template('authorization/settings.html', form=form)

        if form.new_password.data != form.confirm_password.data:
            log_user_action(
                current_user.name,
                "User_Settings",
                "Password does not match",
                level="warning"
            )
            flash(g.tr['flash_password_not_match'], 'error')
            return render_template('authorization/settings.html', form=form)

        if current_user.phone_number != form.phone_number.data:
            changes.append(
                f"phone_number: '{current_user.phone_number}' → '{form.phone_number.data}'"
            )
            current_user.phone_number = form.phone_number.data

        if current_user.email != form.email.data:
            changes.append(
                f"email: '{current_user.email}' → '{form.email.data}'"
            )
            current_user.email = form.email.data
            current_user.is_verified = False
            logout_required = True

            token = generate_link("email_verification", current_user.id)
            verification_url = lang_url_for("verification", token=token, _external=True)

            send_email(
                subject=g.tr['email_verification_subject'],
                html=render_template("emails/verification.html", url=verification_url),
                recipients=form.email.data
            )

            flash(g.tr['flash_verification_link_sent'], 'success')

        if form.new_password.data:
            changes.append("password: '[changed]'")
            current_user.password = bcrypt.generate_password_hash(
                form.new_password.data
            ).decode('utf-8')
            logout_required = True
            flash(g.tr['flash_password_updated'], 'success')

        db.session.commit()

        for change in changes:
            log_user_action(current_user.name,"User_Settings", change)

        if logout_required:
            log_user_action(current_user.name, "Logout")
            logout_user()
            return redirect(lang_url_for('login'))

        flash(g.tr['flash_settings_updated'], 'success')
        return redirect(lang_url_for('user_settings'))

    return render_template('authorization/settings.html', form=form)

@app.route("/<lang>/register", methods=["GET", "POST"])
@localization
def register(lang):
    token = request.form.get("token") or request.args.get("token")

    if not token:
        flash(g.tr['flash_missing_token'], 'error')
        return redirect(lang_url_for('index'))

    link = OneTimeLink.query.filter_by(
        token=token,
        purpose="registration",
        used=False
    ).first()

    if not link:
        flash(g.tr['flash_invalid_link'], 'error')
        return redirect(lang_url_for('login'))

    if link.expires_at and link.expires_at < datetime.utcnow():
        db.session.commit()
        flash(g.tr['flash_link_expired'], 'error')
        return redirect(lang_url_for('login'))

    form = RegistrationForm()
    form.name.render_kw = {"placeholder": g.tr["placeholder_name"]}
    form.surname.render_kw = {"placeholder": g.tr["placeholder_surname"]}
    form.phone_number.render_kw = {"placeholder": g.tr["placeholder_phone_number"]}
    form.email.render_kw = {"placeholder": g.tr["placeholder_email"]}
    form.password.render_kw = {"placeholder": g.tr["placeholder_password"]}
    form.confirm_password.render_kw = {"placeholder": g.tr["placeholder_confirm_password"]}

    if form.validate_on_submit():
        name = form.name.data
        surname = form.surname.data
        phone = form.phone_number.data
        email = form.email.data
        password = form.password.data
        confirm_password = form.confirm_password.data

        user = User.query.filter_by(email=email).first()

        if user:
            log_user_action(
                user.name,
                "Register",
                "User exist",
                level="warning"
            )
            flash(g.tr['flash_email_exists'], 'error')
            return render_template('authorization/register.html', form=form)

        if password != confirm_password:
            log_user_action(
                name,
                "Register",
                "Password does not match",
                level="warning"
            )
            flash(g.tr['flash_password_not_match'], 'error')
            return render_template('authorization/register.html', form=form)

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(
            name=name,
            surname=surname,
            phone_number=phone,
            email=email,
            password=hashed_password
        )
        db.session.add(new_user)
        link.used = True
        db.session.commit()

        log_user_action(name,"Register",f"Email: {email}")

        flash(g.tr['flash_registration_successful'], 'success')
        return redirect(lang_url_for('login', form=form))

    return render_template('authorization/register.html', form=form)

@app.route('/')
def redirect_to_default_lang():
    return redirect(lang_url_for('login', lang='en'))

@app.route('/<lang>/login', methods=['GET', 'POST'])
@localization
def login(lang):
    form = LoginForm()
    form.email.render_kw = {"placeholder": g.tr["placeholder_email"]}
    form.password.render_kw = {"placeholder": g.tr["placeholder_password"]}

    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password, password):

            if not user.is_active:
                log_user_action(
                    user.name,
                    "Login",
                    "User Not Active",
                    level="warning"
                )
                flash(g.tr['flash_user_not_active'], 'error')
                return redirect(lang_url_for('index'))

            if not user.is_verified:
                log_user_action(
                    user.name,
                    "Login",
                    "User Not Verified",
                    level="warning"
                )
                flash(g.tr['flash_user_not_verified'], 'error')
                return redirect(lang_url_for('index'))

            login_user(user)
            log_user_action(current_user.name, "Login")

            next_page = session.pop('next', None)
            return redirect(next_page or lang_url_for('index'))

        log_user_action(
            user.name if user else email,
            "Login",
            "Incorrect Username or Password",
            level="warning"
        )

        flash(g.tr['flash_login_failed'], 'error')
        return render_template('authorization/login.html', form=form)

    return render_template('authorization/login.html', form=form)

@app.route("/<lang>/forgot_password", methods=["GET", "POST"])
@localization
def forgot_password(lang):
    form = TokenSendForm()
    form.email.render_kw = {"placeholder": g.tr["placeholder_email"]}

    if form.validate_on_submit():
        email = form.email.data
        user = User.query.filter_by(email=email).first()

        if user:
            token = generate_link("reset_password", user_id=user.id)
            reset_url = lang_url_for("reset_password", token=token, _external=True)

            send_email(
                subject=g.tr['email_reset_password_subject'],
                html=render_template("emails/reset_password.html", url=reset_url),
                recipients=form.email.data
            )

            log_user_action(user.name,"Forgot_Password")

            flash(g.tr['flash_reset_link'], 'success')
            return redirect(lang_url_for("forgot_password"))

    return render_template("authorization/forgot_password.html", form=form)

@app.route("/<lang>/reset_password", methods=["GET", "POST"])
@localization
def reset_password(lang):
    token = request.form.get("token") or request.args.get("token")

    if not token:
        flash(g.tr['flash_missing_token'], 'error')
        return redirect(lang_url_for('login'))

    link = OneTimeLink.query.filter_by(token=token, used=False).first()

    if not link:
        flash(g.tr['flash_invalid_link'], 'error')
        return redirect(lang_url_for('login'))

    if link.expires_at and link.expires_at < datetime.utcnow():
        db.session.commit()
        flash(g.tr['flash_link_expired'], 'error')
        return redirect(lang_url_for('login'))

    user = User.query.get(link.user_id)

    if not user:
        flash(g.tr['flash_user_not_found'], 'error')
        return redirect(lang_url_for('login'))

    form = ResetPasswordForm()
    form.password.render_kw = {"placeholder": g.tr["placeholder_password"]}
    form.confirm_password.render_kw = {"placeholder": g.tr["placeholder_confirm_password"]}

    if form.validate_on_submit():
        new_password = form.password.data
        confirm_password = form.confirm_password.data

        if new_password != confirm_password:
            log_user_action(
                user.name,
                "Reset_Password",
                "Password does not match",
                level="warning"
            )
            flash(g.tr['flash_password_not_match'], 'error')
            return render_template('authorization/reset_password.html', form=form)

        hashed = bcrypt.generate_password_hash(new_password).decode("utf-8")
        user.password = hashed
        link.used = True
        db.session.commit()

        log_user_action(user.name,"Reset_Password")

        flash(g.tr['flash_password_updated'], 'success')
        return redirect(lang_url_for('login'))

    return render_template("authorization/reset_password.html", form=form, token=token)

@app.route('/<lang>/verify_email/<token>')
@localization
def verification(lang, token):
    link = OneTimeLink.query.filter_by(token=token, purpose="email_verification", used=False).first()
    if not link:
        flash(g.tr['flash_invalid_link'], 'error')
        return redirect(lang_url_for('login'))

    if link.expires_at and link.expires_at < datetime.utcnow():
        db.session.commit()
        flash(g.tr['flash_link_expired'], 'error')
        return redirect(lang_url_for('login'))

    user = User.query.get(link.user_id)
    if not user:
        flash(g.tr['flash_user_not_found'], 'error')
        return redirect(lang_url_for('login'))

    user.is_verified = True
    link.used = True
    db.session.commit()

    log_user_action(user.name, "Verification")
    flash(g.tr['flash_verification_success'], 'success')
    return redirect(lang_url_for('login'))

@app.route('/<lang>/logout')
@login_required
@localization
def logout(lang):
    log_user_action(current_user.name, "Logout")
    logout_user()
    return redirect(lang_url_for('login'))

@app.route("/<lang>/invite", methods=["GET", "POST"])
@localization
@login_required
def invite(lang):
    if not current_user.is_admin:
        abort(403)

    form = TokenSendForm()
    form.email.render_kw = {"placeholder": g.tr["placeholder_email"]}

    if form.validate_on_submit():
        email = form.email.data

        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            log_user_action(
                current_user.name,
                "Invite",
                "Email exist",
                level="warning"
            )
            flash(g.tr['flash_email_exists'], 'error')
            return redirect(lang_url_for("invite"))

        token = generate_link("registration")
        invite_url = lang_url_for("register", token=token, _external=True)

        send_email(
            subject=g.tr['email_invitation_subject'],
            html=render_template(
                "emails/invitation.html",
                user=current_user,
                url=invite_url
            ),
            recipients=form.email.data
        )

        flash(g.tr["flash_invite_sent"], "success")
        log_user_action(current_user.name,"Invite",f"Email: {email}")
        return redirect(lang_url_for("invite"))

    return render_template("authorization/invite.html", form=form)


@app.route("/<lang>/index")
@login_required
@localization
def index(lang):
    tasks = Task.query.filter_by(is_completed=False).all()
    return render_template("index.html", tasks=tasks)

@app.route('/<lang>/parts')
@login_required
@localization
def parts(lang):
    return render_template('/parts/parts.html')

@app.route('/<lang>/parts/new_part', methods=['GET', 'POST'])
@localization
@login_required
def new_part(lang):
    if not current_user.is_admin:
        abort(403)

    form = PartForm()

    form.part_number.render_kw = {"placeholder": g.tr["placeholder_part_number"]}
    form.name_en.render_kw = {"placeholder": g.tr["placeholder_name_en"]}
    form.name_lt.render_kw = {"placeholder": g.tr["placeholder_name_lt"]}
    form.price.render_kw = {"placeholder": g.tr["placeholder_price"]}

    locations = Location.query.all()

    translated_location_names = [
        location.location_en if g.lang == 'en' else location.location_lt
        for location in locations
    ]

    for subform in form.inventory_entries:
        subform.location_id.choices = [
            (location.id,
             location.location_en if g.lang == 'en' else location.location_lt)
            for location in locations
        ]

    if form.is_submitted():
        selected_ids = form.machine_types.data

        if not selected_ids:
            flash(g.tr['flash_machine_type'], 'error')
            return render_template(
                '/parts/add_new.html',
                form=form,
                locations=translated_location_names
            )

        if form.validate():
            part_number = form.part_number.data
            name_en = form.name_en.data
            name_lt = form.name_lt.data
            price = form.price.data
            selected_ids = form.machine_types.data

            if price < 0:
                flash(g.tr['flash_negative_price'], 'error')
                return render_template(
                    '/parts/add_new.html',
                    form=form,
                    locations=translated_location_names
                )

            part = Part.query.filter_by(part_number=part_number).first()

            if part:
                flash(g.tr['flash_part_number'], 'error')
                return render_template(
                    '/parts/add_new.html',
                    form=form,
                    locations=translated_location_names
                )

            machine_types = MachineType.query.filter(
                MachineType.id.in_(selected_ids)
            ).all()

            new_part = Part(
                part_number=part_number,
                name_en=name_en,
                name_lt=name_lt,
                price=price,
                machine_types=machine_types
            )

            db.session.add(new_part)
            db.session.commit()

            for entry in form.inventory_entries.data:
                location_id = entry['location_id']
                quantity = entry['quantity']

                if quantity and quantity > 0:
                    inventory = Inventory(
                        part_id=new_part.id,
                        location_id=location_id,
                        quantity=quantity
                    )
                    db.session.add(inventory)

            db.session.commit()

            log_user_action(current_user.name,"New_Part",f"Part no: {new_part.part_number}")

            flash(g.tr['flash_part_added'], 'success')
            return redirect(lang_url_for('new_part', form=form))

    return render_template(
        '/parts/add_new.html',
        form=form,
        locations=translated_location_names
    )

@app.route('/<lang>/parts/update_part', methods=["GET", "POST"])
@localization
@login_required
def update_part(lang):
    if not current_user.is_admin:
        abort(403)

    parts = Part.query.order_by(Part.part_number).all()

    if request.method == "POST":
        part_number = request.form.get('part_number')
        return redirect(lang_url_for('update_part_form', part_number=part_number))

    return render_template('/parts/update_part.html', parts=parts)

@app.route('/<lang>/parts/update_part/<string:part_number>', methods=["GET", "POST"])
@localization
@login_required
def update_part_form(part_number, lang):
    parts = Part.query.order_by(Part.part_number).all()
    part = Part.query.filter_by(part_number=part_number).first()
    locations = []
    all_locations = Location.query.all()
    changes = []

    if request.method == "POST":
        for location in all_locations:
            field_name = f"quantity_{location.id}"
            quantity_str = request.form.get(field_name)

            if quantity_str is not None:
                quantity = int(quantity_str)

                inventory = Inventory.query.filter_by(
                    part_id=part.id,
                    location_id=location.id
                ).first()

                if inventory:
                    if inventory.quantity != quantity:
                        changes.append(
                            f"Part no: {part.part_number}; "
                            f"Location: {location.location_en}; "
                            f"Qty: {inventory.quantity} → {quantity}"
                        )
                    inventory.quantity = quantity

                else:
                    if quantity > 0:
                        new_inventory = Inventory(
                            part_id=part.id,
                            location_id=location.id,
                            quantity=quantity
                        )
                        db.session.add(new_inventory)

                        changes.append(
                            f"Part no: {part.part_number}; "
                            f"Location: {location.location_en}; "
                            f"Qty: 0 → {quantity}"
                        )

        db.session.commit()

        for change in changes:
            log_user_action(current_user.name,"Update_Part", change)

        flash(g.tr['flash_updated_quantities'], 'success')
        return redirect(lang_url_for('update_part_form', part_number=part.part_number))

    for location in all_locations:
        inventory = Inventory.query.filter_by(part_id=part.id, location_id=location.id).first()

        quantity = inventory.quantity if inventory else 0

        locations.append({
            'location_id': location.id,
            'location_name': location.location_en if g.lang == 'en' else location.location_lt,
            'quantity': quantity
        })

    return render_template(
        '/parts/update_part.html',
        parts=parts,
        part=part,
        locations=locations
    )

@app.route('/<lang>/parts/add_replaced_part', methods=['GET', 'POST'])
@localization
@login_required
def add_replaced_part(lang):
    form = ReplacedPartForm()

    form.part_number.render_kw = {"placeholder": g.tr["placeholder_part_number"]}
    form.quantity.render_kw = {"placeholder": g.tr["placeholder_quantity"]}
    form.serial_number.render_kw = {"placeholder": g.tr["placeholder_serial_number"]}

    machines = Machine.query.all()
    parts = Part.query.order_by(Part.part_number).all()
    locations = Location.query.all()

    form.location.choices = [
        (str(location.id), location.location_en if g.lang == 'en' else location.location_lt)
        for location in locations
    ]

    if form.validate_on_submit():
        date = form.date.data
        part_number = form.part_number.data

        part = Part.query.filter_by(part_number=part_number).first()
        if not part:
            flash(g.tr['flash_part_not_exist'], 'error')
            return render_template(
                '/parts/add_replaced_part.html',
                form=form,
                parts=parts
            )

        quantity = form.quantity.data
        serial_number = form.serial_number.data

        machine = Machine.query.filter_by(serial_number=serial_number).first()
        if not machine:
            flash(g.tr['flash_machine_not_exist'], 'error')
            return render_template(
                '/parts/add_replaced_part.html',
                form=form,
                parts=parts
            )

        if date < machine.start_of_operation:
            flash(g.tr['flash_invalid_date'], 'error')
            return render_template(
                '/parts/add_replaced_part.html',
                form=form,
                parts=parts
            )

        warranty = True
        if date > machine.end_of_warranty:
            warranty = False

        selected_location_id = int(form.location.data)
        inventory = Inventory.query.filter_by(
            part_id=part.id,
            location_id=selected_location_id
        ).first()

        if not inventory or inventory.quantity < quantity:
            flash(g.tr['flash_invalid_quantity'], 'error')
            return render_template(
                '/parts/add_replaced_part.html',
                form=form,
                parts=parts
            )

        inventory.quantity -= quantity

        replaced_part = PartsReplaced(
            date=date,
            part_id=part.id,
            quantity=quantity,
            machine_id=machine.id,
            warranty=warranty,
            created_at=datetime.now(),
            user_id=current_user.id,
            inventory_id=inventory.id
        )

        db.session.add(replaced_part)
        db.session.commit()

        log_user_action(
            current_user.name,
            "Replaced_Part",
            f"Part: {part_number}; Machine s/n: {serial_number}; Qty: {quantity}"
        )

        flash(g.tr['flash_part_replacement_successful'], 'success')
        return redirect(lang_url_for('add_replaced_part', form=form))

    return render_template(
        '/parts/add_replaced_part.html',
        form=form,
        parts=parts,
        machines=machines
    )

@app.route('/<lang>/parts')
@login_required
@localization
def replaced_part(lang):
    return render_template('/parts/parts.html')

@app.route('/<lang>/machines')
@login_required
@localization
def machines(lang):
    return render_template('/machines/machines.html')

@app.route('/<lang>/machines/edit_machine', methods=['GET', 'POST'])
@login_required
@localization
def edit_machine_select(lang):
    if not current_user.is_admin:
        abort(403)

    machines = Machine.query.order_by(Machine.serial_number).all()
    clients = Client.query.order_by(Client.company).all()
    selected_machine = None

    if request.method == 'POST':
        serial_number = request.form.get('serial_number')
        return redirect(lang_url_for('edit_machine', serial_number=serial_number))

    return render_template(
        'machines/edit_machine.html',
        machines=machines,
        clients=clients,
        selected_machine=selected_machine
    )

@app.route('/<lang>/machines/edit_machine/<string:serial_number>', methods=['GET', 'POST'])
@localization
@login_required
def edit_machine(serial_number, lang):
    if not current_user.is_admin:
        abort(403)

    changes = []
    machines = Machine.query.order_by(Machine.serial_number).all()
    clients = Client.query.order_by(Client.company).all()
    selected_machine = Machine.query.filter_by(serial_number=serial_number).first()

    if not selected_machine:
        flash(g.tr['flash_machine_not_exist'], 'error')
        return render_template(
            'machines/edit_machine.html',
            machines=machines,
            clients=clients,
            selected_machine=selected_machine
        )

    if request.method == 'POST':
        client_id = int(request.form.get('client_id'))
        client = Client.query.filter_by(id=client_id).first()
        is_active = request.form.get('is_active') == 'true'
        machine = Machine.query.filter_by(id=selected_machine.id).first()

        if selected_machine.client_id != client_id:
            changes.append(
                f"Machine s/n: {machine.serial_number}; "
                f"Client: '{selected_machine.client.company} {selected_machine.client.city}' "
                f"→ '{client.company} {client.city}'"
            )
            selected_machine.client_id = client_id

        if selected_machine.is_active != is_active:
            changes.append(
                f"Machine s/n: {machine.serial_number}; "
                f"Is Active: '{selected_machine.is_active}' → '{is_active}'"
            )
            selected_machine.is_active = is_active

        db.session.commit()

        for change in changes:
            log_user_action(current_user.name,"Edit_Machine", change)

        flash(g.tr['flash_machine_update'], 'success')
        return redirect(lang_url_for('edit_machine_select'))

    return render_template(
        'machines/edit_machine.html',
        machines=machines,
        clients=clients,
        selected_machine=selected_machine
    )

@app.route('/<lang>/machines/downloads/', methods=["GET", "POST"])
@login_required
@localization
def downloads(lang):
    download_folder = os.path.join(app.root_path, 'static', 'downloads')
    files = os.listdir(download_folder)
    file_info = []

    for file in files:
        machine_type = file.split(' ')[0] if ' ' in file else "Unknown"
        file_info.append({'machine_type': machine_type, 'filename': file})

    return render_template('/machines/downloads.html', files=file_info)

@app.route('/<lang>/machines/machines_list', methods=['GET'])
@login_required
@localization
def machine_list(lang):
    machines = Machine.query.all()
    return render_template('/machines/machines_list.html', machines=machines)

@app.route('/<lang>/machines/downloads/<path:filename>')
@login_required
@localization
def download_file(filename, lang):
    download_folder = os.path.join(app.root_path, 'static', 'downloads')
    return send_from_directory(download_folder, filename, as_attachment=True)

@app.route('/<lang>/machines/add_new/', methods=["GET", "POST"])
@localization
@login_required
def new_machine(lang):
    if not current_user.is_admin:
        abort(403)

    form = MachineForm()

    form.serial_number.render_kw = {"placeholder": g.tr["placeholder_serial_number"]}
    form.warranty.render_kw = {"placeholder": g.tr["placeholder_warranty"]}

    if form.validate_on_submit():
        serial_number = form.serial_number.data
        type = form.type.data
        start_of_operation = form.start_of_operation.data
        warranty = form.warranty.data
        client_id = form.client.data

        end_of_warranty = start_of_operation + relativedelta(years=warranty)

        machine = Machine.query.filter_by(serial_number=serial_number).first()
        if machine:
            flash(g.tr['flash_machine_exist'], 'error')
            return render_template('/machines/add_new.html', form=form)

        new_machine = Machine(
            serial_number=serial_number,
            machine_type_id=type,
            start_of_operation=start_of_operation,
            end_of_warranty=end_of_warranty,
            client_id=client_id
        )

        db.session.add(new_machine)
        db.session.commit()

        log_user_action(
            current_user.name,
            "New_Machine",
            f"Machine s/n: {new_machine.serial_number}"
        )

        flash(g.tr['flash_machine_added'], 'success')
        return redirect(lang_url_for('new_machine', form=form))

    return render_template('/machines/add_new.html', form=form)

@app.route('/<lang>/prices', methods=['GET', 'POST'])
@login_required
@localization
def prices(lang):
    machine_types = MachineType.query.all()

    if request.method == 'POST':
        machine_type_name = request.form.get('machine_type')
        return redirect(lang_url_for(
            'prices_by_type',
            machine_type_name=machine_type_name
        ))

    return render_template('prices/prices.html', machine_types=machine_types)

@app.route('/<lang>/prices/<string:machine_type_name>', methods=['GET'])
@login_required
@localization
def prices_by_type(machine_type_name, lang):
    machine_type = MachineType.query.filter_by(name=machine_type_name).first()
    parts = sorted(machine_type.parts, key=lambda part: part.part_number)
    machine_types = MachineType.query.all()

    return render_template('prices/prices.html',
                           machine_types=machine_types,
                           selected_type=machine_type,
                           parts=parts)

@app.route('/<lang>/service')
@login_required
@localization
def service(lang):
    return render_template('services/service.html')

@app.route('/<lang>/service/add_new', methods=["GET", "POST"])
@localization
@login_required
def new_service(lang):
    form = ServiceForm()

    form.serial_number.render_kw = {"placeholder": g.tr["placeholder_serial_number"]}
    form.bn_count.render_kw = {"placeholder": g.tr["placeholder_bn_count"]}
    form.note.render_kw = {"placeholder": g.tr["placeholder_note"]}

    machines = Machine.query.all()

    if form.validate_on_submit():
        date = form.date.data
        serial_number = form.serial_number.data
        bn_count = form.bn_count.data
        note = form.note.data

        machine = Machine.query.filter_by(serial_number=serial_number).first()

        if machine:
            new_service = Service(
                date=date,
                machine_id=machine.id,
                bn_count=bn_count,
                user_id=current_user.id,
                note=note,
                created_at=datetime.now()
            )

            last_service = Service.query.filter_by(
                machine_id=machine.id
            ).order_by(Service.date.desc()).first()

            if last_service and date < last_service.date:
                flash(g.tr['flash_service_date'], 'error')
                return render_template('services/add_new.html', form=form)

            if last_service and bn_count < last_service.bn_count:
                flash(g.tr['flash_banknote_count'], 'error')
                return render_template('services/add_new.html', form=form)

            db.session.add(new_service)
            db.session.commit()

            log_user_action(
                current_user.name,
                "New_Service",
                f"Machine s/n: {machine.serial_number}"
            )

            flash(g.tr['flash_service_added'], 'success')
            return redirect(lang_url_for('new_service', form=form))

        else:
            flash(g.tr['flash_machine_not_exist'], 'error')
            return render_template('services/add_new.html', form=form)

    return render_template('services/add_new.html', form=form, machines=machines)

@app.route('/<lang>/reports')
@login_required
@localization
def reports(lang):
    return render_template('reports/reports.html')

@app.route('/<lang>/reports/parts.html', methods=["GET", "POST"])
@localization
@login_required
def parts_report(lang):
    form = PartsReportForm()
    results = []

    if form.validate_on_submit():
        client_id = form.client.data
        date_from = form.date_from.data
        date_to = form.date_to.data

        results = db.session.query(PartsReplaced).join(Machine).filter(
            Machine.client_id == client_id,
            PartsReplaced.date.between(date_from, date_to)
        ).order_by(PartsReplaced.date).all()

        if not results:
            flash(g.tr['flash_no_replaced_parts'], 'warning')
            return render_template(
                'reports/parts.html',
                form=form,
                results=results
            )

    return render_template(
        'reports/parts.html',
        form=form,
        results=results
    )

@app.route('/<lang>/reports/services.html', methods=["GET", "POST"])
@localization
@login_required
def services_report(lang):
    current_quarter = (datetime.now().month - 1) // 3 + 1
    form = ServiceReportForm()
    results = []

    if form.validate_on_submit():
        client_id = form.client.data
        now = datetime.now()
        quarter_now = (now.month - 1) // 3 + 1

        quarter_months = {
            1: (1, 3),
            2: (4, 6),
            3: (7, 9),
            4: (10, 12)
        }

        start_month, end_month = quarter_months[quarter_now]

        results = (
            db.session.query(Machine)
            .outerjoin(Service)
            .join(MachineType, Machine.machine_type_id == MachineType.id)
            .filter(
                Machine.client_id == client_id,
                MachineType.name == 'BPS C1',
                or_(
                    Machine.is_active == True,
                    and_(
                        Machine.is_active == False,
                        extract('year', Service.date) == now.year,
                        extract('month', Service.date).between(start_month, end_month)
                    )
                )
            )
            .order_by(Machine.serial_number)
            .all()
        )

        if not results:
            flash(g.tr['flash_machines_not_found'], 'warning')
            return render_template(
                'reports/services.html',
                form=form,
                current_quarter=current_quarter,
                results=results
            )

    return render_template(
        'reports/services.html',
        form=form,
        current_quarter=current_quarter,
        results=results,
        now=datetime.now()
    )

@app.route('/<lang>/clients')
@login_required
@localization
def clients(lang):
    if not current_user.is_admin:
        abort(403)

    clients = Client.query.all()

    return render_template('/clients/clients.html', clients=clients)

@app.route("/<lang>/clients/add_new", methods=["GET", "POST"])
@localization
@login_required
def new_client(lang):
    if not current_user.is_admin:
        abort(403)

    form = ClientForm()

    form.company.render_kw = {"placeholder": g.tr["placeholder_company"]}
    form.address.render_kw = {"placeholder": g.tr["placeholder_address"]}
    form.city.render_kw = {"placeholder": g.tr["placeholder_city"]}
    form.contact_person.render_kw = {"placeholder": g.tr["placeholder_contact_person"]}
    form.phone_number.render_kw = {"placeholder": g.tr["placeholder_phone_number"]}
    form.email.render_kw = {"placeholder": g.tr["placeholder_email"]}

    if form.validate_on_submit():
        company = form.company.data
        address = form.address.data
        city = form.city.data
        contact_person = form.contact_person.data
        phone_number = form.phone_number.data
        email = form.email.data

        existing_client = Client.query.filter(
            or_(
                Client.phone_number == phone_number,
                func.lower(Client.email) == email.lower()
            )
        ).first()

        if existing_client:
            if existing_client.phone_number == phone_number:
                flash(g.tr['flash_tel_exist'], 'error')
            elif existing_client.email == email:
                flash(g.tr['flash_email_exists'], 'error')

            return render_template("/clients/add_new.html", form=form)

        new_client = Client(
            company=company,
            address=address,
            city=city,
            contact_person=contact_person,
            phone_number=phone_number,
            email=email
        )

        db.session.add(new_client)
        db.session.commit()

        log_user_action(
            current_user.name,
            "New_Client",
            f"Client: {company} {city}"
        )

        flash(g.tr['flash_client_added'], 'success')
        return redirect(lang_url_for('clients', form=form))

    return render_template("/clients/add_new.html", form=form)

@app.route('/<lang>/clients/edit/<int:client_id>', methods=['GET', 'POST'])
@localization
@login_required
def edit_client(client_id, lang):
    if not current_user.is_admin:
        abort(403)

    changes = []

    client = Client.query.get(client_id)
    form = ClientForm(obj=client)

    if form.validate_on_submit():
        if client.address != form.address.data:
            changes.append(
                f"Client: '{client.company} {client.city}'; "
                f"Address: '{client.address}' → '{form.address.data}'"
            )
            client.address = form.address.data

        if client.contact_person != form.contact_person.data:
            changes.append(
                f"Client: '{client.company} {client.city}'; "
                f"Contact Person: '{client.contact_person}' → '{form.contact_person.data}'"
            )
            client.contact_person = form.contact_person.data

        if client.phone_number != form.phone_number.data:
            changes.append(
                f"Client: '{client.company} {client.city}'; "
                f"Phone Number: '{client.phone_number}' → '{form.phone_number.data}'"
            )
            client.phone_number = form.phone_number.data

        if client.email != form.email.data:
            changes.append(
                f"Client: '{client.company} {client.city}'; "
                f"Email: '{client.email}' → '{form.email.data}'"
            )
            client.email = form.email.data

        db.session.commit()

        for change in changes:
            log_user_action(current_user.name,"Edit_Client", change)

        flash(g.tr['flash_client_updated'], 'success')
        return redirect(lang_url_for('clients'))

    return render_template('clients/edit.html', form=form, client=client)


@app.route('/<lang>/machines/select', methods=['GET', 'POST'])
@login_required
@localization
def select_machine(lang):
    if not current_user.is_admin:
        abort(403)

    machines = Machine.query.order_by(Machine.serial_number).all()

    if request.method == 'POST':
        machine_id = request.form.get('machine_id')
        return redirect(lang_url_for('update_machine_client', machine_id=machine_id))

    return render_template('machines/select.html', machines=machines)

@app.route('/<lang>/machines/machine_info', methods=['GET', 'POST'])
@localization
@login_required
def machine_search(lang):
    machines = Machine.query.all()

    if request.method == 'POST':
        serial_number = request.form.get('serial_number')
        machine = Machine.query.filter_by(serial_number=serial_number).first()

        if not machine:
            flash(g.tr['flash_machine_not_exist'], 'error')
            return render_template('machines/machine_info.html', machines=machines)

        return redirect(lang_url_for('machine_info', serial_number=machine.serial_number))

    return render_template('machines/machine_info.html', machines=machines)

@app.route('/<lang>/machines/machine_info/<string:serial_number>', methods=['GET'])
@localization
@login_required
def machine_info(serial_number, lang):
    machine = Machine.query.filter_by(serial_number=serial_number).first()
    services = Service.query.filter_by(machine_id=machine.id).order_by(
        Service.date.desc()
    ).all()
    parts = PartsReplaced.query.filter_by(machine_id=machine.id).order_by(
        PartsReplaced.date.desc()
    ).all()
    machines = Machine.query.all()

    return render_template(
        'machines/machine_info.html',
        machines=machines,
        machine=machine,
        services=services,
        parts=parts
    )


@app.route('/<lang>/tasks')
@login_required
@localization
def tasks(lang):
    tasks = Task.query.order_by(
        case(
            (Task.is_completed == False, 0),
            (Task.is_completed == True, 1)
        ),
        Task.created_at.desc()
    ).all()

    return render_template('tasks/tasks.html', tasks=tasks)

@app.route('/<lang>/tasks/new_task', methods=['GET', 'POST'])
@login_required
@localization
def new_task(lang):
    form = TaskForm()
    form.task.render_kw = {"placeholder": g.tr["placeholder_task"]}

    if form.validate_on_submit():
        task = form.task.data
        created_at = datetime.now()

        new_task = Task(
            task=task,
            created_at=created_at,
            user_id=current_user.id
        )

        db.session.add(new_task)
        db.session.commit()

        users = User.query.filter_by(is_active=True, is_verified=True).all()
        recipients = [user.email for user in users if user.email]

        send_email(
            subject=g.tr['email_task_subject'],
            html=render_template(
                "emails/task.html",
                user=current_user,
                task=task
            ),
            recipients=recipients
        )

        log_user_action(current_user.name,"New_Task",f"Task: {task}")

        flash(g.tr['flash_task_added'], 'success')
        return redirect(lang_url_for('tasks', form=form))

    return render_template('tasks/new_task.html', form=form)

@app.route('/<lang>/tasks/view_tasks/<int:task_id>', methods=['GET'])
@localization
@login_required
def complete_task(task_id, lang):
    task = Task.query.get(task_id)
    task.completed_at = datetime.now()
    task.is_completed = True
    task.completed_by_user_id = current_user.id
    db.session.commit()

    log_user_action(current_user.name, "Complete_Task", f"Task: {task.task}")

    flash(g.tr['flash_task_completed'], 'success')
    return redirect(lang_url_for("tasks"))

@app.route('/<lang>/calendar')
@login_required
@localization
def calendar(lang):
    visits = Visit.query.all()
    return render_template('/calendar/calendar.html', visits=visits)

@app.route('/<lang>/visit/new', methods=['GET', 'POST'])
@localization
@login_required
def new_visit(lang):
    if not current_user.is_admin:
        abort(403)

    form = VisitForm()
    form.purpose.render_kw = {"placeholder": g.tr["placeholder_purpose"]}

    if form.validate_on_submit():
        visit = Visit(
            client_id=form.client.data,
            date=form.date.data,
            purpose=form.purpose.data
        )

        client = Client.query.filter_by(id=form.client.data).first()

        existing_visit = Visit.query.filter_by(
            client_id=form.client.data,
            date=form.date.data
        ).first()

        if existing_visit:
            flash(g.tr['flash_visit_exist'], 'error')
            return redirect(lang_url_for('calendar'))

        db.session.add(visit)
        db.session.commit()

        log_user_action(
            current_user.name,
            "New_Visit",
            f"Date: {form.date.data}; "
            f"Client: {client.company} {client.city}; "
            f"Purpose: {form.purpose.data}"
        )

        users = User.query.filter_by(is_active=True, is_verified=True).all()
        recipients = [user.email for user in users if user.email]

        send_email(
            subject=g.tr['email_visit_subject'],
            html=render_template(
                "emails/visit.html",
                user=current_user,
                form=form,
                client=client
            ),
            recipients=recipients
        )

        flash(g.tr['flash_visit_added'], 'success')
        return redirect(lang_url_for('calendar'))

    return render_template('calendar/visit_form.html', form=form)

@app.route('/<lang>/visit/<int:visit_id>')
@login_required
@localization
def visit_detail(visit_id, lang):
    visit = Visit.query.get(visit_id)

    latest_service = (
        db.session.query(
            Service.machine_id,
            func.max(Service.date).label("last_date")
        )
        .group_by(Service.machine_id)
        .subquery()
    )

    services = (
        db.session.query(Machine, Service)
        .join(Service, Machine.id == Service.machine_id)
        .join(
            latest_service,
            and_(
                Service.machine_id == latest_service.c.machine_id,
                Service.date == latest_service.c.last_date
            )
        )
        .filter(
            Machine.client_id == visit.client_id,
            Machine.is_active == True,
            Service.note != None,
            Service.note != ""
        )
        .order_by(Machine.serial_number)
        .all()
    )

    return render_template(
        'calendar/visit_detail.html',
        visit=visit,
        services=services
    )

@app.route('/<lang>/visit/<int:visit_id>/edit', methods=['GET', 'POST'])
@localization
@login_required
def edit_visit(visit_id, lang):
    if not current_user.is_admin:
        abort(403)

    changes = []

    visit = Visit.query.get(visit_id)
    client = Client.query.get(visit.client_id)
    form = VisitForm(obj=visit)

    db.session.commit()

    if 'client' in form._fields:
        del form.client

    if form.validate_on_submit():
        if visit.date != form.date.data:
            changes.append(
                f"Client: {client.company} {client.city}; "
                f"Date: '{visit.date}' → '{form.date.data}'; "
                f"Purpose: {visit.purpose}"
            )
            visit.date = form.date.data

        if visit.purpose != form.purpose.data:
            changes.append(
                f"Client: {client.company} {client.city}; "
                f"Date: {visit.date}; "
                f"Purpose: '{visit.purpose}' → '{form.purpose.data}'"
            )
            visit.purpose = form.purpose.data

        existing_visit = Visit.query.filter(
            Visit.client_id == visit.client_id,
            Visit.date == form.date.data,
            Visit.id != visit.id
        ).first()

        if existing_visit:
            flash(g.tr['flash_visit_exist'], 'error')
            return redirect(lang_url_for('visit_detail', visit_id=visit.id))

        db.session.commit()

        for change in changes:
            log_user_action(current_user.name,"Edit_Visit", change)

        flash(g.tr['flash_visit_updated'], 'success')
        return redirect(lang_url_for('visit_detail', visit_id=visit.id))

    return render_template(
        'calendar/visit_form.html',
        form=form,
        client=client,
        edit_mode=True
    )

@app.route('/<lang>/visit/<int:visit_id>/delete', methods=['POST'])
@localization
@login_required
def delete_visit(visit_id, lang):
    if not current_user.is_admin:
        abort(403)

    visit = Visit.query.get(visit_id)

    log_user_action(
        current_user.name,
        "Delete_Visit",
        f"Date: {visit.date}; "
        f"Client: {visit.client.company} {visit.client.city}; "
        f"Purpose: {visit.purpose}"
    )

    db.session.delete(visit)
    db.session.commit()

    flash(g.tr['flash_visit_deleted'], 'success')
    return redirect(lang_url_for('calendar'))

@app.errorhandler(404)
@localization
def page_not_found(error):
    return render_template("errors/404.html",tr=g.tr), 404

@app.errorhandler(403)
def forbidden(error):
    return render_template('errors/403.html'), 403