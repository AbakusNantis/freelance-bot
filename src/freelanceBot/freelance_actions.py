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
    
    def is_logged_in(self) -> bool:
        # Auf Startseite prüfen (schnell, stabil)
        self.page.goto("https://www.freelance.de/", wait_until="domcontentloaded", timeout=60000)
        # Cookie-Banner ggf. wegklicken
        try:
            self.accept_cookies(self.page)
        except Exception:
            pass

        # Typische „eingeloggt“-Signale
        selectors = [
            "h3:has-text('Mein Profil')",           # Profilüberschrift
            "a[href*='logout']",                    # Logout-Link im Header/Dropdown
            "a:has-text('Logout')",                 # Textbasierter Logout
            "a:has-text('Mein Profil')",            # Link auf Profil
        ]
        for sel in selectors:
            if self.page.locator(sel).first.count() > 0:
                return True
        return False

    def accept_cookies(self, page):
        try:
            # Warten bis der Button erscheint (Timeout nach 3 Sekunden)
            page.wait_for_selector("#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll", timeout=3000)
            page.click("#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll")
            print("Cookie Consent akzeptiert.")
        except Exception:
            print("Kein Cookie Consent gefunden – geht weiter.")

    def login(self) -> None:
        if self.is_logged_in():
            print("Bereits eingelogged")
            return
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
                link = card.query_selector("a.small.fw-semibold.link-warning")
                if link:
                    href = link.get_attribute("href")
                    all_links.append(href)

        print(f"Received {len(all_links)} links.")
        return all_links
    
    def agency_intel(self, url: str) ->list:
        """
        Returning a list with:
        - Agency Name
        - contact person
        - contac email
        """
        self.page.goto(url)
        try:
            self.page.get_by_text("Kontaktdaten anzeigen").click(timeout=2000.0)
            sleep(0.5)

            ### Set default fallbacks) ###
            company = None
            name = None
            email = None

            ### Company ###
            project_header = self.page.locator("div.project-header")
            company_el = project_header.locator("a[onclick^='window.open']").first
            if company_el.count():
                company = (company_el.inner_text() or "")
            
            ### Name ###
            ### Variante 1
            full_block = self.page.locator("div.list-item-main").first
            name_el = full_block.locator("span[class='h5']").first
            if name_el.count():
                name = (name_el.inner_text() or "")

            ### Variante 2
            if not name:
                full_block = self.page.locator("div.media-body").first
                name_el = full_block.locator("div[class='col-md-6']").first
                if name_el.count():
                    name = (name_el.inner_text().split("\n")[0] or "")


            ### Email ###
            ### Variante 1:
            mail_block = self.page.locator("div.col-sm-6.margin-bottom-sm:has-text('E-Mail')").first
            mail_el = mail_block.locator("a[href^='mailto:']").first
            if mail_el.count(): # Prüft, ob Elemente existieren, gibt eigentliche die Anzahl zurück
                email = (mail_el.inner_text() or "").strip()

            ### Variante 2:
            if not email:
                mail_block = self.page.locator("div.col-md-6:has-text('@')").first
                mail_el = mail_block.locator("a[href^='mailto:']").first
                if mail_el.count(): # Prüft, ob Elemente existieren, gibt eigentliche die Anzahl zurück
                    email = (mail_el.inner_text() or "").strip()
            
            return [company, name, email]
        except:
            return None
    
    def agency_list(self, project_day = 0):
        import pandas as pd
        from freelanceBot.freelance_agents_excel import agents_excel
        # Liste an Links kreieren
        all_links = self.projects_urls(project_day)

        cols = ["company", "person", "email"]
        df = pd.DataFrame(columns = cols)
        for url in all_links:
            intel = self.agency_intel(url)
            if intel:
                df.loc[len(df)]=intel
        
        agents_excel(df, "agencies.xlsx")
        
        return df


    
    
    def project_name_simple(self, project_url: str):
        return project_url.split("/")[-1].replace("-", " ")
    
    def check_keywords_simple(self, project_url: str):
        return
    



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
    fc.login()
    #all_links = fc.projects_urls(1)
    #print(all_links)
    #test_link = "https://www.freelance.de/projekte/projekt-1237022-Technischer-leiter-m-w-d-SAP-Architektur-Infrastruktur-und"
    #all intel
    #for link in all_links:
    #fc.agency_intel(test_link)
    fc.agency_list(0)
    fc.close()

if __name__ == "__main__":
    main()
    
