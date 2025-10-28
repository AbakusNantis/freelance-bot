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

def split_name(full_name: str) -> dict:
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



def enrich_df(df: pd.DataFrame) -> pd.DataFrame:
    # Guess gender
    df["gender"] = df["person"].apply(guess_gender)
    name_parts = df["person"].apply(split_name)
    df[["first_name", "last_name"]] = pd.DataFrame(name_parts.tolist(), index=df.index)

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
