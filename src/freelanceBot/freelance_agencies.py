from freelanceBot.freelance_actions import FreelanceActions
import pandas as pd
from nameparser import HumanName
import gender_guesser.detector as gender

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




def main():
    todays_list()
    df_cleaned = clean_new_list()
    # Guess Gender
    # Gess Surname
    # Append to full list


if __name__ == "__main__":
    clean_new_list()
