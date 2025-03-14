# **ISS Tracker Flask**

## **Overview**
The **ISS Tracker API** is a Flask-based web application designed to track and retrieve real-time trajectory data of the **International Space Station (ISS)**. The API fetches ISS state vector data from **NASA's public data source** and stores it in a **Redis database** for efficient querying. This application allows users to access ISS location details, compute speed, and retrieve real-time positional data.

## Features
- Fetches and stores ISS trajectory data in a **Redis Database**
- Provides **RESTful API endpoints** to retrieve ISS position, velocity, and speed.
- Implements **pagination** for querying large datasets.
- Supports **real-time ISS tracking** via Open Notify API.
- Containerized deployment using **Docker and Docker Compose**.

## **Data Sources**
- **NASA ISS OEM Data**: Provides historical and predicted ISS state vectors ([NASA Data](https://nasa-public-data.s3.amazonaws.com)).
- **Open Notify API**: Supplies real-time ISS altitude and longitude ([Open Notify](http://api.open-notify.org/iss-now.json)).

---

## **Installation & Setup**

### **1. Prerequisites**
Ensure you have the following installed:
- **Python 3.9+**
- **Docker & Docker Compose**
- **Redis** (if running outside of Docker)

### **2. Clone the Repository**
```sh
git clone https://github.com/dtrevino0630/ISS-Tracker-Flask.git
cd ISS-Tracker-Flask
```

### **3. Running the Application with Docker**
Build and start the Flask and Redis containers:
```
docker-compose up -d
```
The Flask API will be accessible at ```https://localhost:5000```

## **Flask API Endpoints**
| **Routes**                      | **Method**  | **Description**                                                                    | **Example Code**                                                      |
|---------------------------------|-------------|------------------------------------------------------------------------------------|-----------------------------------------------------------------------|
| `/epochs`                       | **GET**     | Returns the **entire dataset** of ISS state vectors.                               | `curl http://localhost:5000/epochs`                                  |
| `/epochs?limit=int&offset=int`  | **GET**     | Returns **paginated results** (limit & offset).                                    | `curl http://localhost:5000/epochs?limit=5&offset=2`                |
| `/epochs/<epoch>`               | **GET**     | Returns **state vector** for a given epoch.                                        | `curl http://localhost:5000/epochs/2025-045T12:00:00.000Z`           |
| `/epochs/<epoch>/speed`         | **GET**     | Returns **instantaneous speed** for a given epoch.                                 | `curl http://localhost:5000/epochs/2025-045T12:00:00.000Z/speed`     |
| `/epochs/<epoch>/location`      | **GET**     | Returns **latitude, longitude, altitude, and geoposition** for a given epoch.      | `curl http://localhost:5000/epochs/2025-045T12:00:00.000Z/location`  |
| `/now`                          | **GET**     | Returns **closest epoch to current time** with speed.                              | `curl http://localhost:5000/now`                                     |

## **Functions**
### `get_iss_data() -> List[Dict[str, Any]]`
Retrieves and parses ISS trajectory data from NASA's API.

### `calculate_speed(x_dot: float, y_dot: float, z_dot: float) -> float`
Computes the speed of the ISS using Cartesian velocity components.

### `epoch_to_datetime(epoch_str: str) -> datetime`
Converts an ISS epoch timestamp to a Python `datetime` object.

### `find_closest_epoch(data: List[Dict[str, Any]], target_time: datetime) -> Dict[str, Any]`
Finds the state vector closest to a given timestamp.

### `get_data_stats(data: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, Any], float, float]`
Computes the first and last epochs, average speed, and current speed.

## **Testing**
Unit tests are included to validate core functionalities. Run tests using:
```
docker exec -it iss_tracker_app pytest
```
or
```
pytest test_iss_tracker.py
```

## **Example Output**
The following display some sample requests and their respective output:
```
Request: curl http://localhost:5000/epochs/"2025-074T11:58:54.000Z"
Output:
"epoch": "2025-074T11:58:54.000Z",
  "x": 4638.50967061093,
  "x_dot": -3.10239546117154,
  "y": 4923.49202146089,
  "y_dot": 3.65439585849351,
  "z": -611.975207675823,
  "z_dot": 5.98179479415363

Request: curl http://localhost:5000/epochs/"2025-074T11:58:54.000Z"/speed
Output:
"epoch": "2025-074T11:58:54.000Z",
  "speed_km_s": 7.66559427881725

Request: curl http://localhost:5000/now
Output:
"current_state": {
    "epoch": "2025-063T10:38:30.000Z",
    "x": 1996.24794417011,
    "x_dot": 4.46867852495624,
    "y": -6496.35831735636,
    "y_dot": 1.59149019181892,
    "z": -241.393686237859,
    "z_dot": -6.01045329554794
```

## **Cleaning Up Container**
To stop and remove containers, run:
```
docker-compose down
```
To remove all stopped containers:
```
docker system prune -a
```

## Software Diagram
Below is a software diagram illustrating the key components and data flow of the ISS Tracker API:

The system consists of several interconnected components:
- **User Requests:** Clients send API requests to the Flask server.
- **Flask API:** The central application logic that processes requests and retrieves ISS data.
- **Redis Database:** Stores ISS trajectory data for fast access, reducing the need for frequent API calls.
- **NASA & Open Notify APIs:** External data sources providing ISS trajectory and real-time location data.
- **Docker Containers:** The Flask API and Redis database run inside the Docker containers for portability and easy deployment.

When a user queries an endpoint, Flask first checks Redis for cached ISS data. If data is missing, Flask fetches new data from NASA's API, processes it, and stores it in
Redis before returning it to the user. The ```/now``` endpoint directly queries Open Notify for real-time ISS location updates.
![Software Diagram](diagram.png)

### AI Assisted Development
AI tools played a role in determining Unit Tests for the program and error-solving/research for certain code programs. AI was used as a resource to expand knowledge and allow clarity in certain regions. All code was reviewed and analyzed for quality and accuracy if it happened to have assistance from AI.


