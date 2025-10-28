from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from typing import Optional
from dotenv import load_dotenv
import os

load_dotenv()




class KeyVaultManager:
    """
    Ein Manager zum Auslesen von Secrets aus Azure Key Vault.
    Kann in anderen Klassen verwendet werden, um bestimmte Secrets zu lesen.
    """

    def __init__(
        self,
        vault_url= os.getenv("KEYVAULT_URI"),
        credential=None
    ):
        """
        Initialisiert den KeyVaultManager.

        Args:
            vault_url (str): URL des Key Vaults, z.B. "https://mein-vault.vault.azure.net".
            credential: Azure-Credential für die Authentifizierung. Falls None, wird DefaultAzureCredential() verwendet.
        """
        self.vault_url = vault_url
        self.credential = credential or DefaultAzureCredential()
        self.client = SecretClient(vault_url=self.vault_url, credential=self.credential)

    def get_secret(
        self,
        secret_name: str,
        version: Optional[str] = None
    ) -> str:
        """
        Liest den Wert eines Secrets aus dem Key Vault.

        Args:
            secret_name (str): Name des Secrets.
            version (str, optional): Versions-ID des Secrets. Falls None, wird die neueste Version ausgelesen.

        Returns:
            str: Der Secret-Wert.
        """
        secret = self.client.get_secret(name=secret_name, version=version)
        return secret.value