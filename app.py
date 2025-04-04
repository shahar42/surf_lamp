# iot_lamp_service/app.py
import os
from flask import (
    Flask, request, jsonify, render_template, redirect, url_for, flash, session, abort,
    send_from_directory # <<< Added send_from_directory
)
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)
from config import Config
from models import db, Lamps, init_app as init_db_app
from helpers import Workspace_isramar_data, Workspace_owm_data

# --- Application Setup ---
app = Flask(__name__, instance_relative_config=True, static_folder='static') # Specify static folder
app.config.from_object(Config)

# Ensure the instance folder exists
try:
    os.makedirs(app.instance_path)
except OSError:
    pass

# Initialize Database & CLI command
init_db_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Redirect to /login if @login_required fails

@login_manager.user_loader
def load_user(user_id):
    """Flask-Login user loader callback."""
    return Lamps.query.get(int(user_id))

# --- Favicon Route ---
# Serves the favicon.ico file from the static folder.
# Ensure you have a 'static' folder in your project root (same level as app.py)
# and place your 'favicon.ico' file inside it.
@app.route('/favicon.ico')
def favicon():
    """Serves the favicon image."""
    return send_from_directory(os.path.join(app.root_path, 'static'),
                           'favicon.ico', mimetype='image/vnd.microsoft.icon')

# --- Web Routes (HTML Frontend) ---

