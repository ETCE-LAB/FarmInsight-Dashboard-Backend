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

This repository contains the central backend code for FarmInsight.
The Dashboard backend communicates with an InfluxDB to store and load all sensor data.
Images are stored in a directory, the metadata is stored in the SQLite DB.
Images and sensor measurements to the clients via REST, and for live updates, via websockets.
Livestreams are retrieved from an endpoint and are routed through to the client.

Based on an internal scheduler, the backend will request the images on the configured interval from the configured 
endpoint. Once the image is received, it will be stored in the directory.



### Built with

[![Python][Python-img]][Python-url] <br>
[![Django][Django-img]][Django-url] <br>
[![InfluxDB][Influx-img]][Influx-url] <br>
[![SQLite][SQLite-img]][SQLite-url]

## Features

### Organizations
One organization can have one to many members with two different user levels (Admin and Member).
Additionally, an organization can have many FPF.

### Sensors

In order to create or edit a sensor, the user must be a member of the organization and the FPF must exist and be reachable by the Dashboard-Backend.

The backend will store some of the sensor configuration in the SQLite db. The hardware details for the sensor are getting forwarded and stored at the FPF-Backend.

The FPF-Backend sends the sensor measurements in the given interval to the dashboard backend via a REST operation.
Sensor measurements are stored in an influxDB to store and load all sensor data. The data is organized by the fpf which builds a bucket.

### Cameras
The user can configure a camera to save on a give interval images and to view a livestream.
In order to create or edit a camera, the user must be a member of the organization and the FPF must exist and be reachable by the Dashboard-Backend.

Supported livestream protocols are HTTP and RTSP.

### User Authentication
The backend provides the standard django user authentication. User can register and login through the frontend.

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
If necessary, migrate the SQLite database
```sh
python manage.py makemigrations
python manage.py migrate
```

Start on 
```sh
python manage.py runsever
```

Run on a desired port
```sh
python manage.py runserver localhost:8002 
```


## Running the application
### Manual Querying of data with Influx CLI

To check the data stored within your InfluxDB buckets, you can use the InfluxDB CLI (e.g. in Docker Desktop) or the web interface. 
Below is an example command to query data from a specific bucket:
```
influx query 'from(bucket:"c7e6528b-76fd-4895-8bb9-c6cd500fc152") |> range(start: -1000y) |> filter(fn: (r) => r._measurement == "SensorData")'
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
