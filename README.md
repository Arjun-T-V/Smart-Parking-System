# PARKEASE — Smart Mall Parking Management System

<p align="center">
  <strong>Intelligent Parking. Smarter Decisions.</strong>
</p>

<p align="center">
  A Django-based smart parking management platform integrating IoT, database management, and machine learning to improve parking availability and user experience in shopping malls.
</p>

---

## Overview

**PARKEASE** is a Smart Mall Parking Management System designed to simplify vehicle parking inside large shopping malls.

Finding an available parking space in a busy shopping mall can be time-consuming. PARKEASE aims to address this problem by providing a centralized platform where users can explore parking floors, check slot availability, register vehicles, reserve parking spaces, and monitor parking information.

The system integrates **Django for backend development, SQLite for database management, IoT sensors for vehicle detection, and Machine Learning for parking-duration prediction**.

The long-term objective is to estimate how long an occupied parking slot may take to become available, helping users make informed parking decisions.

## Key Features

### 1. User Management
- User registration and login.
- User authentication.
- Personalized user dashboard.
- Vehicle registration and management.

### 2. Smart Parking Management
- Multiple-floor parking management.
- Individual parking slot management.
- Real-time sensor status display.
- Slot availability checking.
- Parking slot reservation.
- Booking history and cancellation management.

### 3. IoT Integration
- ESP32-based sensor integration architecture.
- IR sensor-based vehicle detection.
- Device identification using unique device IDs.
- Authenticated communication between IoT devices and Django.
- Automatic parking-session creation when a vehicle is detected.
- Automatic parking-session closure when a slot becomes clear.
- Sensor states: DETECTED, CLEAR, and UNKNOWN.

### 4. Machine Learning
- Parking-duration prediction using Random Forest Regression.
- Extraction of parking-related features.
- Prediction of estimated parking duration.
- Calculation of remaining parking time using recorded session information.
- Model evaluation using Mean Absolute Error (MAE).
- Exclusion of synthetic, test, and unverified records from genuine-data training.

### 5. Administration
- Administrative dashboard.
- Booking management.
- Parking occupancy reporting.
- Parking floor and slot management through the Django administration interface.

### 6. Payment Management
- Payment-related database structure.
- Booking-associated payment records.
- Checkout interface.

*Payment gateway integration and live transaction processing depend on the implemented payment configuration.*

---

## Technology Stack

| Component | Technology |
|---|---|
| Frontend | HTML5, CSS3, JavaScript |
| Backend | Python, Django |
| Database | SQLite |
| Machine Learning | Scikit-learn |
| ML Algorithm | Random Forest Regressor |
| Data Processing | Pandas |
| Model Serialization | Joblib |
| IoT Microcontroller | ESP32 |
| Sensor | IR Sensor |
| API Communication | HTTP / JSON |
| Development Environment | Visual Studio Code |
| Version Control | Git and GitHub |

---

## System Architecture

PARKEASE follows a Django-based application architecture in which the frontend, backend, database, IoT module, and ML module communicate to provide parking-management functionality.

```text
                   USER
                    |
                    v
             FRONTEND INTERFACE
               HTML / CSS / JS
                    |
                    v
             DJANGO APPLICATION
                    |
          +---------+----------+
          |                    |
          v                    v
     DJANGO VIEWS          DJANGO MODELS
          |                    |
          |                    v
          |                SQLITE DB
          |
    +-----+----------------+
    |                      |
    v                      v
  IoT MODULE             ML MODULE
    |                      |
    v                      v
 ESP32 + IR SENSOR    RANDOM FOREST MODEL
    |                      |
    v                      v
 Vehicle Detection    Duration Prediction
    |                      |
    +----------+-----------+
               |
               v
       PARKING INFORMATION
               |
               v
          USER DASHBOARD
```

## How the System Works

### 1. User Interaction

Users register or log in to the PARKEASE platform. After authentication, they can access the dashboard, manage their vehicles, view parking floors, and interact with the booking system.

### 2. Parking Slot Management

The system maintains parking floors and individual parking slots in the database.

Users can check slot availability for a selected arrival and departure time and proceed with booking when a slot is available.

### 3. IoT-Based Vehicle Detection

An IR sensor detects the presence or absence of a vehicle in a parking slot.

The ESP32 sends the sensor information to the Django backend through an authenticated HTTP POST request.

The backend processes the sensor event:

- DETECTED: Creates a parking session if no active session exists.
- CLEAR: Closes the active parking session.
- UNKNOWN: Represents an unconfirmed sensor state.