@app.route('/')
def index():
    """Homepage - Redirects to settings if logged in, else to login."""
    if current_user.is_authenticated:
        return redirect(url_for('settings'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handles new user registration for a lamp."""
    if current_user.is_authenticated:
        return redirect(url_for('settings')) # Already logged in

    if request.method == 'POST':
        lamp_id = request.form.get('lamp_id')
        initial_password = request.form.get('initial_password')
        username = request.form.get('username')
        password = request.form.get('password')
        password2 = request.form.get('password2')

        # --- Validation ---
        lamp = Lamps.query.filter_by(lamp_id=lamp_id).first()

        if not lamp:
            flash('Invalid Lamp ID.', 'danger')
        elif lamp.is_registered:
            flash('This Lamp ID is already registered.', 'warning')
        elif not lamp.check_initial_password(initial_password):
            flash('Incorrect Initial Password for this Lamp ID.', 'danger')
        elif not username:
            flash('Username cannot be empty.', 'danger')
        elif Lamps.query.filter_by(username=username).first():
            flash('Username already taken. Please choose another.', 'danger')
        elif not password or password != password2:
            flash('Passwords do not match or are empty.', 'danger')
        else:
            # --- Registration Success ---
            try:
                lamp.username = username
                lamp.set_password(password) # Hash and store the new password
                lamp.is_registered = True
                # Optionally clear initial_password after registration for security
                # lamp.initial_password = "" # Consider implications if re-registration is needed
                db.session.commit()
                flash(f'Registration successful for Lamp {lamp_id}! You can now log in.', 'success')
                return redirect(url_for('login'))
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Database error during registration for {lamp_id}: {e}")
                flash('Registration failed due to a server error. Please try again later.', 'danger')

    return render_template('register.html', title='Register Lamp')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
    if current_user.is_authenticated:
        return redirect(url_for('settings')) # Already logged in

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = Lamps.query.filter_by(username=username).first()

        if user and user.check_password(password):
            # Check if the user record actually corresponds to a registered lamp
            if not user.is_registered:
                # This case should ideally not happen if registration sets the flag correctly
                flash('Login failed: Lamp associated with this user is not fully registered.', 'danger')
            else:
                login_user(user, remember=remember)
                flash(f'Welcome back, {user.username}!', 'success')
                # Redirect to the page the user was trying to access, or settings
                next_page = request.args.get('next')
                return redirect(next_page or url_for('settings'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html', title='Login')


@app.route('/logout')
@login_required
def logout():
    """Logs the user out."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """Allows logged-in users to configure their lamp settings (location, brightness)."""
    if request.method == 'POST':
        location = request.form.get('location')
        brightness_str = request.form.get('brightness')

        # Validate brightness
        try:
            brightness = int(brightness_str)
            if not (0 <= brightness <= 100):
                raise ValueError("Brightness out of range")
        except (ValueError, TypeError):
            flash('Invalid brightness value. Please enter a number between 0 and 100.', 'danger')
            # Re-render form with current values to avoid losing valid location selection
            return render_template('settings.html', title='Settings',
                                   available_locations=app.config['AVAILABLE_LOCATIONS'],
                                   current_location=current_user.configured_location,
                                   current_brightness=current_user.brightness_setting)

        # Validate location
        if location not in app.config['AVAILABLE_LOCATIONS']:
            flash('Invalid location selected.', 'danger')
            # Re-render form
            return render_template('settings.html', title='Settings',
                                   available_locations=app.config['AVAILABLE_LOCATIONS'],
                                   current_location=current_user.configured_location,
                                   current_brightness=brightness) # Use validated brightness


        # --- Save Settings ---
        try:
            current_user.configured_location = location
            current_user.brightness_setting = brightness
            db.session.commit()
            flash('Settings updated successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Database error saving settings for user {current_user.username}: {e}")
            flash('Failed to save settings due to a server error.', 'danger')

        # Redirect back to GET settings page after POST to prevent form resubmission
        return redirect(url_for('settings'))

    # --- GET Request ---
    return render_template('settings.html', title='Settings',
                           available_locations=app.config['AVAILABLE_LOCATIONS'],
                           current_location=current_user.configured_location,
                           current_brightness=current_user.brightness_setting)


# --- API Endpoint for Arduino Lamp ---

@app.route('/api/lamp/config', methods=['GET'])
def get_lamp_config():
    """
    API endpoint for the Arduino lamp to fetch its configuration and weather data.
    Requires 'id' query parameter matching the lamp_id.
    """
    lamp_id = request.args.get('id')
    if not lamp_id:
        return jsonify({"error": "Missing 'id' query parameter"}), 400

    lamp = Lamps.query.filter_by(lamp_id=lamp_id).first()

    if not lamp:
        app.logger.warning(f"API request for non-existent lamp ID: {lamp_id}")
        # Use abort(404) to let Flask handle the standard 404 response
        abort(404, description=f"Lamp with ID '{lamp_id}' not found.")
        # Alternatively, return custom JSON:
        # return jsonify({"error": f"Lamp with ID '{lamp_id}' not found"}), 404

    # --- Initialize Response ---
    response_data = {
        "api_version": "1.0",  # Include API version
        "registered": lamp.is_registered,
        "brightness": lamp.brightness_setting,
        "location_used": None, # Will be updated if weather is fetched
        "wave_height_m": None,
        "wave_period_s": None,
        "wind_speed_mps": None,
        "wind_deg": None,
        "error": None # General error field for the Arduino
    }

    # --- Fetch Weather Data (Only if Registered and Location is Set) ---
    if lamp.is_registered and lamp.configured_location:
        location = lamp.configured_location
        response_data["location_used"] = location # Record which location was used

        # Fetch ISRAMAR Data
        isramar_data = Workspace_isramar_data(location)
        if isramar_data:
            response_data["wave_height_m"] = isramar_data.get("wave_height_m")
            response_data["wave_period_s"] = isramar_data.get("wave_period_s")
        else:
            app.logger.warning(f"Failed to get ISRAMAR data for {location} (Lamp: {lamp_id})")
            # Keep weather fields as None, potentially set error later if both fail

        # Fetch OpenWeatherMap Data
        owm_data = Workspace_owm_data(location)
        if owm_data:
            response_data["wind_speed_mps"] = owm_data.get("wind_speed_mps")
            response_data["wind_deg"] = owm_data.get("wind_deg")
        else:
            app.logger.warning(f"Failed to get OWM data for {location} (Lamp: {lamp_id})")
            # Keep weather fields as None

        # Set generic error if *both* fetches failed, but lamp should be getting data
        if isramar_data is None and owm_data is None:
             response_data["error"] = "Could not fetch weather data"

    elif lamp.is_registered and not lamp.configured_location:
        response_data["error"] = "Location not configured"
        app.logger.info(f"Lamp {lamp_id} is registered but has no location set.")

    elif not lamp.is_registered:
        response_data["error"] = "Lamp not registered"
        # No need to fetch weather for an unregistered lamp
        pass # Defaults are already None/False

    return jsonify(response_data), 200
# --- Error Handlers ---
@app.errorhandler(404)
def not_found_error(error):
    # Distinguish between API 404s and Web 404s
    if request.path.startswith('/api/'):
         # Get description from abort() or provide a default
         description = getattr(error, 'description', 'Resource not found')
         return jsonify(error=description), 404
    # Check specifically for favicon 404 AFTER checking API paths
    # If the favicon route exists, this shouldn't be hit for favicon.ico,
    # but good practice if other static files might 404.
    elif request.path.endswith('favicon.ico'):
         # Could return a specific message or just the standard 404 page
         app.logger.warning(f"404 Error specifically for path: {request.path}")
         return render_template('404.html'), 404 # Or return '', 404 if preferred
    else:
         return render_template('404.html'), 404 # Assumes you create a 404.html

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback() # Rollback potentially failed DB transactions
     # Log the error properly here
    app.logger.error(f"Server Error: {error}", exc_info=True)
    if request.path.startswith('/api/'):
         return jsonify(error="Internal server error"), 500
    else:
         flash("An unexpected error occurred. Please try again later.", "danger")
         return render_template('500.html'), 500 # Assumes you create a 500.html

# --- Main Execution ---
if __name__ == '__main__':
    # Use development server. For production, use a proper WSGI server like Gunicorn or uWSGI.
    # Ensure debug=False for production deployments
    app.run(debug=True, host='0.0.0.0', port=5000) # Listen on all interfaces
