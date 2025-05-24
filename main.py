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


async def get_unique_components_from_csv(csv_url: str) -> list[dict[str, str]]:
    """Fetches a CSV from a URL and returns unique components for dropdown options."""
    try:
        response = await asyncio.to_thread(requests.get, csv_url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        # If CSV can't be fetched, return empty options or some default error option
        return [] 

    try:
        csv_content = response.text
        csvfile = io.StringIO(csv_content)
        reader = csv.DictReader(csvfile)
        
        if not reader.fieldnames or "component" not in reader.fieldnames:
            return [] # 'component' column is missing

        components = set()
        for row in reader:
            comp = row.get("component")
            if comp:
                components.add(comp)
        
        return sorted([{"value": c, "label": c.replace("_", " ").title()} for c in components], key=lambda x: x["label"])

    except csv.Error:
        return [] # Error parsing CSV
    except Exception:
        return [] # Other unexpected errors


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
        # If widget_config contains a callable for options, resolve it here
        # This part is tricky because register_widget runs at import time.
        # For dynamic options fetched via network, the widget registration itself
        # might need to be made async or options fetched on first request to /widgets.json
        # For simplicity here, assuming options are pre-fetched or static if passed directly.
        # A more robust solution for dynamic options would involve an async setup for WIDGETS population.

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
            
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        endpoint = widget_config.get("endpoint")
        if endpoint:
            if "id" not in widget_config:
                widget_config["id"] = endpoint
            
            # Dynamic options fetching at registration time (example - not fully robust for all cases)
            # This is a simplified approach. Ideally, options fetching should be handled carefully
            # to avoid blocking at startup or to allow for updates.
            # For now, let's assume if options_url is present, we try to fetch it once.
            # This will block if run at startup, which is not ideal for production.
            # A better pattern might be to store the URL and fetch options on demand when the UI requests them
            # or when /widgets.json is called, if FastAPI allows async /widgets.json.

            params = widget_config.get("params", [])
            for param_config in params:
                if param_config.get("options_url") and not param_config.get("options"):
                    # This is illustrative and has limitations (sync call in sync context)
                    # In a real scenario, this needs careful async handling or a different pattern.
                    # For now, this won't work as intended directly in a sync decorator execution path.
                    # We will pre-fetch for the new widgets we are adding as a workaround.
                    pass # Placeholder for where dynamic fetching logic would go if fully implemented at this stage

            WIDGETS[endpoint] = widget_config
        
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

# Helper function to create the generic data fetching logic for format1 indicators
def create_format1_indicator_endpoint_logic(csv_url: str):
    async def endpoint_logic(component_type: str = Query(..., alias="type", description="The component type from the CSV to filter by.")):
        """Fetches data from a remote CSV, filters by component type, and returns counts over time."""
        try:
            response = await asyncio.to_thread(requests.get, csv_url, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=503, detail=f"Could not fetch CSV data: {e}")

        try:
            csv_content = response.text
            csvfile = io.StringIO(csv_content)
            reader = csv.DictReader(csvfile)
            
            expected_headers = ["filing_date", "count", "component"]
            if not reader.fieldnames or not all(h in reader.fieldnames for h in expected_headers):
                current_headers = ", ".join(reader.fieldnames or ["None"])
                raise HTTPException(
                    status_code=500, 
                    detail=f"CSV missing headers. Expected: {expected_headers}. Found: {current_headers}."
                )

            processed_data = []
            for row in reader:
                try:
                    if row.get("component") == component_type:
                        count_str = row.get("count")
                        date_str = row.get("filing_date")
                        if count_str is not None and count_str.strip() != "" and \
                           date_str is not None and date_str.strip() != "":
                            processed_data.append({"filing_date": date_str, "count": float(count_str)})
                except (ValueError, KeyError):
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
                if component_type not in all_components and "component" in (reader.fieldnames or []):
                    sample_components = list(all_components)[:5]
                    available_msg_part = ", ".join(sample_components) + ("..." if len(all_components) > 5 else "")
                    raise HTTPException(status_code=404, detail=f"Component type '{component_type}' not found. Available: {available_msg_part}")
                else:
                    raise HTTPException(status_code=404, detail=f"No data for component '{component_type}'.")
            return processed_data
        except csv.Error as e:
            raise HTTPException(status_code=500, detail=f"Error parsing CSV: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    return endpoint_logic

# --- Chemicals Widget ---
CHEMICALS_CSV_URL = "https://raw.githubusercontent.com/john-friedman/datamule-indicators/main/indicators/format1/Resources/chemicals/overview.csv"

# Pre-fetch options for Chemicals (ideally, this would be async or on-demand)
# This is a simplified approach for the current context.
# Note: Running blocking I/O at import time like this is generally not recommended for production FastAPI apps.
# Consider initializing these in an async startup event or fetching them on first request.

# For demonstration, let's simulate what would happen if we could await:
# This part needs to be handled carefully. For now, we might need to fetch options synchronously
# OR make the /widgets.json endpoint async and resolve them there.
# Given the current structure, true async fetching for WIDGETS population at import time is problematic.

# Workaround: Fetch options synchronously for immediate use in widget registration (not ideal)
def fetch_options_sync(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        csv_content = response.text
        csvfile = io.StringIO(csv_content)
        reader = csv.DictReader(csvfile)
        if not reader.fieldnames or "component" not in reader.fieldnames:
            return []
        components = set()
        for row in reader:
            comp = row.get("component")
            if comp:
                components.add(comp)
        return sorted([{"value": c, "label": c.replace("_", " ").title()} for c in components], key=lambda x: x["label"])
    except: # Broad except for simplicity in this workaround
        return []

chemicals_options = fetch_options_sync(CHEMICALS_CSV_URL)

@register_widget({
    "name": "Chemicals Index",
    "description": "Displays an index for various chemical components.",
    "type": "table",
    "endpoint": "chemicals_widget",
    "gridData": {"w": 20, "h": 12},
    "params": [
        {
            "paramName": "type",
            "label": "Chemical Component",
            "type": "text",
            "required": True,
            "show": True,
            "value": chemicals_options[0]["value"] if chemicals_options else "",
            "description": "Select the chemical component type.",
            "options": chemicals_options
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
                    "field": "count",
                    "headerName": "Index Value",
                    "chartDataType": "series",
                }
            ]
        }
    },
})
@app.get("/chemicals_widget", summary="Chemicals Index Data")
async def chemicals_widget_endpoint(component_type: str = Query(..., alias="type", description="The chemical component type.")):
    logic = create_format1_indicator_endpoint_logic(CHEMICALS_CSV_URL)
    return await logic(component_type=component_type)

# --- DEI Widget ---
DEI_CSV_URL = "https://raw.githubusercontent.com/john-friedman/datamule-indicators/main/indicators/format1/Governance/dei/overview.csv"
dei_options = fetch_options_sync(DEI_CSV_URL)

@register_widget({
    "name": "DEI Index",
    "description": "Displays an index for various DEI (Diversity, Equity, Inclusion) components.",
    "type": "table",
    "endpoint": "dei_widget",
    "gridData": {"w": 20, "h": 12},
    "params": [
        {
            "paramName": "type",
            "label": "DEI Component",
            "type": "text",
            "required": True,
            "show": True,
            "value": dei_options[0]["value"] if dei_options else "",
            "description": "Select the DEI component type.",
            "options": dei_options
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
                    "field": "count",
                    "headerName": "Index Value",
                    "chartDataType": "series",
                }
            ]
        }
    },
})
@app.get("/dei_widget", summary="DEI Index Data")
async def dei_widget_endpoint(component_type: str = Query(..., alias="type", description="The DEI component type.")):
    logic = create_format1_indicator_endpoint_logic(DEI_CSV_URL)
    return await logic(component_type=component_type)

