# helpers.py

# --- Imports ---
# Make sure you have these imports at the top of your helpers.py
import requests
import json
from flask import current_app # Needed for accessing config and logger

# --- Hardcoded URLs/Parameters for Hadera ---
# URLs known to work from the original Arduino code
HADERA_ISRAMAR_URL = "https://isramar.ocean.org.il/isramar2009/station/data/Hadera_Hs_Per.json"
OWM_CITY = "Hadera" # City name for OpenWeatherMap

# --- Helper Functions ---

def Workspace_isramar_data(location):
    """
    Fetches and parses wave data from ISRAMAR.
    MODIFIED: Ignores 'location' argument and ALWAYS fetches Hadera data.
    Returns dict with 'wave_height_m' and 'wave_period_s' or None on error.
    """
    # Ignore the 'location' argument passed from app.py, always use Hadera URL
    url = HADERA_ISRAMAR_URL
    current_app.logger.info(f"Fetching ISRAMAR data for HARDCODED location 'Hadera' from: {url}")

    try:
        response = requests.get(url, timeout=10) # 10 second timeout
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        data = response.json()
        wave_height = None
        wave_period = None

        # Parse based on original Arduino logic structure (parameters array)
        if "parameters" in data and isinstance(data["parameters"], list):
            for param in data["parameters"]:
                # Check if param is a dictionary and has the expected keys/types
                if isinstance(param, dict) and \
                   "name" in param and \
                   "values" in param and \
                   isinstance(param["values"], list) and \
                   len(param["values"]) > 0:
                    try:
                        # Attempt to convert value to float, handle potential errors
                        value = float(param["values"][0])
                        if param["name"] == "Significant wave height":
                            wave_height = value
                        elif param["name"] == "Peak wave period":
                            wave_period = value
                    except (ValueError, TypeError):
                        current_app.logger.warning(f"Could not convert ISRAMAR value {param['values'][0]} to float for parameter '{param['name']}'.")


        # Return data only if both values were found and are valid numbers
        if wave_height is not None and wave_period is not None:
             current_app.logger.info(f"ISRAMAR Hadera data parsed: H={wave_height}, P={wave_period}")
             return {"wave_height_m": wave_height, "wave_period_s": wave_period}
        else:
             current_app.logger.warning(f"Could not find valid wave height/period in ISRAMAR Hadera JSON structure.")
             return None # Return None if data wasn't found/parsed correctly

    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error fetching ISRAMAR Hadera data: {e}")
        return None
    except json.JSONDecodeError as e:
         current_app.logger.error(f"Error decoding ISRAMAR Hadera JSON: {e}")
         return None
    except Exception as e:
         # Catch any other unexpected errors during processing
         current_app.logger.error(f"Unexpected error processing ISRAMAR Hadera data: {e}", exc_info=True)
         return None


def Workspace_owm_data(location):
    """
    Fetches and parses wind data from OpenWeatherMap.
    MODIFIED: Ignores 'location' argument and ALWAYS fetches Hadera data.
    Returns dict with 'wind_speed_mps' and 'wind_deg' or None on error.
    """
    # Ignore the 'location' argument passed from app.py, always use Hadera
    city = OWM_CITY
    api_key = current_app.config.get('OPENWEATHERMAP_API_KEY')
    # Get base URL from config, default if not set
    base_url = current_app.config.get('OPENWEATHERMAP_API_URL', "https://api.openweathermap.org/data/2.5/weather")

    if not api_key:
        current_app.logger.error("OpenWeatherMap API Key not configured.")
        return None

    params = {
        'q': city,
        'appid': api_key,
        'units': 'metric' # Request units in meters/sec
    }
    current_app.logger.info(f"Fetching OWM data for HARDCODED location '{city}' with params: {params}")

    try:
        response = requests.get(base_url, params=params, timeout=10) # 10 second timeout
        response.raise_for_status() # Raise HTTPError for bad responses

        data = response.json()
        wind_speed = None
        wind_deg = None

        # Safely extract wind data
        if isinstance(data.get('wind'), dict):
            wind_data = data['wind']
            # Check types before assigning
            if isinstance(wind_data.get('speed'), (int, float)):
                wind_speed = float(wind_data['speed'])
            if isinstance(wind_data.get('deg'), (int, float)):
                wind_deg = int(wind_data['deg'])

        # Return data only if both values were found and are valid
        if wind_speed is not None and wind_deg is not None:
            current_app.logger.info(f"OWM Hadera data parsed: Speed={wind_speed}, Deg={wind_deg}")
            return {"wind_speed_mps": wind_speed, "wind_deg": wind_deg}
        else:
            current_app.logger.warning(f"Could not find valid wind speed/deg in OWM Hadera JSON structure.")
            return None # Return None if data wasn't found/parsed correctly

    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error fetching OWM Hadera data: {e}")
        return None
    except json.JSONDecodeError as e:
         current_app.logger.error(f"Error decoding OWM Hadera JSON: {e}")
         return None
    except Exception as e:
         # Catch any other unexpected errors
         current_app.logger.error(f"Unexpected error processing OWM Hadera data: {e}", exc_info=True)
         return None

# --- You might have other helper functions below ---
