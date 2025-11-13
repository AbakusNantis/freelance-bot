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
    df = df.copy() # Vermeidet aus irgendeinem Grund den Fehler "A value is trying to be set on a copy of a slice from a DataFrame.Try using .loc[row_indexer,col_indexer] = value instead"

    # 1) Normalisieren
    strings_to_exclude = [s.strip().lower() for s in EXCLUDES_FROM_PROJECTNAME]
    df["normalized"] = df[PROJECTNAME_ROW].astype("string").str.strip().str.lower()  

    # 2) Filter-Masken
    pattern = "|".join(re.escape(s)for s in strings_to_exclude)
    keep_mask = ~df["normalized"].astype(str).str.contains(pattern, case=False, na=False, regex = True)
    df_filtered = df.loc[keep_mask].drop(columns = ["normalized"])

    return df_filtered

def preprocess(df: pd.DataFrame, output_path = CLEANED_PROJECTS_FILE) -> pd.DataFrame:
    print (f"{len(df)} rows before preprocessing.")
    
    # Drop rows with empty columns
    df_nona = df.dropna(axis=0)
    print (f"{len(df)-len(df_nona)} dropped rows with empty values")
    
    # Drop rows containing project prompts that have to be excluded
    df_excluded_names = exclude_from_projectnames(df_nona)
    print (f"{len(df_nona)-len(df_excluded_names)} dropped rows based on projectnames")
    print (f"{len(df_excluded_names)} left")

    # save to excel
    df_excluded_names.to_excel(output_path, index=False)
    return df_excluded_names

def main():
    df = pd.read_excel("new_projects_raw.xlsx")
    preprocess(df)

if __name__ == "__main__": 
    main()