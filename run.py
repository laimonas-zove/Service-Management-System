from Management_system import app, db
from Management_system.utils import create_default_admin

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        create_default_admin()
    app.run(debug=True)