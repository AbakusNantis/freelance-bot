from entryScraper import ScrapeNewEntries

def main():
    # Scraping newest 100 entries:
    es = ScrapeNewEntries().scrape()
    return es

if __name__ == "__main__": 
    print(main())