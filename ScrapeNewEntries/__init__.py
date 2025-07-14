import requests
from lxml import html

class ScrapeNewEntries:
    """
    Scraper for freelance.de projects page.
    Fetches the page and extracts project URLs.
    """
    def __init__(self, url: str = "https://www.freelance.de/projekte?remotePreference=remote_remote--remote&pageSize=100"):
        self.url = url

    def scrape(self) -> list[str]:
        """
        Perform a GET request to the URL and parse project links.
        Returns:
            List[str]: List of full project URLs.
        """
        response = requests.get(self.url)
        response.raise_for_status()
        tree = html.fromstring(response.content)
        # Extract hrefs from project cards
        hrefs = tree.xpath('//search-project-card/a/@href')
        # Build absolute URLs
        full_urls = [requests.compat.urljoin(self.url, href) for href in hrefs]
        return full_urls

if __name__ == "__main__":
    #target_url = "https://www.freelance.de/projekte?remotePreference=remote_remote--remote&pageSize=100"
    fls = ScrapeNewEntries()
    print(fls.scrape())



#/html/body/app-root/div/app-content/div/projects-search/search-view/div/div/div/search-project-card[1]/a
#/html/body/app-root/div/app-content/div/projects-search/search-view/div/div/div/search-project-card[2]/a