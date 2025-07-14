# function_app.py
import json
import logging
import azure.functions as func
from azure.functions import FunctionApp, AuthLevel
from ScrapeNewEntries import ScrapeNewEntries

app = func.FunctionApp()

@app.route(route="hello", auth_level=func.AuthLevel.ANONYMOUS)

def scrape(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(
        ScrapeNewEntries().scrape()[0],
        status_code=200
    )


    """name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')

    if name:
        return func.HttpResponse(f"Hello, {name}. This HTTP triggered function executed successfully.")
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )"""