# --- Electronic Components Widget ---
ELECTRONIC_COMPONENTS_CSV_URL = "https://raw.githubusercontent.com/john-friedman/datamule-indicators/main/indicators/format1/Resources/electronic-components/overview.csv"
electronic_components_options = fetch_options_sync(ELECTRONIC_COMPONENTS_CSV_URL)

@register_widget({
    "name": "Electronic Components Index",
    "description": "Displays an index for various electronic components.",
    "type": "table",
    "endpoint": "electronic_components_widget",
    "gridData": {"w": 20, "h": 12},
    "params": [
        {
            "paramName": "type",
            "label": "Electronic Component",
            "type": "text",
            "required": True,
            "show": True,
            "value": electronic_components_options[0]["value"] if electronic_components_options else "",
            "description": "Select the electronic component type.",
            "options": electronic_components_options
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
                    "field": "count",
                    "headerName": "Index Value",
                    "chartDataType": "series",
                }
            ]
        }
    },
})
@app.get("/electronic_components_widget", summary="Electronic Components Index Data")
async def electronic_components_widget_endpoint(component_type: str = Query(..., alias="type", description="The electronic component type.")):
    logic = create_format1_indicator_endpoint_logic(ELECTRONIC_COMPONENTS_CSV_URL)
    return await logic(component_type=component_type)

