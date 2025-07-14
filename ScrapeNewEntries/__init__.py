## Azure Function: Scraper (Timer Trigger)
# File: Scraper/__init__.py
import os
import logging
import azure.functions as func
import requests
from azure.data.tables import TableServiceClient, UpdateMode
from datetime import datetime

# Load configuration from environment variables
COSMOS_CONN_STR = os.getenv("COSMOS_TABLE_CONNECTION_STRING")
TABLE_NAME = os.getenv("COSMOS_TABLE_NAME", "ScrapeResults")
SCRAPE_URL = os.getenv("SCRAPE_TARGET_URL")  # e.g. https://example.com/api/listings
MAX_RESULTS = int(os.getenv("SCRAPE_MAX_RESULTS", "100"))

# Initialize Table client once (best practice)
_table_service = TableServiceClient.from_connection_string(conn_str=COSMOS_CONN_STR)
_table_client = _table_service.get_table_client(table_name=TABLE_NAME)

# Ensure table exists
try:
    _table_client.create_table()
except Exception as e:
    logging.debug(f"Table '{TABLE_NAME}' may already exist: {e}")


def main(mytimer: func.TimerRequest) -> None:
    logging.info(f"Scraper function triggered at {datetime.utcnow().isoformat()}Z")
    try:
        response = requests.get(SCRAPE_URL, timeout=10)
        response.raise_for_status()
        data = response.json()  # or parse HTML if needed
    except requests.RequestException as err:
        logging.error(f"Error fetching URL {SCRAPE_URL}: {err}")
        return

    # Extract listings (assuming JSON array)
    listings = data.get("listings", [])[:MAX_RESULTS]
    timestamp = datetime.utcnow().isoformat()

    for item in listings:
        # Derive unique RowKey, e.g. hash of URL or ID field
        url = item.get("url")
        listing_id = item.get("id") or url
        partition_key = timestamp.split("T")[0]  # date partition
        row_key = listing_id.replace("/", "_")

        entity = {
            "PartitionKey": partition_key,
            "RowKey": row_key,
            "Url": url,
            "ScrapedAt": timestamp
        }

        try:
            # Upsert entity
            _table_client.upsert_entity(mode=UpdateMode.MERGE, entity=entity)
            logging.debug(f"Upserted listing {row_key}")
        except Exception as e:
            logging.error(f"Failed to upsert {row_key}: {e}")

    logging.info(f"Scraper completed: processed {len(listings)} listings")

# File: Scraper/function.json
# {
#   "scriptFile": "__init__.py",
#   "bindings": [
#     {
#       "name": "mytimer",
#       "type": "timerTrigger",
#       "direction": "in",
#       "schedule": "0 */5 * * * *",  # every 5 minutes
#       "runOnStartup": false
#     }
#   ]
# }

# Requirements (requirements.txt):
# azure-functions
# azure-data-tables
# requests
