# iot_lamp_service/config.py
import os
from dotenv import load_dotenv

# --- Load .env file ---
# This loads variables from a .env file into the environment.
# Crucial for LOCAL DEVELOPMENT.
# IMPORTANT: Ensure '.env' is listed in your .gitignore file to avoid committing secrets!
basedir = os.path.abspath(os.path.dirname(__file__))
dotenv_path = os.path.join(basedir, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    print("INFO: Loaded environment variables from local .env file.") # Informative message
else:
    print("INFO: Local .env file not found. Relying on system environment variables (expected in production).")

class Config:
    """Base configuration settings."""

    # --- Critical Secrets ---
    # SECRET_KEY: Essential for session security etc.
    # Reads from 'SECRET_KEY' environment variable.
    # The fallback 'you-will-never-guess' is INSECURE and only a placeholder.
    # MUST be set securely in Render's environment variables for production.
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'

    # OpenWeatherMap API Key: Required for weather data.
    # Reads from 'OPENWEATHERMAP_API_KEY' environment variable.
    # MUST be set in Render's environment variables for production.
    OPENWEATHERMAP_API_KEY = os.environ.get('OPENWEATHERMAP_API_KEY')

    # --- Database Configuration ---
    # SQLALCHEMY_DATABASE_URI: Specifies the database connection string.
    # Priority Order:
    # 1. DATABASE_URL (Standard for Render linked databases)
    # 2. SQLALCHEMY_DATABASE_URI (Alternative env var, or from .env)
    # 3. Fallback to local SQLite database (for development convenience)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        os.environ.get('SQLALCHEMY_DATABASE_URI') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'app.db') # Using your specified DB name 'app.db'

    # Disable modification tracking overhead, recommended setting
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Application Specific Configuration ---

    # OpenWeatherMap API endpoint URL
    OPENWEATHERMAP_API_URL = "https://api.openweathermap.org/data/2.5/weather"

    # ISRAMAR URL Mapping (Fixed for now, could be moved to env vars if needed)
    ISRAMAR_URL_MAP = {
        'Haifa': 'https://isramar.ocean.org.il/isramar2009/json/Haifa_Hs_Per.json',
        'Tel Aviv': 'https://isramar.ocean.org.il/isramar2009/json/Tel_Aviv_Hs_Per.json',
        'Ashdod': 'https://isramar.ocean.org.il/isramar2009/json/Ashdod_Hs_Per.json',
    }
    AVAILABLE_LOCATIONS = list(ISRAMAR_URL_MAP.keys())

    # --- Initial Lamp Credentials ---
    # This section loads initial Lamp IDs and Passwords from the .env file.
    # NOTE 1: This is primarily useful for the 'flask init-db' command to populate
    #         the database with the initial set of lamps and their temporary passwords.
    # NOTE 2: The running application (register/login routes) should rely on the
    #         data already present IN THE DATABASE, not these config values directly.
    # NOTE 3: Since the .env file won't exist in the production environment on Render,
    #         this dictionary will likely be empty when running deployed. This is okay
    #         if the database is correctly initialized during/after deployment.
    INITIAL_LAMP_CREDS = {}
    for i in range(1, 11): # Check for up to 10 initial lamps
        lamp_id_key = f'INITIAL_LAMP_{i}_ID'
        lamp_pw_key = f'INITIAL_LAMP_{i}_PW'
        lamp_id = os.environ.get(lamp_id_key)
        lamp_pw = os.environ.get(lamp_pw_key)
        if lamp_id and lamp_pw:
            INITIAL_LAMP_CREDS[lamp_id] = lamp_pw
        else:
            break # Stop looking if a sequential entry is missing

    # --- Startup Checks / Warnings (Optional but helpful) ---
    # These checks run when the Config class is defined (i.e., on app startup)

    # Check if critical secrets are missing (useful during local dev)
    if not SECRET_KEY or SECRET_KEY == 'you-will-never-guess':
         print("WARNING: SECRET_KEY is missing or using the insecure default. Set it in your .env file or environment variables.")

    if not OPENWEATHERMAP_API_KEY:
        print("WARNING: OPENWEATHERMAP_API_KEY not found. Weather fetching will fail. Set it in your .env file or environment variables.")

    if not INITIAL_LAMP_CREDS and not os.environ.get('DATABASE_URL'): # Only warn if likely running locally without .env creds
         print("WARNING: No INITIAL_LAMP credentials found in environment/config. 'flask init-db' might not populate lamps correctly.")

    # Check database URI type in production
    if os.environ.get('FLASK_ENV') == 'production':
        if not SQLALCHEMY_DATABASE_URI or 'sqlite' in SQLALCHEMY_DATABASE_URI:
             # Use print for warnings, raise Exception for critical failures preventing startup
             print("CRITICAL WARNING: Production environment (FLASK_ENV=production) is configured to use SQLite or has no database URI. Ensure DATABASE_URL is set correctly in the Render environment variables.")
             # Consider uncommenting the line below to prevent starting in a misconfigured state:
             # raise ValueError("Production environment must use DATABASE_URL, not SQLite.")
        if not SECRET_KEY or SECRET_KEY == 'you-will-never-guess':
             print("CRITICAL WARNING: SECRET_KEY is missing or insecure in production!")
             # raise ValueError("SECRET_KEY not set or is insecure in production environment.")