# --- ESG Widget ---
ESG_CSV_URL = "https://raw.githubusercontent.com/john-friedman/datamule-indicators/main/indicators/format1/Governance/esg/overview.csv"
esg_options = fetch_options_sync(ESG_CSV_URL)

@register_widget({
    "name": "ESG Index",
    "description": "Displays an index for various ESG (Environmental, Social, Governance) components.",
    "type": "table",
    "endpoint": "esg_widget",
    "gridData": {"w": 20, "h": 12},
    "params": [
        {
            "paramName": "type",
            "label": "ESG Component",
            "type": "text",
            "required": True,
            "show": True,
            "value": esg_options[0]["value"] if esg_options else "",
            "description": "Select the ESG component type.",
            "options": esg_options
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
                    "field": "count",
                    "headerName": "Index Value",
                    "chartDataType": "series",
                }
            ]
        }
    },
})
@app.get("/esg_widget", summary="ESG Index Data")
async def esg_widget_endpoint(component_type: str = Query(..., alias="type", description="The ESG component type.")):
    logic = create_format1_indicator_endpoint_logic(ESG_CSV_URL)
    return await logic(component_type=component_type)

# --- Explosive Materials Widget ---
EXPLOSIVE_MATERIALS_CSV_URL = "https://raw.githubusercontent.com/john-friedman/datamule-indicators/main/indicators/format1/Resources/explosive-materials/overview.csv"
explosive_materials_options = fetch_options_sync(EXPLOSIVE_MATERIALS_CSV_URL)

@register_widget({
    "name": "Explosive Materials Index",
    "description": "Displays an index for various explosive materials components.",
    "type": "table",
    "endpoint": "explosive_materials_widget",
    "gridData": {"w": 20, "h": 12},
    "params": [
        {
            "paramName": "type",
            "label": "Explosive Material Component",
            "type": "text",
            "required": True,
            "show": True,
            "value": explosive_materials_options[0]["value"] if explosive_materials_options else "",
            "description": "Select the explosive material component type.",
            "options": explosive_materials_options
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
                    "field": "count",
                    "headerName": "Index Value",
                    "chartDataType": "series",
                }
            ]
        }
    },
})
@app.get("/explosive_materials_widget", summary="Explosive Materials Index Data")
async def explosive_materials_widget_endpoint(component_type: str = Query(..., alias="type", description="The explosive material component type.")):
    logic = create_format1_indicator_endpoint_logic(EXPLOSIVE_MATERIALS_CSV_URL)
    return await logic(component_type=component_type)

# --- Health Research Widget ---
HEALTH_RESEARCH_CSV_URL = "https://raw.githubusercontent.com/john-friedman/datamule-indicators/main/indicators/format1/Health/health-research/overview.csv"
health_research_options = fetch_options_sync(HEALTH_RESEARCH_CSV_URL)

@register_widget({
    "name": "Health Research Index",
    "description": "Displays an index for various health research components.",
    "type": "table",
    "endpoint": "health_research_widget",
    "gridData": {"w": 20, "h": 12},
    "params": [
        {
            "paramName": "type",
            "label": "Health Research Component",
            "type": "text",
            "required": True,
            "show": True,
            "value": health_research_options[0]["value"] if health_research_options else "",
            "description": "Select the health research component type.",
            "options": health_research_options
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
                    "field": "count",
                    "headerName": "Index Value",
                    "chartDataType": "series",
                }
            ]
        }
    },
})
@app.get("/health_research_widget", summary="Health Research Index Data")
async def health_research_widget_endpoint(component_type: str = Query(..., alias="type", description="The health research component type.")):
    logic = create_format1_indicator_endpoint_logic(HEALTH_RESEARCH_CSV_URL)
    return await logic(component_type=component_type)

# --- Health Widget ---
HEALTH_CSV_URL = "https://raw.githubusercontent.com/john-friedman/datamule-indicators/main/indicators/format1/Health/health/overview.csv"
health_options = fetch_options_sync(HEALTH_CSV_URL)

@register_widget({
    "name": "Health Index",
    "description": "Displays an index for various health components.",
    "type": "table",
    "endpoint": "health_widget",
    "gridData": {"w": 20, "h": 12},
    "params": [
        {
            "paramName": "type",
            "label": "Health Component",
            "type": "text",
            "required": True,
            "show": True,
            "value": health_options[0]["value"] if health_options else "",
            "description": "Select the health component type.",
            "options": health_options
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
                    "field": "count",
                    "headerName": "Index Value",
                    "chartDataType": "series",
                }
            ]
        }
    },
})
@app.get("/health_widget", summary="Health Index Data")
async def health_widget_endpoint(component_type: str = Query(..., alias="type", description="The health component type.")):
    logic = create_format1_indicator_endpoint_logic(HEALTH_CSV_URL)
    return await logic(component_type=component_type)

