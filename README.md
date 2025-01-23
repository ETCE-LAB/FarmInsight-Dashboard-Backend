<img src="https://github.com/user-attachments/assets/bb514772-084e-439f-997a-badfe089be76" width="300">

# FarmInsight-Dashboard-Backend

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Development Setup](#development-setup)
- [Running the Application](#running-the-application)
- [API Endpoints](#api-endpoints)
- [Contributing](#contributing)
- [License](#license)

## Overview
## Features

## Development Setup

### Set up InfluxDB in Docker

This guide provides step-by-step instructions for setting up InfluxDB within a Docker container, configuring it with 
environment variables, and managing it using Docker Compose.

#### Prerequisites

Ensure you have Docker installed on your system. 
If you do not have Docker installed, please follow the installation instructions on the [official Docker website](https://docs.docker.com/get-docker/).

#### Configuration

**Environment File Setup**:

Configure your local environment settings by creating an `.env.dev` file inside the `/django-server/environment/` directory. 
This file should contain all necessary environment variables for InfluxDB.
Example of `.env.dev`:
```
INFLUXDB_URL=http://localhost:8086
DOCKER_INFLUXDB_INIT_USERNAME=admin
INFLUXDB_INIT_PASSWORD=your_password
INFLUXDB_INIT_TOKEN=your_token
DOCKER_INFLUXDB_INIT_ORG=ETCE-LAB

DEBUG=True
SECRET_KEY=django-insecure-j_qnae2dq2!wltq1%ca7gku^ol8o7^t9-1xg5)gjw*1kcl)!d8

ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:3000
CORS_ALLOWED_ORIGINS=http://localhost:3000

RESOURCE_SERVER_INTROSPECTION_URL=https://development-isse-identityserver.azurewebsites.net/connect/introspect

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
Start on 
```
python manage.py runsever
```
Run on a desired port
```
python manage.py runserver localhost:8002 
```

If necessary, migrate the database
```
python manage.py makemigrations
python manage.py migrate
```

## Running the application
### Manual Querying of data with Influx CLI

To check the data stored within your InfluxDB buckets, you can use the InfluxDB CLI (e.g. in Docker Desktop). 
Below is an example command to query data from a specific bucket:
```
influx query 'from(bucket:"c7e6528b-76fd-4895-8bb9-c6cd500fc152") |> range(start: -1000y) |> filter(fn: (r) => r._measurement == "SensorData")'
```

## API Endpoints
## Contributing
## License
