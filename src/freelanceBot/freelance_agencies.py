from freelanceBot.freelance_actions import FreelanceActions
import pandas as pd
from nameparser import HumanName
import gender_guesser.detector as gender

def _save_excel(df: pd.DataFrame, excel_path: str):
    with pd.ExcelWriter(excel_path, engine="openpyxl", mode="w") as writer:
        df.to_excel(writer, index=False)
    return excel_path

def todays_list():
    fc = FreelanceActions(headless=False)
    fc.login()
    fc.agency_list(0)
    fc.close()

def clean_new_list(path1 = r"agencies.xlsx", path2 = r"agencies_full.xlsx", path3 = r"agencies_new_cleaned.xlsx"):
    # Get lists
    df1 = pd.read_excel(path1)
    df2 = pd.read_excel(path2)
    before = len(df1)

    # Drop duplicates
    df_nodupes = df1.drop_duplicates(subset=["email"], keep="first")
    

    # Filter Emails that are already existent
    mask_drop = df_nodupes["email"].isin(df2)
    df1_filtered = df_nodupes.loc[~mask_drop]
    removed = before - len(df1_filtered) 
    print(f"Removed {removed} lines")

    with pd.ExcelWriter(path3, engine="openpyxl", mode="w") as writer:
        df1_filtered.to_excel(writer, index=False)
    return removed

def guess_gender(name: str) -> str:
    first = HumanName(name).first  # extrahiert den Vornamen
    d = gender.Detector(case_sensitive=False)
    g = d.get_gender(first)  # 'male', 'female', 'mostly_male', 'mostly_female', 'andy' (androgyn), 'unknown'
    return g

def enrich_df(df: pd.DataFrame) -> pd.DataFrame:
    # Guess gender
    df["gender"] = df["person"].apply(guess_gender)

    # Gues surname
    _save_excel(df, "agencies_enriched.xlsx")
    return df




def main():
    #todays_list()
    #df_cleaned = clean_new_list()
    df_cleaned = pd.read_excel("agencies_new_cleaned.xlsx")
    df_enriched = enrich_df(df_cleaned)
    # Guess Gender
    # Gess Surname
    # Append to full list


if __name__ == "__main__":
    main()