# --- Layoffs Widget ---
LAYOFFS_CSV_URL = "https://raw.githubusercontent.com/john-friedman/datamule-indicators/main/indicators/format1/Employment/layoffs/overview.csv"
layoffs_options = fetch_options_sync(LAYOFFS_CSV_URL)

@register_widget({
    "name": "Layoffs Index",
    "description": "Displays an index for various layoffs components.",
    "type": "table",
    "endpoint": "layoffs_widget",
    "gridData": {"w": 20, "h": 12},
    "params": [
        {
            "paramName": "type",
            "label": "Layoffs Component",
            "type": "text",
            "required": True,
            "show": True,
            "value": layoffs_options[0]["value"] if layoffs_options else "",
            "description": "Select the layoffs component type.",
            "options": layoffs_options
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
                    "field": "count",
                    "headerName": "Index Value",
                    "chartDataType": "series",
                }
            ]
        }
    },
})
@app.get("/layoffs_widget", summary="Layoffs Index Data")
async def layoffs_widget_endpoint(component_type: str = Query(..., alias="type", description="The layoffs component type.")):
    logic = create_format1_indicator_endpoint_logic(LAYOFFS_CSV_URL)
    return await logic(component_type=component_type)

# --- LLM Widget ---
LLM_CSV_URL = "https://raw.githubusercontent.com/john-friedman/datamule-indicators/main/indicators/format1/Technology/llm/overview.csv"
llm_options = fetch_options_sync(LLM_CSV_URL)

@register_widget({
    "name": "LLM Index",
    "description": "Displays an index for various LLM (Large Language Model) components.",
    "type": "table",
    "endpoint": "llm_widget",
    "gridData": {"w": 20, "h": 12},
    "params": [
        {
            "paramName": "type",
            "label": "LLM Component",
            "type": "text",
            "required": True,
            "show": True,
            "value": llm_options[0]["value"] if llm_options else "",
            "description": "Select the LLM component type.",
            "options": llm_options
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
                    "field": "count",
                    "headerName": "Index Value",
                    "chartDataType": "series",
                }
            ]
        }
    },
})
@app.get("/llm_widget", summary="LLM Index Data")
async def llm_widget_endpoint(component_type: str = Query(..., alias="type", description="The LLM component type.")):
    logic = create_format1_indicator_endpoint_logic(LLM_CSV_URL)
    return await logic(component_type=component_type)

# --- Metals Widget ---
METALS_CSV_URL = "https://raw.githubusercontent.com/john-friedman/datamule-indicators/main/indicators/format1/Resources/metals/overview.csv"
metals_options = fetch_options_sync(METALS_CSV_URL)

@register_widget({
    "name": "Metals Index",
    "description": "Displays an index for various metals components.",
    "type": "table",
    "endpoint": "metals_widget",
    "gridData": {"w": 20, "h": 12},
    "params": [
        {
            "paramName": "type",
            "label": "Metal Component",
            "type": "text",
            "required": True,
            "show": True,
            "value": metals_options[0]["value"] if metals_options else "",
            "description": "Select the metal component type.",
            "options": metals_options
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
                    "field": "count",
                    "headerName": "Index Value",
                    "chartDataType": "series",
                }
            ]
        }
    },
})
@app.get("/metals_widget", summary="Metals Index Data")
async def metals_widget_endpoint(component_type: str = Query(..., alias="type", description="The metal component type.")):
    logic = create_format1_indicator_endpoint_logic(METALS_CSV_URL)
    return await logic(component_type=component_type)

# --- Military Equipment Widget ---
MILITARY_EQUIPMENT_CSV_URL = "https://raw.githubusercontent.com/john-friedman/datamule-indicators/main/indicators/format1/War/military-equipment/overview.csv"
military_equipment_options = fetch_options_sync(MILITARY_EQUIPMENT_CSV_URL)

