"""
    Utility functions for the WhatsApp Web Wrapper.
"""
from os import getenv
from pathlib import Path
from time import sleep
from difflib import SequenceMatcher
from random import randint, choice
from datetime import datetime

from dotenv import load_dotenv
from playwright.sync_api import Playwright, sync_playwright, Page
from bs4 import BeautifulSoup
import gspread
from oauth2client.service_account import ServiceAccountCredentials

from exceptions import NotLoggedInException, ClientMessageException
import message_format

# Load environment variables
load_dotenv(dotenv_path=Path("credentials.env"))

class Client:

    def __init__(self, row: dict[any, any], index: int):
        
        self.construct_from_row(row, index)
        self.days_left = None
        self.message_type = None

    def flush_to_sheet(self, sheet: gspread.Spreadsheet) -> None:

        self.unwrap()
        row_index = self.serial_number + 1
        column_indices = {
            "S.No.": 1,
            "name": 2,
            "days_to_review": 3,
            "last_update": 4,
            "schedule_update": 5,
            "status": 6,
            "message_status": 7
        }

        sheet.update_cell(row_index, column_indices["S.No."], self.serial_number)
        sheet.update_cell(row_index, column_indices["name"], self.name)
        sheet.update_cell(row_index, column_indices["days_to_review"], self.days_to_review)
        sheet.update_cell(row_index, column_indices["last_update"], self.last_update)
        sheet.update_cell(row_index, column_indices["schedule_update"], self.schedule_update)
        sheet.update_cell(row_index, column_indices["status"], self.status)
        sheet.update_cell(row_index, column_indices["message_status"], self.message_status)

    def unwrap(self) -> None:

        self.last_update = self.last_update.strftime("%d-%m-%Y") if self.last_update is not None else ""
        self.schedule_update = self.schedule_update.strftime("%d-%m-%Y") if self.schedule_update is not None else ""

    def construct_from_row(self, row: dict[any, any], index: int) -> None:

        self.serial_number = index+1
        self.name = row["Name"]
        self.days_to_review = row["Days To Review"] if row["Days To Review"] != "" else None
        self.last_update = datetime.strptime(row["Last Update"], "%d-%m-%Y") if row["Last Update"] != "" else None
        self.schedule_update = datetime.strptime(row["Schedule Update"], "%d-%m-%Y") if row["Schedule Update"] != "" else None 
        self.status = row["Status"] if row["Status"] != "" else None
        self.message_status = row["Message Status"] if row["Message Status"] != "" else None

        self.clear_if_valid()

    def clear_if_valid(self) -> None:

        if self.status == "Travelling" or self.status == "Break" or self.status == "Sick":

            self.days_to_review = ""
            self.last_update = None

            if self.schedule_update is not None:

                self.schedule_update = None


    def update_days_to_review(self) -> None:

        if self.last_update is not None:

            if self.schedule_update is not None and self.schedule_update > self.last_update:    

                self.days_to_review = (datetime.now() - self.schedule_update).days

            else:

                self.days_to_review = (datetime.now() - self.last_update).days - 7 

        else:

            if self.schedule_update is not None:

                self.days_to_review = (datetime.now() - self.schedule_update).days

            else:

                self.days_to_review = ""

                return None

        self.days_left = self.days_to_review

        if self.days_to_review < -1:

            self.days_to_review = "%d Days Left" % abs(self.days_to_review)

        elif self.days_to_review == -1:

            self.days_to_review = "Review Tomorrow"

        elif self.days_to_review == 0:

            self.days_to_review = "Review Today"

        else:

            self.days_to_review = "Review %d Days Overdue" % self.days_to_review

    def get_message_type(self) -> None:

        if self.status == "Travelling":

            self.message_type = "TRAVELLING_MESSAGE"

        elif self.status == "DND" or self.status == "Break":

            self.message_type = None

        elif self.status == "Sick":

            self.message_type = "SICK_MESSAGE"

        else:
            

            if self.days_left < -1:

                self.message_type = "DAILY_MESSAGE"

            elif self.days_left == -1:

                self.message_type = "REMINDER_MESSAGE"

            elif self.days_left == 0:

                self.message_type = None

            else:

                self.message_type = "OVERDUE_MESSAGE"

def get_env_variable(variable_name: str) -> str:
    """
    Get the value of an environment variable

    Args:
        variable_name (str): The name of the environment variable to get.

    Returns:
        str: The value of the environment variable.
    """
    return getenv(variable_name)

def check_logged_in(page: Page) -> bool:
    """
    Check if the user is logged in by looking for a specific element.
    """

    sleep(10)

    return page.locator("[aria-label='Chat list']").is_visible()

def login_to_whatsapp(playwright: Playwright) -> None:

    """
    Login to WhatsApp Web, saving the login state for future sessions.
    """

    auth_data_path = get_env_variable("AUTH_DATA_PATH")

    # Launch browser with persistent context
    

    # Create a new context with storage state if it exists
    if Path(auth_data_path).exists():

        context = playwright.chromium.launch_persistent_context(
            user_data_dir=r"C:\Users\mineS\AppData\Local\Google\Chrome\User Data",
            headless=False  # Set to True if you don't want to see the browser UI
        )

        page = context.new_page()

        page.goto("https://web.whatsapp.com/")

        if not check_logged_in(page):
            raise NotLoggedInException("INVALID_AUTH_DATA")
        
        else:
            return (context, page)

    else:
        raise NotLoggedInException("AUTH_DATA_NOT_FOUND")

