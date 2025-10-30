import pandas as pd
import re

NEW_PROJECTS_FILE = r"new_projects_raw.xlsx"
CLEANED_PROJECTS_FILE = r"new_projects_cleaned.xlsx"

# Strings in the project name that lead to dropping a row
PROJECTNAME_ROW = "project_name"
PROJECTDESC_ROW = "project_description"

EXCLUDES_FROM_PROJECTNAME = [
    "bauleiter", 
    "Linux",
    "SAP",    
    "Unix", 
    "wordpress",
]

def exclude_from_projectnames(df: pd.DataFrame) -> pd.DataFrame:
    """
    Drops rows from an exclude list, if substring from list is in projectname. 
    Therefore, for example projects that contain 'SAP' are all dropped.
    """
    # 1) Normalisieren
    before = len(df)
    print (f"Starting with {before} rows.")
    strings_to_exclude = [s.strip().lower() for s in EXCLUDES_FROM_PROJECTNAME]
    df["normalized"] = df[PROJECTNAME_ROW].astype("string").str.strip().str.lower()

    # 2) Filter-Masken
    pattern = "|".join(re.escape(s)for s in strings_to_exclude)
    keep_mask = ~df["normalized"].astype(str).str.contains(pattern, case=False, na=False, regex = True)
    df_filtered = df.loc[keep_mask].drop(columns = ["normalized"])
    dropped = before - len(df_filtered)
    print(f"{dropped} rows based on project name, {len(df_filtered)} rows left.")
    return df_filtered

def preprocess(df: pd.DataFrame, output_path = CLEANED_PROJECTS_FILE) -> pd.DataFrame:
    df_excluded_names = exclude_from_projectnames(df)
    df_excluded_names.to_excel(output_path, index=False)
    return df_excluded_names

def main():
    df = pd.read_excel("new_projects_raw.xlsx")
    preprocess(df)

if __name__ == "__main__": 
    main()