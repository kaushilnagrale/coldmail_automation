import requests, time

from dotenv import dotenv_values

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains

config = dotenv_values(".env")

JOBRIGHT_URL = config.get("JOBRIGHT_URL")
USER_EMAIL = config.get("USER_EMAIL")
USER_PASSWORD = config.get("USER_PASSWORD")

ASU_USERID = config.get("ASU_USERID")
ASU_PASSWORD = config.get("ASU_PASSWORD")

# Chrome options

def _options_():
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")

    # Disable for faster page loads
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--blink-settings=imagesEnabled=false")

    # Use a persistent profile to retain Duo authentication (Shibboleth)
    # options.add_argument("--user-data-dir=/tmp/selenium-profile")
    # options.add_argument("--profile-directory=Default")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-features=SameSiteByDefaultCookies,CookiesWithoutSameSiteMustBeSecure")

    options.binary_location = "/usr/bin/google-chrome"
    # options.add_argument("--headless=new")  # Optional
    return options


def _click(wait, locator, retries=3):
    """Find and click an element, re-finding on StaleElementReferenceException."""
    for attempt in range(retries):
        try:
            elem = wait.until(EC.element_to_be_clickable(locator))
            elem.click()
            return
        except StaleElementReferenceException:
            if attempt == retries - 1:
                raise


def _send_keys(wait, locator, *keys, retries=3):
    """Find an element and send keys, re-finding on StaleElementReferenceException."""
    for attempt in range(retries):
        try:
            elem = wait.until(EC.element_to_be_clickable(locator))
            for k in keys:
                elem.send_keys(k)
            return
        except StaleElementReferenceException:
            if attempt == retries - 1:
                raise

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

def _speedbump(driver, timeout=20):
    wait = WebDriverWait(driver, timeout)
    # Wait until we are on the speedbump (or at least Google accounts)
    wait.until(lambda d: "accounts.google.com" in d.current_url)
    driver.switch_to.default_content()
    # Common locators for Google's "Continue"
    continue_locators = [
        (By.XPATH, "//button[.//span[normalize-space()='Continue'] or normalize-space()='Continue']"),
        (By.XPATH, "//div[@role='button'][.//span[normalize-space()='Continue'] or normalize-space()='Continue']"),
        (By.CSS_SELECTOR, "button[jsname]"),  # fallback; filtered below
    ]

    last_err = None
    for loc in continue_locators:
        try:
            btn = wait.until(EC.element_to_be_clickable(loc))

            # Guard: ensure it's actually the Continue button (avoid clicking random jsname buttons)
            text = (btn.text or "").strip().lower()
            inner = (btn.get_attribute("innerText") or "").strip().lower()
            if "continue" not in text and "continue" not in inner:
                continue

            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            btn.click()
            return True
        except Exception as e:
            last_err = e

    raise RuntimeError(f"Could not click Continue on speedbump page. Last error: {last_err}")


def authenticate(driver, wait):
    driver.get(JOBRIGHT_URL)
    main_window = driver.current_window_handle

    # Click the SIGN IN button
    _click(wait, (By.XPATH, "//span[text()='SIGN IN']"))

    # Wait for the sign-in modal's Google iframe to be visible, then switch into it

    google_iframe = wait.until(EC.presence_of_element_located(
        (By.XPATH, "//iframe[@title='Sign in with Google Button']")
    ))
    driver.switch_to.frame(google_iframe)

    # Click the Google button inside the iframe
    _click(wait, (By.XPATH, "//div[@role='button']"))
    driver.switch_to.default_content()

    # Google OAuth opens in a new popup window — switch to it
    wait.until(EC.number_of_windows_to_be(2))
    popup = [w for w in driver.window_handles if w != main_window][0]
    driver.switch_to.window(popup)

    # Step 1: Enter email and click Next
    _send_keys(wait, (By.ID, "identifierId"), USER_EMAIL, Keys.RETURN)

    if USER_EMAIL.rsplit('@')[1] == 'asu.edu':
        # Google redirects to ASU CAS SSO — fill ASURITE credentials
        _send_keys(wait, (By.ID, "username"), ASU_USERID)
        _send_keys(wait, (By.ID, "password"), ASU_PASSWORD, Keys.RETURN)

        # Wait up to 60s for Duo push approval, then click "Yes, this is my device" if prompted
        duo_wait = WebDriverWait(driver, 60)
        _click(duo_wait, (By.XPATH, "//button[contains(text(), 'Yes, this is my device')]"))
        _speedbump(driver, timeout=20)
        
    else:
        # Step 2: Standard Google password page
        _send_keys(wait, (By.NAME, "Passwd"), USER_PASSWORD, Keys.RETURN)

    # Wait for popup to close, then return to main window
    wait.until(EC.number_of_windows_to_be(1))
    driver.switch_to.window(main_window)

if __name__ == "__main__":

    #Initialize WebDriver
    driver = webdriver.Chrome(options=_options_())
    wait = WebDriverWait(driver, 10)

    try:
        authenticate(driver, wait)
        time.sleep(10)
    except Exception as e:
        print("Exception:", e)
        raise e
    finally:
        driver.quit()