@register_widget({
    "name": "Military Equipment Index",
    "description": "Displays an index for various military equipment components.",
    "type": "table",
    "endpoint": "military_equipment_widget",
    "gridData": {"w": 20, "h": 12},
    "params": [
        {
            "paramName": "type",
            "label": "Military Equipment Component",
            "type": "text",
            "required": True,
            "show": True,
            "value": military_equipment_options[0]["value"] if military_equipment_options else "",
            "description": "Select the military equipment component type.",
            "options": military_equipment_options
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
                    "field": "count",
                    "headerName": "Index Value",
                    "chartDataType": "series",
                }
            ]
        }
    },
})
@app.get("/military_equipment_widget", summary="Military Equipment Index Data")
async def military_equipment_widget_endpoint(component_type: str = Query(..., alias="type", description="The military equipment component type.")):
    logic = create_format1_indicator_endpoint_logic(MILITARY_EQUIPMENT_CSV_URL)
    return await logic(component_type=component_type)

# --- Nuclear Widget ---
NUCLEAR_CSV_URL = "https://raw.githubusercontent.com/john-friedman/datamule-indicators/main/indicators/format1/Technology/nuclear/overview.csv"
nuclear_options = fetch_options_sync(NUCLEAR_CSV_URL)

@register_widget({
    "name": "Nuclear Index",
    "description": "Displays an index for various nuclear components.",
    "type": "table",
    "endpoint": "nuclear_widget",
    "gridData": {"w": 20, "h": 12},
    "params": [
        {
            "paramName": "type",
            "label": "Nuclear Component",
            "type": "text",
            "required": True,
            "show": True,
            "value": nuclear_options[0]["value"] if nuclear_options else "",
            "description": "Select the nuclear component type.",
            "options": nuclear_options
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
                    "field": "count",
                    "headerName": "Index Value",
                    "chartDataType": "series",
                }
            ]
        }
    },
})
@app.get("/nuclear_widget", summary="Nuclear Index Data")
async def nuclear_widget_endpoint(component_type: str = Query(..., alias="type", description="The nuclear component type.")):
    logic = create_format1_indicator_endpoint_logic(NUCLEAR_CSV_URL)
    return await logic(component_type=component_type)

# --- Outsourcing Widget ---
OUTSOURCING_CSV_URL = "https://raw.githubusercontent.com/john-friedman/datamule-indicators/main/indicators/format1/Market%20Dynamics/outsourcing/overview.csv"
outsourcing_options = fetch_options_sync(OUTSOURCING_CSV_URL)

@register_widget({
    "name": "Outsourcing Index",
    "description": "Displays an index for various outsourcing components.",
    "type": "table",
    "endpoint": "outsourcing_widget",
    "gridData": {"w": 20, "h": 12},
    "params": [
        {
            "paramName": "type",
            "label": "Outsourcing Component",
            "type": "text",
            "required": True,
            "show": True,
            "value": outsourcing_options[0]["value"] if outsourcing_options else "",
            "description": "Select the outsourcing component type.",
            "options": outsourcing_options
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
                    "field": "count",
                    "headerName": "Index Value",
                    "chartDataType": "series",
                }
            ]
        }
    },
})
@app.get("/outsourcing_widget", summary="Outsourcing Index Data")
async def outsourcing_widget_endpoint(component_type: str = Query(..., alias="type", description="The outsourcing component type.")):
    logic = create_format1_indicator_endpoint_logic(OUTSOURCING_CSV_URL)
    return await logic(component_type=component_type)

# --- Pandemic Widget ---
PANDEMIC_CSV_URL = "https://raw.githubusercontent.com/john-friedman/datamule-indicators/main/indicators/format1/Health/pandemic/overview.csv"
pandemic_options = fetch_options_sync(PANDEMIC_CSV_URL)

@register_widget({
    "name": "Pandemic Index",
    "description": "Displays an index for various pandemic related components.",
    "type": "table",
    "endpoint": "pandemic_widget",
    "gridData": {"w": 20, "h": 12},
    "params": [
        {
            "paramName": "type",
            "label": "Pandemic Component",
            "type": "text",
            "required": True,
            "show": True,
            "value": pandemic_options[0]["value"] if pandemic_options else "",
            "description": "Select the pandemic component type.",
            "options": pandemic_options
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
                    "field": "count",
                    "headerName": "Index Value",
                    "chartDataType": "series",
                }
            ]
        }
    },
})
@app.get("/pandemic_widget", summary="Pandemic Index Data")
async def pandemic_widget_endpoint(component_type: str = Query(..., alias="type", description="The pandemic component type.")):
    logic = create_format1_indicator_endpoint_logic(PANDEMIC_CSV_URL)
    return await logic(component_type=component_type)

# --- Political Stability Widget ---
POLITICAL_STABILITY_CSV_URL = "https://raw.githubusercontent.com/john-friedman/datamule-indicators/main/indicators/format1/International/political-stability/overview.csv"
political_stability_options = fetch_options_sync(POLITICAL_STABILITY_CSV_URL)

