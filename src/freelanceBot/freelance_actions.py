import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError
from dataclasses import dataclass
import os, re
from utils.KVManager import KeyVaultManager
from time import sleep
import pandas as pd

######## CONFIGURATIONS ############
PATH_FULL = "agencies_full.xlsx"
PATH_NEW_RAW = "new_projects_raw.xlsx"
PATH_NEW_AGENCIES = "agencies.xlsx"
PATH_CLEANED = "agencies_new_cleaned.xlsx"
PATH_ENRICHED = "agencies_enriched.xlsx"

RELEVANT_COLS = ["company", "person", "email"]


####################################

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
    
    def maybe_dismiss_page(self, page: Page, timeout: int = 1500):
        """
        Erkennt die Interstitial-Seite mit dem 'nicht mehr anzeigen'-Häkchen
        und dem 'Weiter zur vorherigen Seite'-Link. Führt nur dann Aktionen aus,
        wenn die Seite tatsächlich angezeigt wird.
        
        Returns:
            True, wenn Interstitial erkannt und geschlossen wurde, sonst False.
        """
        # 1) Schnell prüfen, ob das Checkbox-/Label-Element auftaucht
        probe = self.page.locator('#no_postlogin_show_pa_default, label[for="no_postlogin_show_pa_default"]').first
        try:
            probe.wait_for(state="visible", timeout=timeout)
        except PlaywrightTimeoutError:
            return False  # keine Interstitial-Seite
        
        # 2) Häkchen setzen (über input.check oder Label-Klick)
        if page.locator('#no_postlogin_show_pa_default').count():
            page.check('#no_postlogin_show_pa_default', force=True)
        else:
            page.click('label[for="no_postlogin_show_pa_default"]', force=True)

        # 3) Weiter-Link/Button klicken
        try:
            page.get_by_role("link", name=re.compile(r"Weiter.*vorherigen Seite", re.I)).click(timeout=3000)
        except PlaywrightTimeoutError:
            # Fallback: generischer Button/Link
            page.locator('a.btn.btn-default').first.click()

        # 4) Kurzes Laden abwarten
        page.wait_for_load_state("domcontentloaded")
        return True


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
    
    def projects_urls(self, time_period: int) -> list:
        """
        Returning all project Urls for selected time period as list. 
        day: 0 = today, 1 = yesterday, 7 = last 7 days 
        """
        if time_period == 0: 
            time_str = "D0--today"
        if time_period == 1: 
            time_str = "D1--yesterday"
        if time_period == 7: 
            time_str = "D7--past_7_days"

        base_url = f"https://www.freelance.de/projekte?remotePreference=remote_remote--remote&lastUpdate={time_str}"
        self.page.goto(f"{base_url}&page=1&pageSize=100") 
        _ = self.maybe_dismiss_page(self.page)
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
                    if href and href != "":
                        all_links.append(href)

        print(f"Received {len(all_links)} links.")
        return all_links
       
    def projects_intel(self, url: str) ->list:
        """
        Returning a list with:
        - Agency Name
        - contact person
        - contact email
        """
        try:
            self.page.goto(url)
            _ = self.maybe_dismiss_page(self.page)
        
            self.page.get_by_text("Kontaktdaten anzeigen").click(timeout=2000.0)
            sleep(0.5)

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
            
            ### Project Name
            prname_block = self.page.locator("div.highlight-text").first
            name_el = prname_block.locator('h1[class="margin-bottom-xs"]').first
            if name_el.count():
                project_name = (name_el.inner_text() or "").strip()

            ### Project Text ###
            #prdesc_block = self.page.locator("div.panel.panel-default.panel-white").first
            #prdesc_block.wait_for(state = "attached", timeout=3000)

            # Textbox one ::before finden
            desc_el = self.page.locator('div.panel-body.highlight-text').first
            project_description = (desc_el.text_content() or "").strip()

            return [url, project_name, project_description, company, name, email]
        
        except PlaywrightTimeoutError:
            return None
        except Exception as e:
            print("projects_intel error:", e)
            return None
        
    def new_projects_intel(self, time_period, path_new_raw_full = PATH_NEW_RAW, path_new_agencies = PATH_NEW_AGENCIES):
        import pandas as pd
        from freelanceBot.freelance_agents_excel import agents_excel
        # Liste an Links kreieren
        all_links = self.projects_urls(time_period)

        cols = ["url", "project_name", "project_description", "company", "person", "email"]
        df = pd.DataFrame(columns = cols)
        for url in all_links:
            intel = self.projects_intel(url)
            if intel:
                df.loc[len(df)]=intel

        # export full dataset
        agents_excel(df, path_new_raw_full)

        # export only agents data
        df2 = df.drop(columns=["url", "project_name", "project_description"])
        agents_excel(df2, path_new_agencies)
        
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
    
    def scrape_freelance(self, time_period) -> pd.DataFrame:
        """
        Scraping freelance for a certain time period.
        - Login
        - agency_list:
            - new projects raw file
            - agencies raw file
        - close
        Returns full dataset as dataframe.
        """

        self.login()
        agency_list = self.new_projects_intel(time_period)
        self.close
        return agency_list

def main(time_period, headless = False):
    fc = FreelanceActions(headless)

    # test_url = r'https://www.freelance.de/projekte/projekt-1236689-SAP-Manager-SF-HCM-m-w-d'
    # print (fc.projects_intel(test_url))
    # fc.new_projects_intel(1)
    # fc.close()

    fc.scrape_freelance(time_period)

if __name__ == "__main__":
    main(1)
    
