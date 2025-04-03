# iot_lamp_service/helpers.py
import requests
from flask import current_app, json # Use Flask's json for consistency if needed

def Workspace_isramar_data(location_name: str) -> dict | None:
    """
    Fetches wave data from the ISRAMAR JSON endpoint for a given location name.

    Args:
        location_name: The key corresponding to the location in ISRAMAR_URL_MAP (e.g., 'Haifa').

    Returns:
        A dictionary {'wave_height_m': float, 'wave_period_s': float} on success,
        None on failure (network error, invalid JSON, missing data).
    """
    url_map = current_app.config.get('ISRAMAR_URL_MAP', {})
    url = url_map.get(location_name)

    if not url:
        current_app.logger.error(f"ISRAMAR URL not found for location: {location_name}")
        return None

    try:
        response = requests.get(url, timeout=10) # Added timeout
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        data = response.json()

        # Navigate the nested structure based on observed ISRAMAR JSON format
        # Example: {"Data":[{"date_time":"...", "Hs": "1.23", "Tp": "5.67", ...}, ...]}
        # We typically want the latest entry if it's a list
        if isinstance(data, dict) and 'Data' in data and isinstance(data['Data'], list) and data['Data']:
            latest_data = data['Data'][0] # Assume first entry is latest, adjust if needed
            height_str = latest_data.get('Hs') # Wave Height (m)
            period_str = latest_data.get('Tp') # Wave Period (s)

            if height_str is not None and period_str is not None:
                try:
                    # Convert to float, handle potential conversion errors
                    height_m = float(height_str)
                    period_s = float(period_str)
                    return {'wave_height_m': height_m, 'wave_period_s': period_s}
                except (ValueError, TypeError):
                     current_app.logger.error(f"ISRAMAR data conversion error for {location_name}. Height: '{height_str}', Period: '{period_str}'")
                     return None
            else:
                current_app.logger.warning(f"ISRAMAR data missing 'Hs' or 'Tp' key for {location_name}. Data: {latest_data}")
                return None
        else:
            current_app.logger.error(f"Unexpected ISRAMAR JSON structure or empty data for {location_name}. URL: {url}")
            return None

    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error fetching ISRAMAR data for {location_name}: {e}")
        return None
    except json.JSONDecodeError as e:
        current_app.logger.error(f"Error decoding ISRAMAR JSON for {location_name}: {e}")
        return None
    except Exception as e: # Catch any other unexpected errors
        current_app.logger.error(f"Unexpected error processing ISRAMAR data for {location_name}: {e}")
        return None


def Workspace_owm_data(location_name: str) -> dict | None:
    """
    Fetches wind data from the OpenWeatherMap API for a given location name.

    Args:
        location_name: The city name to query (e.g., 'Haifa').

    Returns:
        A dictionary {'wind_speed_mps': float, 'wind_deg': int} on success,
        None on failure (network error, invalid JSON, missing data, API key issue).
    """
    api_key = current_app.config.get('OPENWEATHERMAP_API_KEY')
    base_url = current_app.config.get('OPENWEATHERMAP_API_URL')

    if not api_key or not base_url:
        current_app.logger.error("OpenWeatherMap API Key or URL is not configured.")
        return None

    # Add country code for better accuracy, assuming Israel for now
    query_param = f"{location_name},IL"
    params = {
        'q': query_param,
        'appid': api_key,
        'units': 'metric' # Get speed in m/s
    }

    try:
        response = requests.get(base_url, params=params, timeout=10) # Added timeout
        response.raise_for_status() # Raise HTTPError for bad responses (like 401 Unauthorized)

        data = response.json()

        # Navigate the OWM current weather JSON structure
        # Example: {"wind": {"speed": 3.13, "deg": 210}, "cod": 200, ...}
        if data.get('cod') == 200 and 'wind' in data:
            wind_data = data['wind']
            speed = wind_data.get('speed') # Wind speed (m/s)
            deg = wind_data.get('deg')     # Wind direction (degrees)

            # OWM might omit 'deg' if wind is variable or speed is very low
            if speed is not None:
                try:
                    # Ensure speed is float, deg is int (or default if missing)
                    speed_mps = float(speed)
                    # Use get(key, default) for degree, providing 0 if missing
                    wind_deg = int(deg) if deg is not None else 0
                    return {'wind_speed_mps': speed_mps, 'wind_deg': wind_deg}
                except (ValueError, TypeError):
                    current_app.logger.error(f"OWM data conversion error for {location_name}. Speed: '{speed}', Deg: '{deg}'")
                    return None
            else:
                 current_app.logger.warning(f"OWM data missing 'wind.speed' for {location_name}. Data: {data}")
                 return None
        elif data.get('cod') != 200:
             current_app.logger.error(f"OpenWeatherMap API error for {location_name}. Code: {data.get('cod')}, Message: {data.get('message')}")
             return None
        else:
            current_app.logger.error(f"Unexpected OWM JSON structure for {location_name}. Data: {data}")
            return None

    except requests.exceptions.HTTPError as e:
         # Specifically log 401 Unauthorized errors which usually mean API key issues
        if e.response.status_code == 401:
             current_app.logger.error(f"OpenWeatherMap API Key Error (401 Unauthorized). Check your key.")
        else:
            current_app.logger.error(f"HTTP error fetching OWM data for {location_name}: {e}")
        return None
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Network error fetching OWM data for {location_name}: {e}")
        return None
    except json.JSONDecodeError as e:
        current_app.logger.error(f"Error decoding OWM JSON for {location_name}: {e}")
        return None
    except Exception as e: # Catch any other unexpected errors
        current_app.logger.error(f"Unexpected error processing OWM data for {location_name}: {e}")
        return None
