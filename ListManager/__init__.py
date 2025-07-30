import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from azure.storage.blob import BlobServiceClient
from utils.KVManager import KeyVaultManager
from io import StringIO
import pandas as pd

dataframe_cols = ["url", "date", "url_checked"]


class DefaultTable:
    """
    Default table backed by a CSV in Azure Blob Storage.
    Methoden:
    - load
    - write_on_table
    - delete_from_table
    """
    def __init__(
        self,
        connection_string: str = KeyVaultManager().get_secret("conn-str-safreelancebotprod"),
        container_name: str = "freelance-bot-list",
        csv_name: str = "fblist.csv"
    ):
        # 1) Erstelle eine BlobServiceClient-Instanz
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        # 2) Lege den BlobClient an
        self.container_name = container_name
        self.csv_name = csv_name
        self.blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name,
            blob=self.csv_name
        )
        # 3) Lade das DataFrame initial
        self.df = self._load_table_as_df()

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
            df = pd.DataFrame(columns=dataframe_cols)
            # direkt hochladen, damit der Blob beim nächsten mal existiert
            self._upload(df)
            print(f"Blob '{self.csv_name}' nicht gefunden. Leeres CSV mit Spalten {df.columns.tolist()} angelegt.")
        return df

    def _upload(self, df: pd.DataFrame):
        output = df.to_csv(index=False, encoding='utf-8')
        # überschreibe den Blob
        self.blob_client.upload_blob(output, overwrite=True)

    def check_col_for_key (self, key: str, column: str, value):
        """
        Sucht in df['url'] nach key:
        - existiert key: setzt df.loc[... , column] = value
        - existiert nicht: fügt neuen Record mit url=key und column=value hinzu
        """
        # Falls du immer den neuesten Stand aus dem Blob haben willst,
        # lade hier neu: df = self._load_table_as_df()
        df = self.df

        if column not in df.columns:
            df[column] = pd.NA
            print(f"Created column {column}.")

        if key in df['url'].values:
            df.loc[df['url'] == key, column] = value
            print(f"Updated row {key}.")
        else:
            new_row = {col: None for col in df.columns}
            new_row['url'] = key
            new_row[column] = value
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            print(f"Created row {key}.")

        # Daten zurückschreiben und lokalen Cache updaten
        self._upload(df)
        self.df = df

    def delete_url_from_table(self, key: str):
        """
        Löscht die gesamte Zeile mit url == key
        """
        df = self.df
        df = df[df['url'] != key].reset_index(drop=True)
        self._upload(df)
        self.df = df
        print(f"Deleted url {key}.")


if __name__ == "__main__":
    table = DefaultTable()
    table.check_col_for_key("https://beispiel.de", "url_checked", False)
    table.check_col_for_key("https://alte-url.de", "url_checked", True)
    table.delete_url_from_table("https://alte-url.de")
