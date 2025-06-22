<img src="https://github.com/user-attachments/assets/bb514772-084e-439f-997a-badfe089be76" width="300">

# FarmInsight-Dashboard-Backend

## Table of Contents

- [The FarmInsight Project](#the-farminsight-project)
  - [Core vision](#core-vision)
- [Overview](#overview)
  - [Built with](#built-with)
- [Features](#features)
  - [Organizations](#organizations)
  - [Sensors](#sensors)
  - [Cameras](#cameras)
  - [User Authentication](#user-authentication)
- [Development Setup](#development-setup)
  - [Set up Python](#set-up-python)
  - [Install required packages](#install-required-packages)
  - [Create your oicd.key](#create-your-oicdkey)
  - [Set up InfluxDB in Docker](#set-up-influxdb-in-docker)
- [Running the Application](#running-the-application)
  - [Manual Querying of data with Influx CLI](#manual-querying-of-data-with-influx-cli)
  - [Pitfalls during development](#pitfalls-during-development)
  - [Administrative actions](#administrative-actions)
- [Contributing](#contributing)
- [License](#license)

## The FarmInsight Project
Welcome to the FarmInsight Project by ETCE!

The FarmInsight platform brings together advanced monitoring of "Food Production Facilities" (FPF), enabling users to 
document, track, and optimize every stage of food production seamlessly.

All FarmInsight Repositories:
* <a href="https://github.com/ETCE-LAB/FarmInsight-Dashboard-Frontend">Dashboard-Frontend</a>
* <a href="https://github.com/ETCE-LAB/FarmInsight-Dashboard-Backend">Dashboard-Backend</a>
* <a href="https://github.com/ETCE-LAB/FarmInsight-FPF-Backend">FPF-Backend</a>

### Core vision

<img src="/.documentation/FarmInsightOverview.jpg">

FarmInsight empowers users to manage food production facilities with precision and ease. 

Key features include:

* User Management: Set up organizations with role-based access control for secure and personalized use.
* FPF Management: Configure and manage Food Production Facilities (FPFs), each equipped with sensors and cameras.
* Sensor & Camera Integration: Collect sensor data and capture images or livestreams at configurable intervals, all 
accessible through the web application.
* Harvest Documentation: Log and track harvests for each plant directly from the frontend interface.
* Data Visualization: Visualize sensor data with intuitive graphs and charts.
* Media Display: View and manage captured images and livestreams for real-time monitoring.


## Overview

This repository contains the central backend code for FarmInsight and manages all configurations as well as representing a gateway from the clients to all FPF devices.
The backend communicates with an InfluxDB to store and retrieve sensor data, while images are stored in a directory with their metadata saved in an SQLite database.
Data is delivered to clients via REST APIs and, for live updates, via websockets. Livestreams are routed from an endpoint to clients in real time.

Using an internal scheduler, the backend periodically requests images from configured endpoints at specified intervals. Once received, the images are stored and made accessible to the client.

### Built with

[![Python][Python-img]][Python-url] <br>
[![Django][Django-img]][Django-url] <br>
[![InfluxDB][Influx-img]][Influx-url] <br>
[![SQLite][SQLite-img]][SQLite-url]

## Features

### Organizations
Organizations can have multiple members with two user roles: Admin and Member.
Each organization can manage multiple Food Production Facilities (FPFs).

### Sensors

Members of an organization can create or edit sensors if the FPF exists and is accessible by the Dashboard Backend.
Sensor configurations are partially stored in the SQLite database, while hardware details are forwarded to and managed by the FPF Backend.
Sensor measurements are sent from the FPF Backend to the Dashboard Backend at configured intervals via REST APIs.
All sensor data is stored in InfluxDB, organized by FPF into buckets for efficient access.

### Cameras
Users can configure cameras to:
- Capture images at specified intervals.
- Stream live video via supported protocols, including HTTP and RTSP.

Camera setup and editing require the user to be a member of the organization, and the FPF must be accessible by the Dashboard Backend.

### Controllable actions
Controllable actions control the FPF where specified action scripts are running based on configured triggers.
When a trigger triggers, the action script calls the hardware (e.g. via HTTP) to trigger the desired action.
The hardware can for example be a smart plug, or other network capable devices.

If a controllable action is triggered, an appropriate entry will be created in an internal action queue. 
A queue worker will process the open entries in this queue. There additional logic will be performed to check if this action is executable on the specific hardware.

#### Adding a new action (script)
Custom Action scripts can be added easily by following the existing convention.
Just add a class on the package django_server/farminsight_dashboard_backend/action_scripts
See for example the existing http_action_scripts.py and take it as a template.
Give your new class the desired logic and add a new UUID as the action_script_class_id.
Make sure to export the new class in the package '__init__' file.

### Weather forecast
Locations can be added for a FPF and one location can be marked for the weather data forecast gathering.
With an external API, the weather forecast for the upcoming 16 days will be gathered and stored in the Influx DB.

### User Authentication
The backend uses standard Django user authentication.
Users can register and log in through the frontend.

## Development Setup

### Set up Python

You will need to install Python on your local machine if you havent done it already.
The code was written and tested with `Python` version `3.11.3` and `pip` version `24.3.1`. Please feel free to use newer versions.

* To check which pip version is installed in your local system, please run:
  ```sh
  pip --version
  ```
* To check which python version is installed in your local system, please run:
  ```sh
  python --version
  ```
* To install pip, please run:
  ```sh
  pip install
  ```
* To install Python, please download and install your desired version https://www.python.org/

### Install required packages

To install all required packages for the python related parts of the application you can navigate to the `/django_server` 
directory and run the following `pip` command or install the packages.
   ```sh
   pip install -r requirements.txt
   ```

### Create your oicd.key
You may need to [download and install openSSL](https://openssl-library.org/source/) to run the following command.
   ```sh
   openssl genrsa -out oidc.key 4096
   ```

### Set up InfluxDB in Docker

The backend runs without influx db, however, if you want to store measurements for sensors, you must have a reachable influx DB.

This guide provides step-by-step instructions for setting up InfluxDB within a Docker container, configuring it with 
environment variables, and managing it using Docker Compose.

#### Prerequisites

Ensure you have Docker installed on your system. 
If you do not have Docker installed, please follow the installation instructions on the [official Docker website](https://docs.docker.com/get-docker/).

#### Configuration

**Environment File Setup**:

Configure your local environment settings by creating an `.env.dev` file inside the `/django-server/` directory. 
This file should contain all necessary environment variables for InfluxDB.
Example of `.env.dev`:
```
INFLUXDB_URL=http://localhost:8086
DOCKER_INFLUXDB_INIT_USERNAME=admin
INFLUXDB_INIT_PASSWORD=your_password
INFLUXDB_INIT_TOKEN=your_token
DOCKER_INFLUXDB_INIT_ORG=ETCE-LAB
AUTH_SERVICE_URL=URL/connect/token
REACT_APP_BACKEND_URL=URL
DEBUG=bool
ALLOWED_HOSTS="comma separated list of urls"
CSRF_TRUSTED_ORIGINS="comma separated list of urls"
CORS_ALLOWED_ORIGINS="comma separated list of urls"
SECRET_KEY=RANDOM_SECRET_KEY!!
OIDC_ISS_ENDPOINT=Own endpoint including domains if necessary

CLIENT_ID=client_id
CLIENT_SECRET=client_secret
```

#### Docker Setup

Using Docker Compose is the recommended way to manage your InfluxDB container.
It simplifies the startup, shutdown, and maintenance of Docker applications.

- **To Start the InfluxDB Container**:
```
  docker-compose --env-file .env.dev up -d
```
- **To Stop the InfluxDB Container**:
```
docker-compose down
```

#### Starting the Django app
If necessary, migrate the SQLite database and load the default application
```sh
python manage.py makemigrations
python manage.py migrate
python manage.py loaddata application
```

Start on 
```sh
python manage.py runsever
```

Run on a desired port
```sh
python manage.py runserver localhost:8000 
```


## Running the application
### Manual Querying of data with Influx CLI

To check the data stored within your InfluxDB buckets, you can use the InfluxDB CLI (e.g. in Docker Desktop) or the web interface. 
Below is an example command to query data from a specific bucket:
```
influx query 'from(bucket:"c7e6528b-76fd-4895-8bb9-c6cd500fc152") |> range(start: -1000y) |> filter(fn: (r) => r._measurement == "SensorData")'
```
### Pitfalls during development
When startup fails check that the .env.dev and oidc.key file exist and are filled out correctly.


When you encounter **Error: invalid_request Invalid client_id parameter value.** while trying to log in it means your database is not fully setup.
To remedy this and setup an application and default admin superuser (pw:1234) **DEVELOPMENT ONLY**:
```sh
python manage.py loaddata application
```

The FPF-Backend is setup so it can only be one FPF at a time, if the Dashboard backend DB gets emptied and you want to create a new FPF, u also need to empty the FPF-Backend configuration tables.
### Administrative actions
Deleting user accounts or doing other potentially necessary cleanup of Database entries not covered through the standard can be done through the django admin panel.

To do that one needs an admin accounts with privileges, in our case that's Benjamin Leidings account and the admin Account (pw is with Anant), and log into the admin panel, ours: [farminsight backend](https://farminsight-backend.etce.isse.tu-clausthal.de/admin/).

By the standard configuration only the Userprofile is editable, to edit all models edit the "farminsight_dashboard_backend/admin.py" file and enable the following code:
```python
from django.apps import apps
app = apps.get_app_config('farminsight_dashboard_backend')
for model_name, model in app.models.items():
    admin.site.register(model)
```
If there is no admin account with adequate rights you need to create a superuser using the console interface:
```sh
python manage.py createsuperuser
```

## Contributing

This project was developed as part of the Digitalisierungsprojekt at DigitalTechnologies WS24/25 by:
* Tom Luca Heering
* Theo Lesser
* Mattes Knigge
* Julian Schöpe
* Marius Peter

Project supervision:
* Johannes Meier
* Benjamin Leiding

Many thanks to Anant for the deployment!

## License



<!-- MARKDOWN LINKS & IMAGES -->
[Python-img]: https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54
[Python-url]: https://www.python.org/
[Django-img]: https://img.shields.io/badge/django-%23092E20.svg?style=for-the-badge&logo=django&logoColor=white
[Django-url]: https://www.djangoproject.com/
[Influx-img]: https://img.shields.io/badge/InfluxDB-22ADF6?style=for-the-badge&logo=InfluxDB&logoColor=white
[Influx-url]: https://www.influxdata.com/
[SQLite-img]: https://img.shields.io/badge/sqlite-%2307405e.svg?style=for-the-badge&logo=sqlite&logoColor=white
[SQLite-url]: https://www.sqlite.org/
