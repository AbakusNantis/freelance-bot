## Was tut es aktuell zuverlässig?
### freelance_actions.py
liefert die Aktionen für playwright
#### class FreelanceActions
Eine Klasse für alle Aktionen.
Dazu gehört:
- is_logged_in: Testet, ob man bereits auf freelance angemeldet ist
- accept_cookies: Klickt auf den Cookie Consent Button
- login: Einloggen gemäß der Daten, die im KeyVault hinterlegt sind (werden über den utils/KVManager geholt)
- project_urls: holt alle project urls für einen bestimmten Tag (heute oder gestern)
- agency_intel: scraped die Kontaktinformationen zu einer Projekt-URL
- agency_list: generiert aus allen neuen Project_URLs eine Liste, die dann als agencies.xlsx abgespeichert wird
- close: Schließt den Browser

#### main()
Aktuell (28.10.25) scraped die main() alle neuen project URLs von gestern und speichert sie in der agencies.xlsx ab

### freelance_agencies
#### main()
- todays_list() holt die neuen Projekt_URLS von heute (sollte erweiterbar werden auf gestern) und erstellt die agencies.xlsx
- clean_new_list() macht:
    - Duplikate entfernen
    - sicherstellen, dass emails, die in agencies_full.xlsx bereits vorkommen, nicht mehr dazu kommen
    - die Liste am Anfang der Datei ebenfalls ausgenommen wird
- enrich_df() fügt eine Gender Spalte hinzu und erkennt Vor- und Nachname, speichert als agencies_enriched.xlsx
- append_excel() hängt die neue Liste an agencies_enriched.xlsx an

### send_email
Schickt die Mail an alle aus der agencies_enriched raus