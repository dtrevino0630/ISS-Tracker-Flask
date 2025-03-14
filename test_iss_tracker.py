import pytest
import requests
import json
from datetime import datetime
from unittest.mock import patch, MagicMock
from iss_tracker import (
    get_iss_data,
    calculate_speed,
    epoch_to_datetime,
    find_closest_epoch,
    get_geolocation,
    app
)

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

def test_calculate_speed():
    """Test velocity magnitude calculation."""
    assert calculate_speed(0, 0, 0) == 0
    assert calculate_speed(3, 4, 0) == 5
    assert pytest.approx(calculate_speed(-3, 4, 0)) == 5
    assert pytest.approx(calculate_speed(1.5, 2.0, 2.5), abs=0.001) == 3.5355

def test_epoch_to_datetime():
    """Test epoch string conversion to datetime."""
    dt = epoch_to_datetime("2025-069T12:00:00.000Z")
    assert dt == datetime(2025, 3, 10, 12, 0, 0)
    
    with pytest.raises(ValueError):
        epoch_to_datetime("Invalid Format")

def test_find_closest_epoch():
    """Test finding the closest state vector."""
    sample_data = [
        {"epoch": "2025-069T12:00:00.000Z", "x_dot": 1, "y_dot": 2, "z_dot": 3},
        {"epoch": "2025-069T13:00:00.000Z", "x_dot": 4, "y_dot": 5, "z_dot": 6},
    ]
    target_time = datetime(2025, 3, 10, 12, 30, 0)
    closest = find_closest_epoch(sample_data, target_time)
    assert closest["epoch"] == "2025-069T12:00:00.000Z"

def test_get_iss_data(monkeypatch):
    """Mock ISS data request."""
    class MockResponse:
        def __init__(self, text):
            self.text = text

        def raise_for_status(self):
            pass

    mock_xml = '''<ndm><oem><body><segment><data>
        <stateVector>
            <EPOCH>2025-069T12:00:00.000Z</EPOCH>
            <X units="km">1000.0</X>
            <Y units="km">2000.0</Y>
            <Z units="km">3000.0</Z>
            <X_DOT units="km/s">1.0</X_DOT>
            <Y_DOT units="km/s">2.0</Y_DOT>
            <Z_DOT units="km/s">3.0</Z_DOT>
        </stateVector>
        </data></segment></body></oem></ndm>'''

    def mock_get(*args, **kwargs):
        return MockResponse(mock_xml)

    monkeypatch.setattr(requests, "get", mock_get)
    data = get_iss_data()
    assert data is not None, "get_iss_data returned None"
    assert len(data) >= 1, f"Expected at least 1 state vector, but got {len(data)}"
    assert any(d["epoch"] == "2025-069T12:00:00.000Z" for d in data)

def test_get_geolocation():
    """Test geolocation retrieval with mocking."""
    with patch("iss_tracker.Nominatim") as mock_geolocator:
        mock_instance = mock_geolocator.return_value
        mock_instance.reverse.return_value.address = "Austin, TX, USA"
        
        result = get_geolocation(30.2672, -97.7431)
        assert result == "Austin, TX, USA"

def test_flask_routes(client):
    """Test Flask API endpoints."""
    response = client.get("/epochs")
    assert response.status_code == 200
    
    response = client.get("/epochs/2025-069T12:00:00.000Z")
    assert response.status_code in [200, 404]
    
    response = client.get("/epochs/2025-069T12:00:00.000Z/speed")
    assert response.status_code in [200, 404]
    
    response = client.get("/now")
    assert response.status_code == 200
