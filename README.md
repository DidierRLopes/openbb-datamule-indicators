# OpenBB Datamule Indicators

A FastAPI backend application that provides various economic and market indicators through API endpoints. This service is designed to work with OpenBB Workspace.

This was built based on [https://github.com/john-friedman/datamule-indicators](https://github.com/john-friedman/datamule-indicators).

## Features

The application provides a comprehensive set of economic and market indicators organized into the following categories:

- Governance
  - DEI (Diversity, Equity, Inclusion) Index
  - ESG (Environmental, Social, Governance) Index

- Trade
  - Tariffs Index
  - Supply Chain Index

- Employment
  - Layoffs Index

- Market Dynamics
  - Outsourcing Index
  - Supplier Concentration Index

- Consumer Sentiment
  - Consumer Confidence Index

- Technology
  - Space Index
  - Nuclear Index

- International
  - Political Stability Index

- Corporate Finance
  - IPO Index

- Health
  - Health Research Index
  - Health Index
  - Pandemic Index

- Resources
  - Explosive Materials Index
  - Metals Index
  - Semiconductor Materials Index
  - Propellant Components Index
  - Raw Materials Index
  - Electronic Components Index
  - Chemicals Index

- Military & Security
  - Military Equipment Index
  - Terrorism Index
  - War Index

## Prerequisites

- Python 3.8 or higher
- Poetry (Python package manager)

## Installation

1. Clone the repository:

```bash
git clone https://github.com/DidierRLopes/openbb-datamule-indicators.git
cd openbb-datamule-indicators
```

2. Install dependencies using Poetry:

```bash
poetry install
```

## Running the Application

1. Activate the virtual environment:

```bash
poetry shell
```

2. Start the FastAPI server:

```bash
uvicorn main:app --reload
```

The server will start at `http://localhost:8000`

## API Documentation

Once the server is running, you can access:

- Interactive API documentation (Swagger UI): `http://localhost:8000/docs`
- Alternative API documentation (ReDoc): `http://localhost:8000/redoc`

## Available Endpoints

- `/` - Root endpoint with basic API information
- `/widgets.json` - Returns configuration of all registered widgets
- `/apps.json` - Returns available applications
- Various indicator endpoints (e.g., `/ipo_index_widget`, `/consumer_confidence_widget`, etc.)

## Development

The application uses FastAPI and includes CORS middleware configured for OpenBB Workspace. The main application file is `main.py`, which contains all the endpoint definitions and widget configurations.
