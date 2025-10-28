def agents_excel(rows, excel_path, sheet_name="Sheet1"):
    import pandas as pd

    # rows kann DataFrame ODER list[dict]/list[list/tuple] sein
    if isinstance(rows, pd.DataFrame):
        df_in = rows.copy()
    else:
        df_in = pd.DataFrame(rows)

    if df_in.empty:
        # optional: trotzdem Datei anlegen/leeres Sheet schreiben
        with pd.ExcelWriter(excel_path, engine="openpyxl") as w:
            df_in.to_excel(w, sheet_name=sheet_name, index=False)
        return df_in

    # hier Dein bisheriger Append-/Dedupe-/Sortier-Flow …
    # (oder die zuvor gepostete append_rows_to_excel-Funktion wiederverwenden)
    # Beispiel minimal:
    from pathlib import Path
    p = Path(excel_path)
    if p.exists():
        try:
            base = pd.read_excel(p, sheet_name=sheet_name)
        except ValueError:
            base = pd.DataFrame()
    else:
        base = pd.DataFrame()

    # Spalten vereinheitlichen
    cols = list(base.columns) + [c for c in df_in.columns if c not in base.columns]
    if not base.empty:
        base = base.reindex(columns=cols)
    df_in = df_in.reindex(columns=cols)

    out = pd.concat([base, df_in], ignore_index=True).drop_duplicates(ignore_index=True)

    sort_col = "Firma" if "Firma" in out.columns else (out.columns[0] if len(out.columns) else None)
    if sort_col:
        out[sort_col] = out[sort_col].astype("string")
        out = out.sort_values(by=sort_col, kind="mergesort", na_position="last").reset_index(drop=True)

    with pd.ExcelWriter(p, engine="openpyxl") as w:
        out.to_excel(w, sheet_name=sheet_name, index=False)

    return out
