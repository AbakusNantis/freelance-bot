# function_app.py
import json
import logging

import azure.functions as func
from azure.functions import FunctionApp, AuthLevel
from ScrapeNewEntries import ScrapeNewEntries

app = func.FunctionApp()

@app.route(route="scrapenewentries", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
#@app.route(auth_level=func.AuthLevel.ANONYMOUS)


def scrapeNewEntries(req: func.HttpRequest) -> func.HttpResponse:
#def ScrapeNewEntries() -> func.HttpResponse:
    try:
        urls = ScrapeNewEntries().scrape()
        return func.HttpResponse(
            json.dumps(urls),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        logging.exception("Scrape fehlgeschlagen")
        return func.HttpResponse(f"Error: {e}", status_code=500)