import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright
from dataclasses import dataclass
import os, re
from utils.KVManager import KeyVaultManager
from time import sleep

GOOD_KEYWORDS = [
    "Analys",
    "Analyt",
    "Azure",
    "Data Engineer",
    "Data Scientist",
    "DevOps",
    "Developer",
    "Entwickler",
    "Interim",
    "Nearshore",
    "Offshore",
    "Python",
    "Test",

]

class FreelanceActions:
    def __init__(self, headless: bool = True):
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch_persistent_context(
            #user_data_dir=".profile_freelance",
            user_data_dir=".profile_freelance2",
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
    
    def projects_urls(self, day: int = 0) -> list:
        """
        day: 0 = today, 1 = yesterday
        int: usually 0 or 1 (page folds after 100 entries)
        """
        if day == 0: 
            day_str = "D0--today"
        if day == 1: 
            day_str = "D1--yesterday"

        base_url = f"https://www.freelance.de/projekte?remotePreference=remote_remote--remote&lastUpdate={day_str}"
        
        self.page.goto(f"{base_url}&page=1&pageSize=100") 
        sleep(2) # warten, damit die page items geladen sind    
        self.page.wait_for_selector("search-project-card")

        # How many pages of results are there
        page_items_active = len(self.page.query_selector_all(".page-item"))
        print(f"Page items active: {page_items_active}")
        page_items_disabled = len(self.page.query_selector_all(".page-item.disabled"))
        print(f"Page items disabled: {page_items_disabled}")

        
        # Bei einem disabled Element gibt es nur mehrere Seiten, weil nur "vorherige" disabled ist
        # Bei mehr als einem werden "nächste" und "vorherige" mitgezählt und müssen abgezogen werden
        if page_items_disabled ==1:
            pages = page_items_active - 2 
        else:
            pages = 1
        print(f"{pages} pages of new infos")

        all_links = []

        for page in range(1, pages+1):
            print (f"Scanning Page {page}")
            # Ggf nochmal die Seite laden
            self.page.goto(
                f"{base_url}&page={page}&pageSize=100")
            sleep(2) # warten, damit alle cards geladen sind
            # Alle Karten selektieren
            cards = self.page.query_selector_all("search-project-card")
        
            for card in cards:
                # Innerhalb jeder Karte nach dem gewünschten Link suchen
                href = card.get_attribute("href")
                all_links.append(href)
                """link = card.query_selector("a.small.fw-semibold.link-warning")
                if link:
                    href = link.get_attribute("href")
                    all_links.append(href)"""

        print(f"Received {len(all_links)} links.")
        return all_links
    
    def project_name_simple(self, project_url: str):
        return project_url.split("/")[-1].replace("-", " ")
    
    def check_keywords_simple(self, project_url: str):


    def project_name(self, project_url: str):
        self.page.goto(project_url)
        #self.page.wait_for_selector("margin-bottom-xs")
        header = self.page.locator("div.highlight-text").first
        project_name = header.inner_text()
        #project_name = header.get_attribute("h1")
        return project_name

        
        

    def close(self):
        self.browser.close()
        self._pw.stop()

def main():
    fc = FreelanceActions(headless=False)
    #fc.login()
    #all_links = fc.projects_urls(1)
    test_link = "https://www.freelance.de/projekte/projekt-1236676-Junior-1st-Level-Supporter-m-w-d"
    print (fc.project_name_simple(test_link))
    fc.close()

if __name__ == "__main__":
    main()
    