def enter_search_box(page: Page, search_term: str) -> None:

    """
    Enter a search term into the search box.
    """

    page.locator("#side").get_by_role("paragraph").click()

    page.locator("#side").get_by_role("textbox").fill(search_term)

def get_search_results(page: Page) -> None:

    """
    Get the search results.
    """

    html = page.content()

    soup = BeautifulSoup(html, "html.parser")

    results = soup.find_all("div", attrs={"role": "listitem"})

    results = [elem.find("span", attrs={"class": "x1iyjqo2 x6ikm8r x10wlt62 x1n2onr6 xlyipyv xuxw1ft x1rg5ohu _ao3e"}) for elem in results if elem is not None]

    results = [result.get("title") for result in results if result is not None]
    
    return results

def click_on_search_result(page: Page, search_term: str, results: list[str]) -> bool:

    """
    Click on a search result.
    """

    target, current_best = None, 0

    for result in results:

        if search_term.lower() in result.lower():

            if SequenceMatcher(None, search_term, result).ratio() > current_best:

                current_best = SequenceMatcher(None, search_term, result).ratio()

                target = result

    if target is not None:

        page.get_by_title(target, exact=True).first.click()

        return True
    
    else:

        return False

def has_chatted_today(page: Page) -> bool:

    """
    Check if the user has chatted today.
    """

    html = page.content()

    soup = BeautifulSoup(html, "html.parser")

    date_holders = soup.find_all("span", attrs={"class": "_ao3e"})

    date_holders = [date_holder.text.lower() for date_holder in date_holders if date_holder is not None]


    if "today" in date_holders:
        return True
    else:
        return False

def send_message(page: Page, message: str) -> None:

    """
    Send a message to the user.
    """

    page.locator("#main").get_by_role("paragraph").click()

    page.locator("#main").get_by_role("textbox").fill(message)

    page.locator("#main").get_by_label("Send").click()

def send_client_message(page: Page, client_name: str, message_type: str) -> None:

    """
    Send a message to a client.
    """

    try:
        sleep(randint(1,3))

        enter_search_box(page, client_name)

        print(client_name)

        sleep(randint(1,3))

        state = click_on_search_result(page, client_name, get_search_results(page))

        sleep(randint(1,3))

        if state:

            if not has_chatted_today(page):
                
                message = None

                if message_type == "DAILY_MESSAGE":
                    message = choice(message_format.DAILY_MESSAGE)

                elif message_type == "REMINDER_MESSAGE":
                    message = choice(message_format.REMINDER_MESSAGE) + message_format.CALENDAR_LINK

                elif message_type == "OVERDUE_MESSAGE":
                    message = choice(message_format.OVERDUE_MESSAGE)

                elif message_type == "SICK_MESSAGE":
                    message = choice(message_format.SICK_MESSAGE)

                elif message_type == "TRAVELLING_MESSAGE":
                    message = choice(message_format.TRAVELLING_MESSAGE)
                
                if message is not None:
                    print(message_type, message)

                    
                    send_message(page, message)

                    return True
                else:
                    return False
                


            else:
                return False

        else:

            raise ClientMessageException("CLIENT_NOT_FOUND")
    
    except Exception as e:

        raise ClientMessageException(str(e))

def create_google_sheet_client() -> gspread.Client:

    """
    Create a Google Sheet client.
    """

    scope = [
        'https://www.googleapis.com/auth/drive',
        'https://www.googleapis.com/auth/drive.file'
        ]

    file_name = get_env_variable("SERVICE_ACCOUNT_CREDENTIALS_PATH")
    
    creds = ServiceAccountCredentials.from_json_keyfile_name(file_name,scope)

    client = gspread.authorize(creds)

    return client

def get_google_sheet(client: gspread.Client) -> gspread.Spreadsheet:

    """
    Get the data from the Google Sheet.
    """

    sheet_name = get_env_variable("CLIENT_SHEET_NAME")

    sheet = client.open(sheet_name).sheet1

    return sheet


if __name__ == "__main__":

    client = create_google_sheet_client()

    sheet = get_google_sheet(client)

    
    temp = sheet.get_all_records()
    test = []
    for j, i in enumerate(temp):

        test.append(Client(i, j))

    for client in test:

        client.update_days_to_review()
        client.get_message_type()

        #sleep(10)
        #client.flush_to_sheet(sheet)
    

    with sync_playwright() as playwright:

        context, page = login_to_whatsapp(playwright)

        for client in test:
            
            try:
                state = send_client_message(page, client.name, client.message_type)

            except ClientMessageException as e:
                client.message_status = "NOT_SENT (CLIENT_NOT_FOUND)"

            if state:
                client.message_status = "SENT"
            else:
                client.message_status = "NOT_SENT (ALREADY_CHATTED OR REVIEW TODAY)"

            client.flush_to_sheet(sheet)

            #TODO: handle errors by passing into the message status field of the client class

