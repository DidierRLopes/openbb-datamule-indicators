# Import required libraries
import json
import requests
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
from functools import wraps
import csv
import io

# Initialize FastAPI application with metadata
app = FastAPI(
    title="Simple Backend",
    description="Simple backend app for OpenBB Workspace",
    version="0.0.1"
)

# Define allowed origins for CORS (Cross-Origin Resource Sharing)
# This restricts which domains can access the API
origins = [
    "https://pro.openbb.co",
]

# Configure CORS middleware to handle cross-origin requests
# This allows the specified origins to make requests to the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

ROOT_PATH = Path(__file__).parent.resolve()

WIDGETS = {}


def register_widget(widget_config):
    """
    Decorator that registers a widget configuration in the WIDGETS dictionary.
    
    Args:
        widget_config (dict): The widget configuration to add to the WIDGETS 
            dictionary. This should follow the same structure as other entries 
            in WIDGETS.
    
    Returns:
        function: The decorated function.
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Call the original function
            return await func(*args, **kwargs)
            
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Call the original function
            return func(*args, **kwargs)
        
        # Extract the endpoint from the widget_config
        endpoint = widget_config.get("endpoint")
        if endpoint:
            # Add an id field to the widget_config if not already present
            if "id" not in widget_config:
                widget_config["id"] = endpoint
            
            WIDGETS[endpoint] = widget_config
        
        # Return the appropriate wrapper based on whether the function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator

@app.get("/")
def read_root():
    """Root endpoint that returns basic information about the API"""
    return {"Info": "Hello World"}


# Endpoint that returns the registered widgets configuration
# The WIDGETS dictionary is maintained by the registry.py helper
# which automatically registers widgets when using the
# @register_widget decorator
@app.get("/widgets.json")
def get_widgets():
    """Returns the configuration of all registered widgets
    
    The widgets are automatically registered through the
    @register_widget decorator
    and stored in the WIDGETS dictionary from registry.py
    
    Returns:
        dict: The configuration of all registered widgets
    """
    return WIDGETS


# Apps configuration file for the OpenBB Workspace
# it contains the information and configuration about all the
# apps that will be displayed in the OpenBB Workspace
@app.get("/apps.json")
def get_apps():
    """Apps configuration file for the OpenBB Workspace
    
    Returns:
        JSONResponse: The contents of apps.json file
    """
    # Read and return the apps configuration file
    return JSONResponse(
        content=json.load(
            (Path(__file__).parent.resolve() / "apps.json").open()
        )
    )

# Table to Chart Widget
# The most important part of this widget is that the default view is a
# chart that comes from the "chartView" key in the data object
# chartDataType: Specifies how data is treated in a chart.
#                Example: "category"
#                Possible values: "category", "series", "time", "excluded"
@register_widget({
    "name": "Table to Chart Widget",
    "description": "A table widget",
    "type": "table",
    "endpoint": "table_to_chart_widget",
    "gridData": {"w": 20, "h": 12},
    "data": {
        "table": {
            "enableCharts": True,
            "showAll": False,
            "chartView": {
                "enabled": True,
                "chartType": "column"
            },
            "columnsDefs": [
                {
                    "field": "name",
                    "headerName": "Asset",
                    "chartDataType": "category",
                },
                {
                    "field": "tvl",
                    "headerName": "TVL (USD)",
                    "chartDataType": "series",
                },
            ]
        }
    },
})
@app.get("/table_to_chart_widget")
def table_to_chart_widget():
    """Returns a mock table data for demonstration"""
    mock_data = [
        {
            "name": "Ethereum",
            "tvl": 45000000000,
            "change_1d": 2.5,
            "change_7d": 5.2
        },
        {
            "name": "Bitcoin",
            "tvl": 35000000000,
            "change_1d": 1.2,
            "change_7d": 4.8
        },
        {
            "name": "Solana",
            "tvl": 8000000000,
            "change_1d": -0.5,
            "change_7d": 2.1
        }
    ]
    return mock_data


# Table to time series Widget
# In here we will see how to use a table widget to display a time series chart
@register_widget({
    "name": "Table to Time Series Widget",
    "description": "A table widget",
    "type": "table",
    "endpoint": "table_to_time_series_widget",
    "gridData": {"w": 20, "h": 12},
    "data": {
        "table": {
            "enableCharts": True,
            "showAll": False,
            "chartView": {
                "enabled": True,
                "chartType": "line"
            },
            "columnsDefs": [
                {
                    "field": "date",
                    "headerName": "Date",
                    "chartDataType": "time",
                },
                {
                    "field": "Ethereum",
                    "headerName": "Ethereum",
                    "chartDataType": "series",
                },
                {
                    "field": "Bitcoin",
                    "headerName": "Bitcoin",
                    "chartDataType": "series",
                },
                {
                    "field": "Solana",
                    "headerName": "Solana",
                    "chartDataType": "series",
                }
            ]
        }
    },
})
@app.get("/table_to_time_series_widget")
def table_to_time_series_widget():
    """Returns a mock table data for demonstration"""
    mock_data = [
        {
            "date": "2024-06-06",
            "Ethereum": 1.0000,
            "Bitcoin": 1.0000,
            "Solana": 1.0000
        },
        {
            "date": "2024-06-07",
            "Ethereum": 1.0235,
            "Bitcoin": 0.9822,
            "Solana": 1.0148
        },
        {
            "date": "2024-06-08",
            "Ethereum": 0.9945,
            "Bitcoin": 1.0072,
            "Solana": 0.9764
        },
        {
            "date": "2024-06-09",
            "Ethereum": 1.0205,
            "Bitcoin": 0.9856,
            "Solana": 1.0300
        },
        {
            "date": "2024-06-10",
            "Ethereum": 0.9847,
            "Bitcoin": 1.0195,
            "Solana": 0.9897
        }
    ]
    return mock_data

# IPO Index Widget
# Displays an IPO index over time from a remote CSV file.
# The specific index/column to display is chosen by the 'type' query parameter.
@register_widget({
    "name": "IPO Index",
    "description": "A time series chart displaying an IPO index from a remote CSV.",
    "type": "table",
    "endpoint": "ipo_index_widget",
    "gridData": {"w": 20, "h": 12},
    "params": [  # Documenting the parameter for users of the widget
        {
            "paramName": "type",
            "label": "IPO Component Type",
            "type": "text",
            "required": True,
            "show": True,
            "value": "domestic_us",  # Default to a known valid component
            "description": "Select the IPO component type to display the count for.",
            "options": [
                {
                    "value": "domestic_us",
                    "label": "Domestic US"
                },
                {
                    "value": "international_us",
                    "label": "International US"
                },
                {
                    "value": "domestic_cn",
                    "label": "Domestic CN"
                },
                {
                    "value": "international_cn",
                    "label": "International CN"
                },
                {
                    "value": "domestic_eu",
                    "label": "Domestic EU"
                },
                {
                    "value": "international_eu",
                    "label": "International EU"
                }
                # Add other actual distinct values from the 'component' column if more exist
            ]
        }
    ],
    "data": {
        "table": {
            "enableCharts": True,
            "showAll": False,
            "chartView": {
                "enabled": True,
                "chartType": "line"
            },
            "columnsDefs": [
                {
                    "field": "filing_date",
                    "headerName": "Date",
                    "chartDataType": "time",
                },
                {
                    "field": "count",  # Now plotting the 'count' column
                    "headerName": "Count", # Header reflects we are plotting 'count'
                    "chartDataType": "series",
                }
            ]
        }
    },
})
@app.get("/ipo_index_widget")
def ipo_index_widget(
    ipo_type: str = Query(
        ...,
        alias="type",
        description="The component type from the CSV to filter by (e.g., domestic_us)."
    )
):
    """Fetches IPO data from a remote CSV, filters by component type,
    and returns counts over time.
    
    The 'type' query parameter specifies which value in the 'component' column
    to filter for. The 'count' column for these rows will be plotted against 'filing_date'.
    """
    csv_url = (
        "https://raw.githubusercontent.com/john-friedman/datamule-indicators/"
        "main/indicators/format1/Corporate%20Finance/ipo/overview.csv"
    )
    
    try:
        response = requests.get(csv_url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=503, detail=f"Could not fetch IPO data CSV: {e}"
        )

    try:
        csv_content = response.text
        csvfile = io.StringIO(csv_content)
        reader = csv.DictReader(csvfile)
        
        # Headers are known: filing_date, count, component
        if not reader.fieldnames or not all(h in reader.fieldnames for h in ["filing_date", "count", "component"]):
            raise HTTPException(
                status_code=500, 
                detail="CSV file is missing expected headers: filing_date, count, component."
            )

        processed_data = []
        for row in reader:
            try:
                if row.get("component") == ipo_type:
                    count_str = row.get("count")
                    filing_date_str = row.get("filing_date")

                    if count_str is None or count_str.strip() == "" or \
                       filing_date_str is None or filing_date_str.strip() == "":
                        continue # Skip if essential data is missing
                    
                    count = float(count_str)
                    processed_data.append({"filing_date": filing_date_str, "count": count})
            except ValueError:
                continue # Skip rows where count is not a valid number
            except KeyError:
                continue # Skip rows if essential keys are missing (should be caught by header check)
        
        if not processed_data:
            # Check if the ipo_type even existed in the component column
            all_components = set()
            csvfile.seek(0) # Reset reader to the beginning of the stream
            # Create a new reader instance as the old one might be exhausted or at EOF
            # Alternatively, store rows in a list first if memory allows and file is not excessively large
            temp_reader = csv.DictReader(csvfile)
            next(temp_reader) # Skip header row again for this temporary reader
            for r_dict in temp_reader:
                comp = r_dict.get("component")
                if comp is not None:
                    all_components.add(comp)
            
            if ipo_type not in all_components:
                # Show a sample of available components in the error message
                sample_components = list(all_components)[:5] # Get up to 5 samples
                available_msg_part = ", ".join(sample_components)
                if len(all_components) > 5:
                    available_msg_part += "..."
                raise HTTPException(
                    status_code=404, 
                    detail=f"Component type '{ipo_type}' not found. Available types: {available_msg_part}"
                )
            else:
                 raise HTTPException(
                    status_code=404, 
                    detail=f"No data found for component type '{ipo_type}' with valid counts and filing dates."
                )
            
        return processed_data

    except csv.Error as e:
        raise HTTPException(
            status_code=500, detail=f"Error parsing CSV data: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Unexpected error processing IPO data: {str(e)}"
        )

# Consumer Confidence Widget
@register_widget({
    "name": "Consumer Confidence",
    "description": "A time series chart displaying Consumer Confidence data from a remote CSV.",
    "type": "table",
    "endpoint": "consumer_confidence_widget",
    "gridData": {"w": 20, "h": 12},
    "params": [
        {
            "paramName": "type",
            "label": "Confidence Component Type",
            "type": "text",
            "required": True,
            "show": True,
            "value": "domestic",  # Default to an actual component value
            "description": "Select the Consumer Confidence component type.",
            "options": [
                {
                    "value": "domestic",
                    "label": "Domestic"
                },
                {
                    "value": "international",
                    "label": "International"
                }
                # Add other actual distinct values if more exist in this specific CSV
            ]
        }
    ],
    "data": {
        "table": {
            "enableCharts": True,
            "showAll": False,
            "chartView": {
                "enabled": True,
                "chartType": "line"
            },
            "columnsDefs": [
                {
                    "field": "filing_date",
                    "headerName": "Date",
                    "chartDataType": "time",
                },
                {
                    "field": "count",      # Assuming 'count' holds the confidence value
                    "headerName": "Level",    # Or "Index" or "Value"
                    "chartDataType": "series",
                }
            ]
        }
    },
})
@app.get("/consumer_confidence_widget")
def consumer_confidence_widget(
    confidence_type: str = Query(
        ...,
        alias="type",
        description="The component type from the Consumer Confidence CSV to filter by."
    )
):
    """Fetches Consumer Confidence data, filters by component type,
    and returns counts/levels over time.
    
    The 'type' query parameter specifies which value in the 'component' column
    to filter for. The 'count' column for these rows will be plotted against 'filing_date'.
    Assumes CSV has columns: filing_date, count, component.
    """
    csv_url = (
        "https://raw.githubusercontent.com/john-friedman/datamule-indicators/main/"
        "indicators/format1/Consumer%20Sentiment/consumer-confidence/overview.csv"
    )
    
    try:
        response = requests.get(csv_url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=503, detail=f"Could not fetch Consumer Confidence CSV: {e}"
        )

    try:
        csv_content = response.text
        csvfile = io.StringIO(csv_content)
        reader = csv.DictReader(csvfile)
        
        expected_headers = ["filing_date", "count", "component"]
        if not reader.fieldnames or not all(h in reader.fieldnames for h in expected_headers):
            missing_headers = [h for h in expected_headers if h not in (reader.fieldnames or [])]
            current_headers = ", ".join(reader.fieldnames or ["None"]) 
            raise HTTPException(
                status_code=500, 
                detail=f"Consumer Confidence CSV missing headers. Expected: {expected_headers}. Found: {current_headers}. Missing: {missing_headers}"
            )

        processed_data = []
        for row in reader:
            try:
                if row.get("component") == confidence_type:
                    value_str = row.get("count") # Assuming 'count' is the value column
                    date_str = row.get("filing_date")

                    if value_str is None or value_str.strip() == "" or \
                       date_str is None or date_str.strip() == "":
                        continue
                    
                    value = float(value_str)
                    processed_data.append({"filing_date": date_str, "count": value})
            except ValueError:
                continue 
            except KeyError:
                continue 
        
        if not processed_data:
            all_components = set()
            csvfile.seek(0)
            temp_reader = csv.DictReader(csvfile)
            if temp_reader.fieldnames and "component" in temp_reader.fieldnames:
                next(temp_reader) 
                for r_dict in temp_reader:
                    comp = r_dict.get("component")
                    if comp is not None:
                        all_components.add(comp)
            
            if confidence_type not in all_components and "component" in (reader.fieldnames or []):
                sample_components = list(all_components)[:5]
                available_msg_part = ", ".join(sample_components)
                if len(all_components) > 5:
                    available_msg_part += "..."
                raise HTTPException(
                    status_code=404, 
                    detail=f"Component type '{confidence_type}' not found in Consumer Confidence CSV. Available: {available_msg_part}"
                )
            else:
                 raise HTTPException(
                    status_code=404, 
                    detail=f"No data for component '{confidence_type}' with valid values and dates in Consumer Confidence CSV."
                )
            
        return processed_data

    except csv.Error as e:
        raise HTTPException(
            status_code=500, detail=f"Error parsing Consumer Confidence CSV: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Unexpected error processing Consumer Confidence data: {str(e)}"
        )

# Simple table widget from an API endpoint
# This is a simple widget that demonstrates how to use a table widget
# from an API endpoint
# Note that the endpoint is the endpoint of the API that will be used to
# fetch the data
# and the data is returned in the JSON format
@register_widget({
    "name": "Table Widget from API Endpoint",
    "description": "A table widget from an API endpoint",
    "type": "table",
    "endpoint": "table_widget_from_api_endpoint",
    "gridData": {"w": 12, "h": 4},
})
@app.get("/table_widget_from_api_endpoint")
def table_widget_from_api_endpoint():
    """Get current TVL of all chains using Defi LLama"""
    response = requests.get("https://api.llama.fi/v2/chains")

    if response.status_code == 200:
        return response.json()

    print(f"Request error {response.status_code}: {response.text}")
    raise HTTPException(
        status_code=response.status_code,
        detail=response.text
    )
