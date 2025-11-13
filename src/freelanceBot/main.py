from freelanceBot.freelance_actions import main as freelance_actions
from freelanceBot.freelance_projects import main as freelance_projects
from freelanceBot.freelance_agencies import main as freelance_agencies
from freelanceBot.send_email import main as send_agency_mail


def main(time_period, headless = False, mail_freelance_agencies = False,):
    # Scrape freelance for given time period
    freelance_actions(time_period=time_period, headless = headless)
    # Prepare Project Lists for the day
    freelance_projects()
    # Prepare Agencies Lists for the day
    freelance_agencies()
    if mail_freelance_agencies:
        send_agency_mail()


if __name__ == "__main__": 
    print(main(
        time_period = 0, 
        headless = False,
        mail_freelance_agencies=True,
        ))