from freelanceBot.freelance_actions import FreelanceActions
import pandas as pd
from nameparser import HumanName
import gender_guesser.detector as gender

PATH_FULL = "agencies_full.xlsx"
PATH_NEW = "new_projects_raw.xlsx"
PATH_CLEANED = "agencies_new_cleaned.xlsx"
PATH_ENRICHED = "agencies_enriched.xlsx"

RELEVANT_COLS = ["company", "person", "email"]

EXCLUDES = [
    "concordcobalt.de", # machen keine Auftrags und Geschäftsbesorungen für Firmen
    "ferchau.com", # haben ein Business Portal --> registriert
    "hays.de",
    "hays.at",
    "etengo.de",
    "percision.de", # nur Einzelbeauftragungen
    "sparkm.de", # anderer Bereich
    "sw-xperts.com", # bieten sie nicht an
    "solcom.de", #hatte ich schon zu viele angeschrieben
    "varius-ti.com" # reines bodyleasing
    "weissenberg-group.de" # in der Regel keine solchen Anfragen
]


def _save_excel(df: pd.DataFrame, excel_path: str):
    with pd.ExcelWriter(excel_path, engine="openpyxl", mode="w") as writer:
        df.to_excel(writer, index=False)
    return excel_path

def agencies_new_projects(time_period = 0, headless = False) ->pd.DataFrame:
    """
    0 = today
    1 = yesterday
    7 = 7 days ago
    """
    fc = FreelanceActions(headless)
    fc.login()
    df = fc.new_projects_intel(time_period) # Creates new_projects_raw file with all data
    fc.close()
    return df

def clean_new_list(path_new = PATH_NEW, path_master = PATH_FULL, output_path = PATH_CLEANED) -> pd.DataFrame:
    """
    Cleans the list of new projects for agency data use. 
    - Takes only the relevant columns
    - removes rows with duplicate emails
    - Filters emails, that are already in the master_file
    - 
    Returns cleaned DataFrame with only relevant columns to output path
    """
    print("### Cleaning Agents list")
    # Get lists
    df_new = pd.read_excel(path_new)[RELEVANT_COLS]
    df_master = pd.read_excel(path_master)
    before = len(df_new)
    print (f"{before} elements in new list")

    # Drop duplicates
    df_nodupes = df_new.drop_duplicates(subset=["email"], keep="first")

    print(f"{before - len(df_nodupes)} duplicates dropped")
    
    # Filter Emails that are already existent
    mask_drop = df_nodupes["email"].isin(df_master)
    df_new_filtered = df_nodupes.loc[~mask_drop]

    print(f"{len(df_nodupes)-len(df_new_filtered)} already existing emails dropped")

    # Drop rows containing exclude Emails
    # 1) Normalisieren & trennen: volle Adressen vs. Domains
    items = [s.strip().lower() for s in EXCLUDES]
    full_emails = {s for s in items if "@" in s}                    # z.B. "b.k@test.com"
    domains     = {s.lstrip(".") for s in items if "@" not in s}    # z.B. "solcom.de"

    # 2) E-Mail-Spalte normalisieren
    email_s = df_new_filtered["email"].astype("string").str.strip().str.lower()

    # 3) Filter-Masken
    mask_full = email_s.isin(full_emails)
    if domains:
        email_domains = email_s.str.split("@").str[-1]
        mask_domain = email_domains.fillna("").str.endswith(tuple(domains))
    else:
        mask_domain = False

    # 4) Entfernen der Zeilen
    df_filtered = df_new_filtered[~(mask_full | mask_domain)].copy()
    
    after = len(df_filtered) 
    print(f"{len(df_new_filtered)-after} removed lines due to exlusions")
    removed = before - after
    print(f"{removed} removed lines in total")
    print(f"{after} lines left")

    # Als Excel speichern
    with pd.ExcelWriter(output_path, engine="openpyxl", mode="w") as writer:
        df_filtered.to_excel(writer, index=False)
    return df_filtered

def guess_gender(name: str) -> str:
    """
    Guesses gender of a full name.
    """
    first = HumanName(name).first  # extrahiert den Vornamen
    d = gender.Detector(case_sensitive=False)
    g = d.get_gender(first)  # 'male', 'female', 'mostly_male', 'mostly_female', 'andy' (androgyn), 'unknown'
    return g

def split_name(full_name: str) -> dict:
    """
    Returns first and last name of full_name as dict. 
    {"first": "Max", "last": "Mustermann"}
    """
    if not isinstance(full_name, str) or not full_name.strip():
        return {"first": None, "last": None}
    

    n = HumanName(full_name)
    # HumanName erkennt z. B.:
    #  - "Müller, Anna" → first="Anna", last="Müller"
    #  - "Dr. Anna-Lena von der Heide" → title="Dr.", first="Anna-Lena", last="von der Heide"
    first = n.first.strip() or None
    last  = n.last.strip() or None

    # Heuristische Nachschärfung für deutsche Namenszusätze:
    # Wenn 'von/van/zu/…' irrtümlich in middle gelandet ist, hänge ihn an den Nachnamen an.
    particles = {"von","van","vom","zu","zur","zum","de","der","den","del","della","du","di"}
    middle_tokens = [t for t in n.middle.split() if t]
    if middle_tokens:
        # Falls middle ganz aus Partikeln besteht, zum Nachnamen umhängen
        if all(mt.lower() in particles for mt in middle_tokens):
            last = (" ".join(middle_tokens + ([last] if last else []))).strip()

    # Fallback: Wenn kein last erkannt und es gibt genau zwei Wörter → nimm zweites als Nachname
    if not last:
        toks = [t for t in full_name.replace(",", " ").split() if t]
        if len(toks) >= 2:
            first = first or toks[0]
            last = " ".join(toks[1:])

    return {"first": first, "last": last}



def enrich_df(df: pd.DataFrame, output_path: str = PATH_ENRICHED) -> pd.DataFrame:
    """
    Enrichment of agency data. 
    - Adding gender column
    - Adding first name and last name columns
    - saving under output_path.xlsx
    
    """
    print ("### Data")
    print ("Adding gender")
    # Guess gender
    df["gender"] = df["person"].apply(guess_gender)

    # Guess surname
    print ("Guessing first and last name")
    name_parts = df["person"].apply(split_name)
    df[["first_name", "last_name"]] = pd.DataFrame(name_parts.tolist(), index=df.index)

    # Save Excel
    print("Saving new excel")
    _save_excel(df, output_path)
    return df

def append_excel(path_full_excel: str = PATH_FULL, path_enriched_excel: str = PATH_ENRICHED):
    """
    Appends the Enriched File to the full master file
    """
    print("### Appending excel")
    df_full = pd.read_excel(path_full_excel)
    df_enr  = pd.read_excel(path_enriched_excel)
    df_full_new = pd.concat([df_full, df_enr])
    _save_excel(df_full_new, path_full_excel)
    return df_full_new




def main():
    #agencies_new_projects(time_period, headless = False) # Creates new_projects_raw.xlsx
    df_cleaned = clean_new_list()
    df_cleaned = pd.read_excel(PATH_CLEANED)
    enrich_df(df_cleaned)
    append_excel(PATH_FULL, PATH_ENRICHED)

if __name__ == "__main__":
    main()