The system records parking entry and exit timestamps in the database.

### 4. Machine Learning-Based Prediction

The machine-learning module is designed to predict the duration of a parking session.

The training process extracts the following features:

| Feature | Description |
|---|---|
| Entry Hour | Hour at which the vehicle entered |
| Day of Week | Day on which the vehicle entered |
| Floor Number | Parking floor where the vehicle is parked |
| Is Weekend | Indicates whether the entry occurred on a weekend |

**Target variable:** Parking duration in minutes.

The model uses Random Forest Regression to estimate parking duration.

The estimated remaining parking time can then be calculated using:

```text
Remaining Time = Predicted Duration - Elapsed Time
```

The prediction is intended to help estimate when an occupied parking slot may become available.

---

## Machine Learning Workflow

The ML component follows these stages:

1. Collect completed parking-session records.
2. Verify the origin and quality of the records.
3. Exclude synthetic and test sessions.
4. Exclude unverified sessions.
5. Extract relevant parking features.
6. Split the dataset into training and testing sets.
7. Train the Random Forest Regression model.
8. Evaluate the model using Mean Absolute Error.
9. Save the trained model using Joblib.
10. Load the model for prediction through the Django application.

### Model Configuration

| Parameter | Configuration |
|---|---|
| Algorithm | Random Forest Regressor |
| Number of Estimators | 200 |
| Minimum Samples per Leaf | 3 |
| Random State | 42 |
| Evaluation Metric | Mean Absolute Error |

### Data Quality and Training Requirements

PARKEASE distinguishes between genuine parking records and artificially generated testing records.

The training pipeline uses:
- `synthetic_sessions_manifest.csv` to identify synthetic session IDs.
- `unverified_sessions.csv` to identify sessions requiring verification.
- `is_test_data` to identify controlled test sessions.

A minimum of **30 eligible genuine completed sessions** is required before the current training script proceeds.

**Current development status:** The IoT endpoint has been tested using controlled test events. The latest ML training attempt identified only one eligible completed session, so model training correctly stopped. Additional verified real-world parking data is required before a reliable model can be trained and evaluated.

---

## Project Directory Structure

```text
project_parking/
│
├── manage.py
├── db.sqlite3
│
├── train_model.py
├── generate_test_sessions.py
├── export_ground_floor_dataset.py
│
├── ground_floor_parking.csv
├── synthetic_sessions_manifest.csv
├── unverified_sessions.csv
│
├── project_parking/
│   ├── settings.py
│   ├── urls.py
│   └── ...
│
└── parking/
    │
    ├── admin.py
    ├── forms.py
    ├── models.py
    ├── views.py
    ├── urls.py
    ├── payment_utils.py
    │
    ├── ml/
    │   ├── __init__.py
    │   └── predictor.py
    │
    ├── ml_model/
    │   └── parking_duration_model.joblib
    │
    ├── static/
    │   └── parking/
    │       └── css/
    │           ├── design-system.css
    │           └── parking_slots.css
    │
    └── templates/
        └── parking/
            ├── home.html
            ├── login.html
            ├── register.html
            ├── dashboard.html
            ├── parking_slots.html
            ├── book_slot.html
            ├── my_bookings.html
            ├── my_vehicles.html
            ├── admin_dashboard.html
            ├── admin_bookings.html
            ├── occupancy_report.html
            └── payment_checkout.html
```

## Important Files and Their Responsibilities

| File | Responsibility |
|---|---|
| `manage.py` | Django project management commands |
| `settings.py` | Main application configuration |
| `project_parking/urls.py` | Main URL routing |
| `parking/urls.py` | Application URL routing |
| `models.py` | Database models |
| `views.py` | Backend application logic |
| `forms.py` | Form handling and validation |
| `admin.py` | Django administration configuration |
| `payment_utils.py` | Payment-related helper functions |
| `train_model.py` | ML model training and evaluation |
| `predictor.py` | Model loading and prediction logic |
| `generate_test_sessions.py` | Synthetic session generation |
| `export_ground_floor_dataset.py` | Parking dataset export |
| `parking_slots.html` | Parking slot interface |
| `design-system.css` | Shared UI design system |
| `parking_slots.css` | Parking page styling |

---

## Database Design

PARKEASE uses SQLite as its development database.

The main database models include:

| Model | Purpose |
|---|---|
| ParkingFloor | Stores parking floor information |
| ParkingSlot | Stores individual parking slots and their status |
| Booking | Stores user parking reservations |
| Vehicle | Stores user vehicle information |
| IoTSensor | Stores sensor device information and state |
| ParkingSession | Stores actual vehicle entry and exit records |
| Payment | Stores payment information associated with bookings |

