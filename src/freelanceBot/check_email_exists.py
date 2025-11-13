####### Plan #######
"""
- z.B. mit dem Paket validate-email-wt
- Eine Liste an "neuen" Emails aus einer xlsx (default: agencies_new_enriched) und einer Spalte
- nur die Endungen nehmen
- Diese Liste validieren --> True Spalte
- alle mit True: an eine bestehende Liste agency_emailx.xlsx anhängen
"""

import pandas as pd
import re

from freelanceBot.utils.email_checker import find_email_on_website



PATH_ENRICHED = "agencies_enriched.xlsx"
PATH_AGENCY_EMAILS_NEW = "agency_emails_new.xlsx"
PATH_AGENCY_EMAILS = "agency_emails.xlsx"
EMAIL_COLUMN = "email"

EMAIL_PARTS = [
    "info","kontakt","contact","freelancer", "freelance",
    "inbox", "recruiting","bewerbung", "application", "applications", "projects",
    "hello","hi","office","mail","post","team",
    "sales","vertrieb","business","b2b","partner","alliances",
    "jobs","career","karriere","hr","humanresources"
]

BAD_LIST = [
    "aplitrak.com",
]

def _save_excel(df: pd.DataFrame, excel_path: str):
    with pd.ExcelWriter(excel_path, engine="openpyxl", mode="w") as writer:
        df.to_excel(writer, index=False)
    return excel_path

def _drop_bad_list(df: pd.DataFrame, bad_list = BAD_LIST) -> pd.DataFrame:
    pattern = "|".join(re.escape(x) for x in bad_list)
    mask = df["text"].str.contains(pattern, case=False, na=False)

    # Alle Rows DROPPEN, bei denen etwas aus bad_list vorkommt
    df_clean = df[~mask]

    return df_clean
    

def domain_from_email(email:str):
    try:
        return email.split("@", 1)[1].strip().lower()
    except Exception:
        return None
    
# Funktion für Common Email Adress mit find_email_on_website
def find_common_email(domain: str, local_parts: list[str] = EMAIL_PARTS):
    print(f"Finding common email for: {domain}")
    cmn = find_email_on_website(domain, local_parts)
    if cmn is not None: 
        print(f"Found {cmn}")
    return cmn

def common_email_column (path_enriched: str = PATH_ENRICHED, email_column: str = EMAIL_COLUMN, path_master = PATH_AGENCY_EMAILS) -> pd.DataFrame:
    df = pd.read_excel(path_enriched)
    df_master = pd.read_excel(path_master)
    
    # Create column with only domain
    df["domain"] = df[email_column].map(domain_from_email)
    
    # Elemente aus Droplist entfernen
    df_no_baddies =  _drop_bad_list(df, BAD_LIST)

    # Duplicate Domains droppen
    df_nodupes = df_no_baddies.drop_duplicates(subset="domain")
    
    # Sicherstellen, dass diejenigen, die schon im masterfile drin sind, ebenfalls gedropped werden
    mask_drop = df_nodupes["domain"].isin(df_master["domain"])
    df_filtered = df_nodupes.loc[~mask_drop]
    
    # Create Common email adress
    df_filtered["email_common"] = df_filtered["domain"].map(lambda x: find_common_email(x, local_parts=EMAIL_PARTS))
    
    print(f"Searched {len(df_filtered)} emails.")

    return df_filtered[["domain", "email_common"]]



def append_excel(df: pd.DataFrame, path_master: str = PATH_AGENCY_EMAILS):
    """
    Appends a dataframe to a master xlsx file
    """
    print("### Appending excel")
    df_master = pd.read_excel(path_master)
    df_full_new = pd.concat([df_master, df])
    _save_excel(df_full_new, path_master)
    return df_full_new


if __name__ == "__main__":
    df_common_email = common_email_column(path_enriched="agencies_full.xlsx")
    _save_excel(df_common_email, PATH_AGENCY_EMAILS_NEW)
    append_excel(df_common_email)
    print("Finished")


