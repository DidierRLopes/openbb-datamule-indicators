# OpenBB Datamule Indicators

This is a comprehensive app for tracking and analyzing financial and economic indicators across multiple domains using SEC filing data. The system processes mentions of various topics from regulatory filings and generates standardized sector-level comparisons and metrics. Data is updated daily on [John Friedman's GitHub repository](https://github.com/john-friedman/datamule-indicators).

![CleanShot 2025-05-24 at 18 29 30@2x](https://github.com/user-attachments/assets/88d84678-c803-4e38-8d56-f42be5008583)

## Getting Started

Sign-in to the [OpenBB Workspace](https://pro.openbb.co/), and follow the following steps:

1. Go to the "Apps" tab
2. Click on "Connect backend"
3. Fill in the form with:
  Name: Datamule Indicator
  URL: https://openbb-datamule-indicators.fly.dev
5. Click on "Test". You should get a "Test successful" with the number of apps found.
6. Click on "Add".

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