@register_widget({
    "name": "Political Stability Index",
    "description": "Displays an index for various political stability components.",
    "type": "table",
    "endpoint": "political_stability_widget",
    "gridData": {"w": 20, "h": 12},
    "params": [
        {
            "paramName": "type",
            "label": "Political Stability Component",
            "type": "text",
            "required": True,
            "show": True,
            "value": political_stability_options[0]["value"] if political_stability_options else "",
            "description": "Select the political stability component type.",
            "options": political_stability_options
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
                    "field": "count",
                    "headerName": "Index Value",
                    "chartDataType": "series",
                }
            ]
        }
    },
})
@app.get("/political_stability_widget", summary="Political Stability Index Data")
async def political_stability_widget_endpoint(component_type: str = Query(..., alias="type", description="The political stability component type.")):
    logic = create_format1_indicator_endpoint_logic(POLITICAL_STABILITY_CSV_URL)
    return await logic(component_type=component_type)

# --- Propellant Components Widget ---
PROPELLANT_COMPONENTS_CSV_URL = "https://raw.githubusercontent.com/john-friedman/datamule-indicators/main/indicators/format1/Resources/propellant-components/overview.csv"
propellant_components_options = fetch_options_sync(PROPELLANT_COMPONENTS_CSV_URL)

@register_widget({
    "name": "Propellant Components Index",
    "description": "Displays an index for various propellant components.",
    "type": "table",
    "endpoint": "propellant_components_widget",
    "gridData": {"w": 20, "h": 12},
    "params": [
        {
            "paramName": "type",
            "label": "Propellant Component",
            "type": "text",
            "required": True,
            "show": True,
            "value": propellant_components_options[0]["value"] if propellant_components_options else "",
            "description": "Select the propellant component type.",
            "options": propellant_components_options
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
                    "field": "count",
                    "headerName": "Index Value",
                    "chartDataType": "series",
                }
            ]
        }
    },
})
@app.get("/propellant_components_widget", summary="Propellant Components Index Data")
async def propellant_components_widget_endpoint(component_type: str = Query(..., alias="type", description="The propellant component type.")):
    logic = create_format1_indicator_endpoint_logic(PROPELLANT_COMPONENTS_CSV_URL)
    return await logic(component_type=component_type)

# --- Raw Materials Widget ---
RAW_MATERIALS_CSV_URL = "https://raw.githubusercontent.com/john-friedman/datamule-indicators/main/indicators/format1/Resources/raw-materials/overview.csv"
raw_materials_options = fetch_options_sync(RAW_MATERIALS_CSV_URL)

@register_widget({
    "name": "Raw Materials Index",
    "description": "Displays an index for various raw materials components.",
    "type": "table",
    "endpoint": "raw_materials_widget",
    "gridData": {"w": 20, "h": 12},
    "params": [
        {
            "paramName": "type",
            "label": "Raw Material Component",
            "type": "text",
            "required": True,
            "show": True,
            "value": raw_materials_options[0]["value"] if raw_materials_options else "",
            "description": "Select the raw material component type.",
            "options": raw_materials_options
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
                    "field": "count",
                    "headerName": "Index Value",
                    "chartDataType": "series",
                }
            ]
        }
    },
})
@app.get("/raw_materials_widget", summary="Raw Materials Index Data")
async def raw_materials_widget_endpoint(component_type: str = Query(..., alias="type", description="The raw material component type.")):
    logic = create_format1_indicator_endpoint_logic(RAW_MATERIALS_CSV_URL)
    return await logic(component_type=component_type)

# --- Semiconductor Materials Widget ---
SEMICONDUCTOR_MATERIALS_CSV_URL = "https://raw.githubusercontent.com/john-friedman/datamule-indicators/main/indicators/format1/Resources/semiconductor-materials/overview.csv"
semiconductor_materials_options = fetch_options_sync(SEMICONDUCTOR_MATERIALS_CSV_URL)

@register_widget({
    "name": "Semiconductor Materials Index",
    "description": "Displays an index for various semiconductor materials components.",
    "type": "table",
    "endpoint": "semiconductor_materials_widget",
    "gridData": {"w": 20, "h": 12},
    "params": [
        {
            "paramName": "type",
            "label": "Semiconductor Material Component",
            "type": "text",
            "required": True,
            "show": True,
            "value": semiconductor_materials_options[0]["value"] if semiconductor_materials_options else "",
            "description": "Select the semiconductor material component type.",
            "options": semiconductor_materials_options
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
                    "field": "count",
                    "headerName": "Index Value",
                    "chartDataType": "series",
                }
            ]
        }
    },
})
@app.get("/semiconductor_materials_widget", summary="Semiconductor Materials Index Data")
async def semiconductor_materials_widget_endpoint(component_type: str = Query(..., alias="type", description="The semiconductor material component type.")):
    logic = create_format1_indicator_endpoint_logic(SEMICONDUCTOR_MATERIALS_CSV_URL)
    return await logic(component_type=component_type)

