from selenium import webdriver
from selenium_stealth import stealth
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
from typing import List
import random
import time

from Account import Account
from constants import *
from util import *


class Scheduler(webdriver.Chrome):
    def __init__(self, account: Account) -> None:
        # Init webdriver options
        options = webdriver.ChromeOptions()
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--log-level-1")
        service = Service(ChromeDriverManager().install())

        super().__init__(options=options, service=service)
        self.implicitly_wait(10)  # Configure wait time

        # Init stealth
        stealth(
            self,
            languages=[f"{random.choice(languages)}", f"{random.choice(languages)}"],
            vendor=f"{random.choice(vendors)}",
            platform=f"{random.choice(platforms)}",
            webgl_vendor=f"{random.choice(webgl)}",
            renderer=f"{renderers}",
            fix_hairline=True,
        )

        # Go to tiktok url to be able to add the cookies
        self.get(TIKTOK_URL)

        # Init session
        if not account.cookies:
            password = input(f"Password for {account.email}: ")
            cookies = self.login(account.email, password)
            account.cookies = cookies
            account.save()
        else:
            # Load cookies
            for cookie in account.cookies:
                self.add_cookie(cookie)

    def post(self, video_path: str, caption: None | str, date: None | datetime) -> None:
        """
        Posts a video at a specific time.

        Args:
            video_path (str): the full path to the video being uploaded.
            caption (srt): the caption to the video being uploaded.
            date (str): if the date is None it should be uploaded now.
        """
        # Navigate to the website
        if self.current_url == TIKTOK_UPLOAD_URL:
            # Navigating to the same page does not refresh it
            # so the previous video being uploaded is still on the same page
            self.refresh()
        else:
            self.get(TIKTOK_UPLOAD_URL)

        # A common error is that tiktok seemingly at random makes a popup with no text
        # which makes the program crash, so it shall be accepted if it appears
        self.wait_for_alert()

        # Write the video_path to the file input
        file_input = self.find_element(By.CSS_SELECTOR, 'input[type="file"]')
        file_input.send_keys(video_path)

        # Write caption
        caption_field = self.find_element(By.CSS_SELECTOR, 'div[spellcheck="false"]')
        caption_field.send_keys(caption)

        if date:
            # Input the date
            self.input_date(date)

        # Wait till video is uploaded and submit
        element = WebDriverWait(self, 20).until(
            EC.element_to_be_clickable(
                (
                    By.CSS_SELECTOR,
                    "#root > div > div > div > div.jsx-475921512.container-v2.form-panel > div.jsx-475921512.contents-v2.reverse > div.jsx-3457533826.form-v2.reverse > div.jsx-3457533826.button-row > div.jsx-3457533826.btn-post > button",
                )
            )
        )
        element.click()

        # Wait till posted
        time.sleep(5)

    def wait_for_alert(self, wait: int = 5):
        """
        Waits for a popup to appear and accepts it if so.
        """
        try:
            WebDriverWait(self, wait).until(EC.alert_is_present())
            alert = self.switch_to.alert
            alert.accept()
        except TimeoutException:
            pass

    def input_date(self, date: datetime):
        # Toggle the schedule switch
        schedule_switch = self.find_element(By.CSS_SELECTOR, "#tux-3")
        schedule_switch.click()

        # The first time a user schedules a video it will ask to allow the option
        # It should attempt to find the button, which comes up quite fast after toggling the schedule switch
        try:
            self.implicitly_wait(3)
            allow_button = self.find_element(
                By.CSS_SELECTOR,
                "body > div:nth-child(9) > div > div > div.tiktok-modal__modal-footer.is-horizontal > div.tiktok-modal__modal-button.is-highlight",
            )
            allow_button.click()
        except:
            print("Couldn't find accept button! Continuing...")
        finally:
            self.implicitly_wait(10)

        # Input date and time
        self.select_target_day(date.day)
        self.select_target_time(date.hour, date.minute)

    def select_target_day(self, day: int):
        # Open calendar
        calendar_btn = self.find_element(
            By.CSS_SELECTOR,
            "#root > div > div > div > div.jsx-475921512.container-v2.form-panel > div.jsx-475921512.contents-v2.reverse > div.jsx-3457533826.form-v2.reverse > div.jsx-3471246984 > div > div.jsx-3471246984.scheduled-picker > div.jsx-3471246984.date-picker-input.picker-input",
        )
        calendar_btn.click()

        month_click_count = 0

        while True:
            # Find the selectable days of the month
            valid_days = self.find_elements(
                By.CSS_SELECTOR, "span.jsx-4172176419.day.valid"
            )

            # Iterate over them till the target_day is found
            # When the day is clicked the calendar closes automatically
            for valid_day in valid_days:
                if valid_day.text == str(day):
                    valid_day.click()
                    return  # Exit the function if the target day is found

            # If the target day is not found and we haven't clicked next month button yet, click on it
            if month_click_count < 1:
                next_month_btn = self.find_element(
                    By.CSS_SELECTOR,
                    "#root > div > div > div > div.jsx-475921512.container-v2.form-panel > div.jsx-475921512.contents-v2.reverse > div.jsx-3457533826.form-v2.reverse > div.jsx-3471246984 > div > div.jsx-3471246984.scheduled-picker > div.jsx-3471246984.date-picker-input.picker-input > div > div.jsx-4172176419.month-header-wrapper > span:nth-child(3)",
                )
                next_month_btn.click()
                month_click_count += 1
            else:
                # If we've already clicked next month button once, break the loop
                break

    def select_target_time(self, hour: int, minute: int):
        # Open hour dialog
        time_btn = self.find_element(
            By.CSS_SELECTOR,
            "#root > div > div > div > div.jsx-475921512.container-v2.form-panel > div.jsx-475921512.contents-v2.reverse > div.jsx-3457533826.form-v2.reverse > div.jsx-3471246984 > div > div.jsx-3471246984.scheduled-picker > div.jsx-3471246984.time-picker-input.picker-input",
        )
        time_btn.click()

        # Wait for animation to end
        time.sleep(1)

        # Find list of hours. Returns a list of 24 items (24 hours)
        hours = self.find_elements(
            By.CLASS_NAME, "tiktok-timepicker-option-text.tiktok-timepicker-left"
        )

        # The nth web element corresponds to the hour
        target_hour = hours[hour]

        # Scroll the hour element into view
        self.execute_script("arguments[0].scrollIntoView(true);", target_hour)

        # Attempt to click on the target hour, with retries
        for _ in range(3):  # Try clicking 3 times
            try:
                target_hour.click()
                break  # Break the loop if click succeeds
            except:
                # Wait for a short time before retrying
                time.sleep(1)

        # Find list of minutes. Return a list of 12 items (ex: 05, 10, 15, 20)
        minutes = self.find_elements(
            By.CLASS_NAME, "tiktok-timepicker-option-text.tiktok-timepicker-right"
        )

        # Find nearest minute index
        minute_index = int(minute / (60 / len(minutes)))
        target_minute = minutes[minute_index]

        # Scroll the minute element into view
        self.execute_script("arguments[0].scrollIntoView(true);", target_minute)

        # Click on the target minute
        target_minute.click()

    def login(self, email: str, password: str) -> List[dict]:
        """
        Signs in to an account.

        Args:
            email (str): The email to the account
            password (str): The password to the account

        Returns:
            cookies: The session cookie to log in in the future.
        """
        print(email, password)

        # Go to the login page
        self.get(TIKTOK_LOGIN_URL)

        # Input email
        email_input = self.find_element(
            By.CSS_SELECTOR,
            "#loginContainer > div.tiktok-aa97el-DivLoginContainer.exd0a430 > form > div.tiktok-q83gm2-DivInputContainer.etcs7ny0 > input",
        )
        for letter in email:
            email_input.send_keys(letter)
            time.sleep(random.random() * 0.25)

        # Input password
        password_input = self.find_element(
            By.CSS_SELECTOR,
            "#loginContainer > div.tiktok-aa97el-DivLoginContainer.exd0a430 > form > div.tiktok-15iauzg-DivContainer.e1bi0g3c0 > div > input",
        )
        for letter in password:
            password_input.send_keys(letter)
            time.sleep(random.random() * 0.25)

        # Submit
        submit_button = self.find_element(
            By.CSS_SELECTOR,
            "#loginContainer > div.tiktok-aa97el-DivLoginContainer.exd0a430 > form > button",
        )
        submit_button.click()

        # Wait for page load
        input("Press enter when logged in: ")

        # Return cookies
        cookies = self.get_cookies()
        return cookies

    def click(self, by: str, value: str):
        """
        A simplified function for clicking elements.
        """
        self.find_element(by, value).click()
