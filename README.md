## Geplanter Aufbau
### [x]ScrapeNewEntries
Besucht die freelance Seite mit den neuesten 100 Einträgen. 
Gibt die neuesten 100 Einträge als Liste zurück.  

### [ ]Prüfen jeder URL
#### [ ] FreelanceActions
[x]Client und Login (Logged sich mit den Credentials bei Freelance ein und akzeptiert Cookies)
[ ] Return Header
[ ] Return Content
[ ] Return Startdatum
Optional:
[ ] Fill_Text_Field (Füllt das Textfeld)
[ ] select_cv
[ ] click_additional_fields
[ ] send_application
[ ] random_waiting_time
#### [ ] List Manager
[x] load_table
[x] upload (CSV mit neuem Dataframe überschreiben)
[ ] return_url_values (gibt Werte für eine URL zurück) 
[x] check_col_for_key (allgemeine Funktion, um keys in cols hinzuzufügen)
[x] delete_urls_from_table
[ ] return_list_with_unchecked_urls

#### [ ] Employee Manager
Was sollte an Informationen verfügbar sein?
- identifier
- Vorname
- Nachname
- Datum, bis zu dem nicht verfügbar
- Liste aller relevanten Skills (mit Gewichtung?)
- Liste an Ausschluss-Keywords
- Name des Textfiles mit dem CV in promptfreundlicher Form

[ ] load_employee_data -->lädt das JSON der Employees
[ ] all_employee_ids --> gibt eine Liste aller Employee IDs zurück
[ ] employee_value (id, key) --> returned einen bestimmten Wert eines bestimmten Employees

#### [] Freelance Bot
[ ] Lädt neue URLs
[ ] Speichert neue URLs ab, sofern noch nicht vorhanden, und added das Datum der Erstellung
[ ] Gibt eine Liste aller noch nicht geprüften URLs zurück
[ ] Lädt employee Liste
[ ] Für Jede URL in der Liste gibt es eine Check-Schleife
    [ ] Scrape startdatum
    [ ] Holt alle Employee IDs, die für das Startdatum relevant sind
    [ ] Titel
        [ ] Scraped Titel
        [ ] Für alle relevanten ids: Prüfe, ob der Titel zu den KeyWords passt (Hier kann ich erstmal nur prüfen, ob eines der Keywords auftaucht) --> Wenn nein: id aus den hierfür relevanten ids entfernen
    [ ] Projektbeschreibung
        Für alle relevanten IDs:
        [ ] KPI: Prüfen, ob es Ausschluss-Kriterien gibt, wenn ja --> ID entfernen
        [ ] KPI: KeyWords im Text prüfen und schauen, ob diese ein bestimmtes Ranking erreichen, wenn nein --> ID entfernen
        [ ] LLM: 
            [ ] Prompt aufrufen bzw. erstellen
            [ ] CV mit Projektbeschreibung vergleichen
            [ ] Ausschlusskriterien erneut prüfen
            [ ] scrape_kontaktperson --> Array mit [Name, Email, Telefon]
            [ ] einschaetzung_geben --> [ja/nein; Begründung in einem kurzen Satz; Kontaktperson Name; Kontaktperson Email; Kontaktperson Telefon]
                - wenn nein --> ID entfernen
                - wenn ja: Array irgendwohin in eine temporäre Liste speichern (im storage temp.csv oder so...)
            [ ] Irgendeinen Mechanismus finden, wie man damit umgeht, wenn zwei Leute auf eine Ausschreibung passen
    [ ] Flag im CSV setzen, dass diese URL bereits geprüft wurde
    [ ] Optional: Texte schreiben
[ ] Email an mich schicken mit dem temp.csv als Inhalt und klickbaren Links, ggf Texten
            