# --- Sovereign Crisis Widget ---
SOVEREIGN_CRISIS_CSV_URL = "https://raw.githubusercontent.com/john-friedman/datamule-indicators/main/indicators/format1/International/sovereign-crisis/overview.csv"
sovereign_crisis_options = fetch_options_sync(SOVEREIGN_CRISIS_CSV_URL)

@register_widget({
    "name": "Sovereign Crisis Index",
    "description": "Displays an index for various sovereign crisis components.",
    "type": "table",
    "endpoint": "sovereign_crisis_widget",
    "gridData": {"w": 20, "h": 12},
    "params": [
        {
            "paramName": "type",
            "label": "Sovereign Crisis Component",
            "type": "text",
            "required": True,
            "show": True,
            "value": sovereign_crisis_options[0]["value"] if sovereign_crisis_options else "",
            "description": "Select the sovereign crisis component type.",
            "options": sovereign_crisis_options
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
                    "field": "count",
                    "headerName": "Index Value",
                    "chartDataType": "series",
                }
            ]
        }
    },
})
@app.get("/sovereign_crisis_widget", summary="Sovereign Crisis Index Data")
async def sovereign_crisis_widget_endpoint(component_type: str = Query(..., alias="type", description="The sovereign crisis component type.")):
    logic = create_format1_indicator_endpoint_logic(SOVEREIGN_CRISIS_CSV_URL)
    return await logic(component_type=component_type)

# --- Space Widget ---
SPACE_CSV_URL = "https://raw.githubusercontent.com/john-friedman/datamule-indicators/main/indicators/format1/Technology/space/overview.csv"
space_options = fetch_options_sync(SPACE_CSV_URL)

@register_widget({
    "name": "Space Index",
    "description": "Displays an index for various space exploration components.",
    "type": "table",
    "endpoint": "space_widget",
    "gridData": {"w": 20, "h": 12},
    "params": [
        {
            "paramName": "type",
            "label": "Space Component",
            "type": "text",
            "required": True,
            "show": True,
            "value": space_options[0]["value"] if space_options else "",
            "description": "Select the space component type.",
            "options": space_options
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
                    "field": "count",
                    "headerName": "Index Value",
                    "chartDataType": "series",
                }
            ]
        }
    },
})
@app.get("/space_widget", summary="Space Index Data")
async def space_widget_endpoint(component_type: str = Query(..., alias="type", description="The space component type.")):
    logic = create_format1_indicator_endpoint_logic(SPACE_CSV_URL)
    return await logic(component_type=component_type)

# --- Supplier Concentration Widget ---
SUPPLIER_CONCENTRATION_CSV_URL = "https://raw.githubusercontent.com/john-friedman/datamule-indicators/main/indicators/format1/Market%20Dynamics/supplier-concentration/overview.csv"
supplier_concentration_options = fetch_options_sync(SUPPLIER_CONCENTRATION_CSV_URL)

@register_widget({
    "name": "Supplier Concentration Index",
    "description": "Displays an index for various supplier concentration components.",
    "type": "table",
    "endpoint": "supplier_concentration_widget",
    "gridData": {"w": 20, "h": 12},
    "params": [
        {
            "paramName": "type",
            "label": "Supplier Concentration Component",
            "type": "text",
            "required": True,
            "show": True,
            "value": supplier_concentration_options[0]["value"] if supplier_concentration_options else "",
            "description": "Select the supplier concentration component type.",
            "options": supplier_concentration_options
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
                    "field": "count",
                    "headerName": "Index Value",
                    "chartDataType": "series",
                }
            ]
        }
    },
})
@app.get("/supplier_concentration_widget", summary="Supplier Concentration Index Data")
async def supplier_concentration_widget_endpoint(component_type: str = Query(..., alias="type", description="The supplier concentration component type.")):
    logic = create_format1_indicator_endpoint_logic(SUPPLIER_CONCENTRATION_CSV_URL)
    return await logic(component_type=component_type)

# --- Supply Chain Widget ---
SUPPLY_CHAIN_CSV_URL = "https://raw.githubusercontent.com/john-friedman/datamule-indicators/main/indicators/format1/Trade/supply-chain/overview.csv"
supply_chain_options = fetch_options_sync(SUPPLY_CHAIN_CSV_URL)

