from flask import Flask, jsonify, request
import requests
import xmltodict
import math
import logging
import redis
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from geopy.geocoders import Nominatim


app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Redis Configuration
REDIS_HOST = "redis"
REDIS_PORT = 6379
REDIS_KEY = "iss_data"

# Connect to Redis

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# ISS Data Sources
ISS_TRAJECTORY_URL = "https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml"
ISS_NOW_URL = "http://api.open-notify.org/iss-now.json"

def fetch_iss_data() -> List[Dict[str, Any]]:
    """
    Fetch ISS data from the NASA API and store it in Redis

    There is no input arguments

    Returns:
        iss_data (List[Dict[str, Any]]): List of dictionaries, each containing
        time and state vectors (this is a global variable so it can be used throughout)
    """
    try:
        logger.info("Fetching ISS data from NASA API...")
        response = requests.get(ISS_TRAJECTORY_URL, timeout=10)
        logger.info(f"Response status code: {response.status_code}")

        response.raise_for_status()
        logger.info("Successfully fetched ISS data.")

        data = xmltodict.parse(response.text)
        state_vectors = data.get('ndm', {}).get('oem', {}).get('body', {}).get('segment', {}).get('data', {}).get('stateVector', [])
        #state_vectors = data['ndm']['oem']['body']['segment']['data']['stateVector']
        #if not isinstance(state_vectors, list):
        #    state_vectors = [state_vectors]

        if not state_vectors:
            logger.error("NASA API returned no state vectors!")
            return []

        iss_data = [
            {
                'epoch': state['EPOCH'],
                'x': float(state['X']['#text']),
                'y': float(state['Y']['#text']),
                'z': float(state['Z']['#text']),
                'x_dot': float(state['X_DOT']['#text']),
                'y_dot': float(state['Y_DOT']['#text']),
                'z_dot': float(state['Z_DOT']['#text']),
            }
            for state in state_vectors
        ]

        # Store data in Redis
        r.set(REDIS_KEY, json.dumps(iss_data, indent=4))
        logger.info(f"Loaded {len(iss_data)} state vectors into Redis.")
        return iss_data
    except Exception as e:
        logger.error(f"Error fetching ISS data: {e}")
        return []


def get_iss_data() -> List[Dict[str, Any]]:
    """
    Retrieves ISS data from Redis, or fetch from NASA if missing

    There is no input arguments

    Returns:
        iss_data (List[Dict[str, Any]]): List of dictionaries, each containing
        time and state vectors (this is a global variable so it can be used throughout)
    """
    data = r.get(REDIS_KEY)
    if data:
        logger.info("ISS data loaded from Redis.")
        return json.loads(data)
    logger.info("No ISS data found in Redis, fetching from NASA")
    return fetch_iss_data()

def calculate_speed(x_dot: float, y_dot: float, z_dot: float) -> float:
    """
    Calculates speed from Cartesian Velocity Vectors

    Args:
        x_dot (float): Velocity in x direction
        y_dot (float): Velocity in y direction
        z_dot (float): Velocity in z direction

    Returns:
        speed (float): magitude of velocity vector
    """
    try:
        speed = math.sqrt(x_dot**2 + y_dot**2 + z_dot**2)
        return speed
    except (TypeError, ValueError) as e:
        logger.error(f"Invalid Velocity Components: x_dot={x_dot}, y_dot={y_dot}, z_dot={z_dot}. Error: {e}")
        raise

def epoch_to_datetime(epoch_str: str) -> datetime:
    """
    Converts epoch string to datetime object

    Args:
        epoch_str (str): Epoch timestamp string formatted as 'YYYY-DDDTHH:MM:SS.000Z'

    Returns:
        data (datetime): Parsed datetime object
    """
    try:
        year, day, hour, minute, second = (
            int(epoch_str[:4]),
            int(epoch_str[5:8]),
            int(epoch_str[9:11]),
            int(epoch_str[12:14]),
            int(epoch_str[15:17])
        )
        date = datetime(year, 1, 1) + timedelta(days=day - 1, hours=hour, minutes=minute, seconds=second)
        return date
    except ValueError as e:
        logger.error(f"Error parsing epoch: {e}")
        raise ValueError(f"Invalid epoch format: {epoch_str}") from e


