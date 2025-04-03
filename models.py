# iot_lamp_service/models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import click
from flask.cli import with_appcontext
from flask import current_app

db = SQLAlchemy()

class Lamps(UserMixin, db.Model):
    """Database model for IoT Lamps."""
    id = db.Column(db.Integer, primary_key=True) # Internal DB ID
    lamp_id = db.Column(db.String(80), unique=True, nullable=False, index=True) # Physical Lamp ID
    initial_password = db.Column(db.String(120), nullable=False) # Store initial password for first registration validation
    is_registered = db.Column(db.Boolean, default=False, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=True, index=True) # User chosen username
    user_password_hash = db.Column(db.String(256), nullable=True) # Hashed user password
    brightness_setting = db.Column(db.Integer, default=100, nullable=False)
    configured_location = db.Column(db.Text, nullable=True) # User selected location ('Haifa', 'Tel Aviv', etc.)

    # Flask-Login required methods
    def get_id(self):
        """Return the user ID for Flask-Login (using internal db id)."""
        return str(self.id)

    def set_password(self, password):
        """Hashes and sets the user's chosen password."""
        self.user_password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Checks the provided password against the stored hash."""
        if not self.user_password_hash:
            return False
        return check_password_hash(self.user_password_hash, password)

    def check_initial_password(self, password):
        """Checks the provided initial password against the stored one."""
        # Note: Initial password isn't hashed for simplicity, assuming it's temporary.
        # For higher security, hash these too during init-db, but requires more complex validation.
        return self.initial_password == password

    def __repr__(self):
        return f'<Lamp {self.lamp_id}>'


# --- Database Initialization Command ---
@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear existing data and create new tables, then populate initial lamps."""
    db.drop_all()
    db.create_all()

    initial_creds = current_app.config.get('INITIAL_LAMP_CREDS', {})
    if not initial_creds:
        click.echo('No initial lamp credentials found in configuration. Database initialized empty.')
        return

    count = 0
    for lamp_id, initial_pw in initial_creds.items():
        # Check if lamp already exists (shouldn't happen with drop_all, but good practice)
        existing_lamp = Lamps.query.filter_by(lamp_id=lamp_id).first()
        if not existing_lamp:
            new_lamp = Lamps(lamp_id=lamp_id, initial_password=initial_pw)
            db.session.add(new_lamp)
            count += 1
        else:
             click.echo(f'Warning: Lamp ID {lamp_id} already exists, skipping.')

    try:
        db.session.commit()
        click.echo(f'Initialized the database and added {count} initial lamp entries.')
        click.echo('IMPORTANT SECURITY NOTE: The initial passwords stored in the database are temporary.')
        click.echo('Users should register promptly to set their own secure, hashed passwords.')
    except Exception as e:
        db.session.rollback()
        click.echo(f'Error initializing database: {e}')

def init_app(app):
    """Register database functions with the Flask app."""
    db.init_app(app)
    app.cli.add_command(init_db_command)
