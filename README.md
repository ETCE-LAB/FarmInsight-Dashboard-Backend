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

Configure your local environment settings by creating an `.env.dev` file inside the `/django-server/` directory. 
This file should contain all necessary environment variables for InfluxDB.
Example of `.env.dev`:
```
INFLUXDB_URL=http://localhost:8086
DOCKER_INFLUXDB_INIT_USERNAME=admin
INFLUXDB_INIT_PASSWORD=your_password
INFLUXDB_INIT_TOKEN=your_token
DOCKER_INFLUXDB_INIT_ORG=ETCE-LAB
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