### Parking Session Management

The `ParkingSession` model is particularly important for the ML component.

It records:

- Parking slot.
- Associated booking, if applicable.
- Entry timestamp.
- Exit timestamp.
- Test-data classification.

Parking duration is calculated from the difference between the entry and exit timestamps.

Only completed, eligible, verified sessions should be considered for genuine ML training.

---

## Installation and Setup

### Prerequisites

Install the following before setting up the project:

- Python 3.10 or later.
- Git.
- Visual Studio Code (recommended).
- pip package manager.

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/PARKEASE.git
```

Navigate into the project directory:

```bash
cd project_parking
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
```

### 3. Activate the Virtual Environment

For Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 4. Install Dependencies

```bash
python -m pip install Django pandas scikit-learn joblib requests
```

### 5. Configure the IoT Device Token

Configure `IOT_DEVICE_TOKEN` in your Django settings or through a secure environment variable.

Use a strong secret token. Do not commit the actual token to GitHub.

### 6. Apply Database Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Create an Administrator Account

```bash
python manage.py createsuperuser
```

### 8. Start the Development Server

```bash
python manage.py runserver
```

Open the application in your browser:

```text
http://127.0.0.1:8000/
```

---

## IoT API Integration

The Django backend provides an endpoint for receiving sensor updates.

**Endpoint:**

```text
POST /api/iot/sensor-update/
```

**Authentication:**

```text
Authorization: Bearer YOUR_DEVICE_TOKEN
```

**Example request body:**

```json
{
  "device_id": "ESP32_SLOT_002",
  "state": "DETECTED"
}
```

To close the parking session:

```json
{
  "device_id": "ESP32_SLOT_002",
  "state": "CLEAR"
}
```

For controlled development tests, the endpoint also accepts:

```json
{
  "device_id": "ESP32_SLOT_002",
  "state": "DETECTED",
  "test_mode": true
}
```

Test-mode sessions are stored with `is_test_data=True` and excluded from genuine ML training.

The endpoint validates the device token, request format, device ID, and sensor state before processing the event.

---

## Testing

The project supports controlled testing of its backend and IoT communication.

### Django System Check

```bash
python manage.py check
```

### Database Migration Check

```bash
python manage.py makemigrations --check --dry-run
```

### IoT Endpoint Testing

A Python test script, `test_iot_session.py`, can send authenticated sensor events to the local Django server.

The controlled test verified:

- Successful HTTP communication.
- Device authentication.
- Sensor state update.
- Parking-session creation.
- Parking-session closure.
- Correct test-data classification.

The controlled Slot 02 test successfully created and closed Session 1003, with `is_test_data=True`.

---

## Current Development Status

| Component | Status |
|---|---|
| Django application setup | Implemented |
| User authentication pages | Implemented |
| Parking floor and slot management | Implemented |
| Vehicle management | Implemented |
| Booking functionality | Implemented |
| Parking session database | Implemented |
| IoT update endpoint | Tested using controlled requests |
| Test-data identification | Implemented and verified |
| ML training pipeline | Implemented; awaiting sufficient genuine data |
| ML prediction integration | Implemented with model-validation safeguards; real-data validation pending |
| Physical ESP32 and IR sensor operation | Hardware-level verification pending |
| Payment processing | Payment-related components present; gateway status depends on configuration |

---

## Future Enhancements

The following improvements are planned for future development:

- Complete physical ESP32 and IR sensor integration.
- Collect a larger dataset of genuine parking sessions.
- Train and validate the ML model using real parking behaviour.
- Improve prediction accuracy through feature engineering.
- Add more advanced parking occupancy analytics.
- Integrate a production-ready payment gateway.
- Deploy the platform to a cloud server.
- Add notifications for booking confirmation and parking availability.
- Improve security, scalability, and production monitoring.

---

## Project Objective

The primary objective of PARKEASE is to make shopping mall parking more efficient through automation, real-time occupancy information, and predictive analytics.

By combining web technologies, IoT-based vehicle detection, and machine learning, PARKEASE aims to reduce the time spent searching for parking spaces and improve the overall parking experience.

---

## Author

**Arjun T. V**

B.Tech – Computer Engineering

Vimal Jyothi Engineering College  
Kerala, India

---

<p align="center">
  <strong>PARKEASE — Smart Parking for Smarter Cities.</strong>
</p>
