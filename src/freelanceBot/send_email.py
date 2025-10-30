import os, requests, msal
import yaml 
from pathlib import Path
from jinja2 import Environment, StrictUndefined
import pandas as pd
from time import sleep
from dotenv import load_dotenv
load_dotenv()

######## CONFIG ########

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET_VALUE")
SENDER = "bastian.knaus@enari.com"          # Das M365-Postfach, von dem gesendet wird

AGENCIES_ENRICHED_PATH = r"agencies_enriched.xlsx"

######## MAIL_TEMPLATE ########

MAIL_TEMPLATE_PATH = r"src\freelanceBot\mail_template.yml"
with Path(MAIL_TEMPLATE_PATH).open("r", encoding = "utf-8") as f:
    template_src = yaml.safe_load(f)["mail_template_html"]
    env = Environment(
        undefined=StrictUndefined,
        autoescape=False,          # Plain-Text
        trim_blocks=True,          # hübschere Blocksteuerung
        lstrip_blocks=True,        # führende Whitespaces vor Blöcken entfernen
        keep_trailing_newline=True # letzte Zeile behalten
    )
    MAIL_TEMPLATE = env.from_string(template_src)

authority = f"https://login.microsoftonline.com/{TENANT_ID}"
scopes = ["https://graph.microsoft.com/.default"]


######## FUNCTIONALITY ########

def get_token():
    app = msal.ConfidentialClientApplication(
        client_id=CLIENT_ID,
        client_credential=CLIENT_SECRET,
        authority=authority,
    )

    token = app.acquire_token_for_client(scopes=scopes)
    if "access_token" not in token:
        raise SystemExit(token)

    access_token = token["access_token"]

    return access_token

def send_mail(subject: str, content: str, email: str, access_token: str):
    """
    Send one mail
    """
    url = f"https://graph.microsoft.com/v1.0/users/{SENDER}/sendMail"
    payload = {
        "message": {
            "subject": subject,
            "body": {"contentType": "HTML", "content": content},
            "toRecipients": [{"emailAddress": {"address": email}}],
            # Optional: CC/BCC/Attachments etc.
        },
        "saveToSentItems": True,
    }
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        print("Status:", resp.status_code)
        try:
            print("Response JSON:", resp.json())
        except Exception:
            print("Response text:", resp.text)
        raise

def generate_content(name: str, gender: str):
    # Load modular Prompt (outside of function)
    # Ansprache
    if gender == "male": 
        ansprache = "Lieber Herr "
    elif gender == "female":
        ansprache = "Liebe Frau "
    else:
        ansprache = "Sehr geehrte Damen und Herren "
        name = ""


    arguments = {
        "ansprache": ansprache,
        "name": name, 
    }
    full_text = MAIL_TEMPLATE.render(arguments)
    return full_text

def main():
    subject = "Anfrage zu Beauftragungen"
    access_token = get_token()

    df = pd.read_excel(AGENCIES_ENRICHED_PATH)
    for email, lastname, gender in df[["email", "last_name", "gender"]].itertuples(index=False, name = None): 
        content = generate_content(lastname, gender)    
        send_mail(subject, content, email, access_token)
        sleep(2.5)
        print(f"Sent Mail to {email}.")
    

if __name__=="__main__":
    main()