def find_closest_epoch(data: List[Dict[str, Any]], target_time: datetime) -> Dict[str, Any]:
    """
    Determines state vector with epoch closest to target time

    Args:
        data (List[Dict[str, Any]]): List of state vectors
        target_time (datetime): Target time to find closest

    Returns:
        closest_state (Dict[str, Any]): State Vector with epoch closest to target time
    """
    closest_state = min(data, key=lambda state: abs((epoch_to_datetime(state['epoch']) - target_time).total_seconds()))
    return closest_state

def get_geolocation(lat: float, lon: float) -> str:
    """Return the approximate geographical location for given latitude & longitude."""
    geolocator = Nominatim(user_agent="iss_tracker")
    try:
        location = geolocator.reverse((lat, lon), exactly_one=True)
        return location.address if location else "Unknown Location"
    except Exception as e:
        logger.error(f"Error fetching geolocation: {e}")
        return "Unknown Location"

@app.route('/epochs', methods=['GET'])
def get_epochs():
    """
    Return all epochs with optional limit and offset query parameter
    """
    data = get_iss_data()
    limit = request.args.get('limit', default=None, type=int)
    offset = request.args.get('offset', default=0, type=int)
    result = data[offset:offset + limit] if limit else data[offset:]
    return jsonify(result)

@app.route('/epochs/<epoch>', methods=['GET'])
def get_epoch(epoch: str):
    """
    Return the state vector for a specific epoch
    """
    data = get_iss_data()
    for state in data:
        if state['epoch'] == epoch:
            return jsonify(state)
    return jsonify({'error': 'Epoch not found'}), 404

@app.route('/epochs/<epoch>/speed', methods=['GET'])
def get_epoch_speed(epoch: str):
    """
    Return the instantaneous speed for a specific epoch
    """
    data = get_iss_data()
    for state in data:
        if state['epoch'] == epoch:
            speed = calculate_speed(state['x_dot'], state['y_dot'], state['z_dot'])
            return jsonify({'epoch': epoch, 'speed_km_s': speed})
    return jsonify({'error': 'Epoch not found'}), 404

@app.route('/epochs/<epoch>/location', methods=['GET'])
def get_epoch_location(epoch: str):
    """Return latitude, longitude, altitude, and geoposition for a specific epoch."""
    logger.info(f"Fetching location data for epoch: {epoch}")
    data = get_iss_data()

    if not data:
        logger.error("No ISS data found in Redis!")
        return jsonify({'error': 'No ISS data available'}), 500

    for state in data:
        if state['epoch'] == epoch:
            lat = state['y']
            lon = state['x']
            altitude = state['z']

            # Check if latitude & longitude exist
            if lat is None or lon is None or altitude is None:
                logger.error(f"Missing data for epoch: {epoch}")
                return jsonify({'error': f'Missing data for epoch {epoch}'}), 500

            geolocation = get_geolocation(lat, lon)
            return jsonify({
                'epoch': epoch,
                'latitude': lat,
                'longitude': lon,
                'altitude_km': altitude,
                'geoposition': geolocation
            })
    logger.error(f"Epoch not found: {epoch}")
    return jsonify({'error': 'Epoch not found'}), 404

@app.route('/now', methods=['GET'])
def get_current_state():
    """
    Return the state vector closest to the current time
    """
    try:
        response = requests.get(ISS_NOW_URL, timeout=10)
        response.raise_for_status()
        data = response.json()

        position = data.get("iss_position", {})
        timestamp = data.get("timestamp")

        if "latitude" in position and "longitude" in position:
            lat = float(position["latitude"])
            lon = float(position["longitude"])
            geolocation = get_geolocation(lat, lon)

            return jsonify({
                "timestamp": timestamp,
                "latitude": lat,
                "longitude": lon,
                "geoposition": geolocation
            }), 200
        else:
            return jsonify({"error": "Invalid response format"}), 500
    except requests.RequestException as e:
        logger.error(f"Error fetching ISS position: {e}")
        return jsonify({"error": "Failed to retrieve real-time ISS position"}), 500

if __name__ == '__main__':
    # Ensure data is loaded into Redis on startup
    logger.info("Starting ISS Tracker")
    
    # Ensure data is loaded into Redis on startup
    data = get_iss_data()
    if not data:
        logger.error("No data loaded into Redis on startup!")

    app.run(debug=True, host='0.0.0.0', port=5000)
