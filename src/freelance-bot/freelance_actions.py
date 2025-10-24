import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright
from dataclasses import dataclass
import os, re
from utils.KVManager import KeyVaultManager
from time import sleep

class FreelanceActions:
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
    
    def parse_new_projects(self, day: str = "today", page: int = 0) -> None:
        """
        day: today or yesterday
        int: usually 0 or 1 (page folds after 100 entries)
        """
        self.page.goto(f"https://www.freelance.de/projekte?remotePreference=remote_remote--remote&lastUpdate=D{page}--{day}&pageSize=100")     
        self.page.wait_for_selector("search-project-card")

        pages = len(page.query_selector_all(".page-item"))
        page_counter = 1

        for page_counter <= pages:
        # Alle Karten selektieren
        cards = self.page.query_selector_all("search-project-card")
        all_links = []
        for card in cards:
            # Innerhalb jeder Karte nach dem gewünschten Link suchen
            link = card.query_selector("a.small.fw-semibold.link-warning")
            if link:
                href = link.get_attribute("href")
                all_links.append(href)

        print(len(all_links))
        

    def close(self):
        self.browser.close()
        self._pw.stop()

def main():
    fc = FreelanceActions(headless=False)
    #fc.login()
    fc.parse_new_projects()
    fc.close()

if __name__ == "__main__":
    main()


@dataclass

class ScrapeEntry:
    """
    Scrapes a freelance URL for relevant content
    """
    def __init__(self, url: str):
        self.url = url
    
    def scrape(self):
        return
    
