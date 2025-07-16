import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright
from dataclasses import dataclass
import os, re
from utils.KVManager import KeyVaultManager

class FreelanceClient:
    def __init__(self, headless: bool = True):
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch_persistent_context(
            user_data_dir=".profile_freelance",
            headless=headless,
            viewport={'width':1280, 'height':800}
        )
        self.page = self.browser.new_page()
    
    def accept_cookies(self, page):
        try:
            # Warten bis der Button erscheint (Timeout nach 3 Sekunden)
            page.wait_for_selector("#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll", timeout=3000)
            page.click("#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll")
            print("Cookie Consent akzeptiert.")
        except Exception:
            print("Kein Cookie Consent gefunden – geht weiter.")

    def login(self) -> None:
        self.page.goto("https://www.freelance.de/login.php")
        self.accept_cookies(self.page) #cookie button
        self.page.fill("#username", KeyVaultManager().get_secret('freelance-username'))
        self.page.fill("#password", KeyVaultManager().get_secret('freelance-password'))
        self.page.click("input[type=submit]")
        self.page.wait_for_selector("h3:has-text('Mein Profil')") # Erfolgskriterium
        print("Login success.")

    def close(self):
        self.browser.close()
        self._pw.stop()

if __name__ == "__main__":
    fc = FreelanceClient(headless=False)
    fc.login()
    fc.close()


@dataclass

class ScrapeEntry:
    """
    Scrapes a freelance URL for relevant content
    """
    def __init__(self, url: str):
        self.url = url
    
    def scrape(self):
        return
    