@register_widget({
    "name": "Supply Chain Index",
    "description": "Displays an index for various supply chain components.",
    "type": "table",
    "endpoint": "supply_chain_widget",
    "gridData": {"w": 20, "h": 12},
    "params": [
        {
            "paramName": "type",
            "label": "Supply Chain Component",
            "type": "text",
            "required": True,
            "show": True,
            "value": supply_chain_options[0]["value"] if supply_chain_options else "",
            "description": "Select the supply chain component type.",
            "options": supply_chain_options
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
                    "field": "count",
                    "headerName": "Index Value",
                    "chartDataType": "series",
                }
            ]
        }
    },
})
@app.get("/supply_chain_widget", summary="Supply Chain Index Data")
async def supply_chain_widget_endpoint(component_type: str = Query(..., alias="type", description="The supply chain component type.")):
    logic = create_format1_indicator_endpoint_logic(SUPPLY_CHAIN_CSV_URL)
    return await logic(component_type=component_type)

# --- Tariffs Widget ---
TARIFFS_CSV_URL = "https://raw.githubusercontent.com/john-friedman/datamule-indicators/main/indicators/format1/Trade/tariffs/overview.csv"
tariffs_options = fetch_options_sync(TARIFFS_CSV_URL)

@register_widget({
    "name": "Tariffs Index",
    "description": "Displays an index for various tariffs components.",
    "type": "table",
    "endpoint": "tariffs_widget",
    "gridData": {"w": 20, "h": 12},
    "params": [
        {
            "paramName": "type",
            "label": "Tariffs Component",
            "type": "text",
            "required": True,
            "show": True,
            "value": tariffs_options[0]["value"] if tariffs_options else "",
            "description": "Select the tariffs component type.",
            "options": tariffs_options
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
                    "field": "count",
                    "headerName": "Index Value",
                    "chartDataType": "series",
                }
            ]
        }
    },
})
@app.get("/tariffs_widget", summary="Tariffs Index Data")
async def tariffs_widget_endpoint(component_type: str = Query(..., alias="type", description="The tariffs component type.")):
    logic = create_format1_indicator_endpoint_logic(TARIFFS_CSV_URL)
    return await logic(component_type=component_type)

# --- Terrorism Widget ---
TERRORISM_CSV_URL = "https://raw.githubusercontent.com/john-friedman/datamule-indicators/main/indicators/format1/Terrorism/terrorism/overview.csv"
terrorism_options = fetch_options_sync(TERRORISM_CSV_URL)

@register_widget({
    "name": "Terrorism Index",
    "description": "Displays an index for various terrorism related components.",
    "type": "table",
    "endpoint": "terrorism_widget",
    "gridData": {"w": 20, "h": 12},
    "params": [
        {
            "paramName": "type",
            "label": "Terrorism Component",
            "type": "text",
            "required": True,
            "show": True,
            "value": terrorism_options[0]["value"] if terrorism_options else "",
            "description": "Select the terrorism component type.",
            "options": terrorism_options
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
                    "field": "count",
                    "headerName": "Index Value",
                    "chartDataType": "series",
                }
            ]
        }
    },
})
@app.get("/terrorism_widget", summary="Terrorism Index Data")
async def terrorism_widget_endpoint(component_type: str = Query(..., alias="type", description="The terrorism component type.")):
    logic = create_format1_indicator_endpoint_logic(TERRORISM_CSV_URL)
    return await logic(component_type=component_type)

# --- War Widget ---
WAR_CSV_URL = "https://raw.githubusercontent.com/john-friedman/datamule-indicators/main/indicators/format1/War/war/overview.csv"
war_options = fetch_options_sync(WAR_CSV_URL)

@register_widget({
    "name": "War Index",
    "description": "Displays an index for various war related components.",
    "type": "table",
    "endpoint": "war_widget",
    "gridData": {"w": 20, "h": 12},
    "params": [
        {
            "paramName": "type",
            "label": "War Component",
            "type": "text",
            "required": True,
            "show": True,
            "value": war_options[0]["value"] if war_options else "",
            "description": "Select the war component type.",
            "options": war_options
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
                    "field": "count",
                    "headerName": "Index Value",
                    "chartDataType": "series",
                }
            ]
        }
    },
})
@app.get("/war_widget", summary="War Index Data")
async def war_widget_endpoint(component_type: str = Query(..., alias="type", description="The war component type.")):
    logic = create_format1_indicator_endpoint_logic(WAR_CSV_URL)
    return await logic(component_type=component_type)
