# function_app.py

import azure.functions as func

from scrapeNewEntries import bp as bp_scrapeNewEntries

app = func.FunctionApp()

app.register_functions(bp_scrapeNewEntries)