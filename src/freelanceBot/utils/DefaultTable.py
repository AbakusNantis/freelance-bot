from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError
from KVManager import KeyVaultManager
from io import StringIO
import pandas as pd

class DefaultTable:
    """
    Default table either a csv in a blob storage or a database or something else. 
    Contains these methods:
    - load
    - write
    - delete

    We are now using a csv in the storage blob
    """
    def __init__(
            self, 
            connection_string = KeyVaultManager().get_secret("conn-str-safreelancebotprod"),
            container_name = "freelance-bot-list",
            csv_name = "fblist.csv"
            ):
        self.connection_string      = connection_string
        self.container_name         = container_name
        self.csv_name               = csv_name
        self.blob_service_client    = BlobServiceClient.from_connection_string(connection_string)
        self.blob_client            = self.blob_service_client.get_blob_client(container=self.container_name, blob = self.csv_name)
        self.df                     = self._load_table_as_df()

    def _load_table_as_df(self) -> pd.DataFrame:
        """
        Lädt die Tabelle als DataFrame. Falls das CSV im Blob-Container
        nicht existiert, wird es mit den Spalten 'url', 'date' und 'flag01'
        neu angelegt und hochgeladen.
        """
        try:
            csv_text = self.blob_client.download_blob().content_as_text(encoding='utf-8')
            df = pd.read_csv(StringIO(csv_text))
        except ResourceNotFoundError:
            # Blob existiert nicht → neues leeres DataFrame mit Standard-Spalten
            df = pd.DataFrame(columns=["url", "date", "flag01"])
            # direkt hochladen, damit der Blob beim nächsten mal existiert
            self._upload(df)
            print(f"Blob '{self.csv_name}' nicht gefunden. Leeres CSV mit Spalten {df.columns.tolist()} angelegt.")
        return df
    
    def _upload (self, df: pd.DataFrame):
        output = df.to_csv(index = False, encoding = 'utf-8')
        self.blob_client.upload_blob(output, overwrite = True)

    def write_on_table(self, key: str, column: str, value):
        """
        Sucht in der Spalte 'url' nach dem übergebenen key.
        - Wenn vorhanden: Wert in Spalte 'column' setzen.
        - Wenn nicht vorhanden: Neue Zeile mit url=key und column=value anlegen.
        """
        df = self.df

        if column not in self.df.columns:
            # Optional: neue Spalte anlegen, falls sie noch nicht existiert
            self.df[column] = pd.NA
            print(f"Created column {column}.")

        if key in self.df['url'].values:
            # existierende Zeile updaten
            self.df.loc[self.df['url'] == key, column] = value
            print(f"Updated row {key}.")
        
        else:
            # neue Zeile anlegen
            new_row = {col: None for col in df.columns}
            new_row['url'] = key
            new_row[column] = value
            self.df = pd.concat([self.df, pd.DataFrame([new_row])], ignore_index=True)
            print(f"Created row {key}.")
        
        self._upload(self.df)

    def delete_from_table(self, key: str):
        self.df = self.df[self.df['url'] !=key].reset_index(drop = True)
        self._upload(self.df)
        print(f"Deleted url {key}.")


# — Beispielnutzung —
if __name__ == "__main__":
    table = DefaultTable()

    # Schreibe oder update
    table.write_on_table("https://beispiel.de", "status", "verarbeitet")
    table.write_on_table("https://alte-url.de", "status", "verarbeitet")

    # Lösche Eintrag
    table.delete_from_table("https://alte-url.de")