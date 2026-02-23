"""
Jobright.ai - Automated Insider Connection Email Bot (Selenium)

Usage:
  1. pip install selenium webdriver-manager
  2. Update EMAIL, PASSWORD, and optionally CUSTOM_MESSAGE below
  3. Run: python jobright_email_bot.py

Notes:
  - Uses Chrome with a visible browser so you can monitor actions
  - Add --headless flag or set HEADLESS=True for background execution
  - Personalized outreach gets far better results than mass emails
  - Respect Jobright's ToS and rate limits
"""

import time
import logging
import argparse
from dataclasses import dataclass, field
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
)

try:
    from webdriver_manager.chrome import ChromeDriverManager
    USE_WDM = True
except ImportError:
    USE_WDM = False

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

@dataclass
class Config:
    # Auth
    email: str = "YOUR_EMAIL@example.com"
    password: str = "YOUR_PASSWORD"

    # Target
    jobs_url: str = "https://jobright.ai/jobs"
    applied_tab: bool = True          # True = process Applied jobs, False = Recommended

    # Behavior
    max_jobs: int = 50                # Max job cards to process (0 = unlimited)
    max_emails_per_job: int = 20      # Max emails per job listing
    delay_between_emails: float = 3.0 # Seconds between each email send
    delay_between_jobs: float = 5.0   # Seconds between job cards
    page_load_timeout: int = 15       # Seconds to wait for elements
    headless: bool = False            # Run without visible browser

    # Custom message (set to None to use Jobright's default template)
    # Use {name} placeholder for the contact's first name
    custom_message: Optional[str] = None
    # Example:
    # custom_message: str = (
    #     "Hi {name},\n\n"
    #     "I'm a CS grad student at ASU with 3+ years of data engineering "
    #     "experience. I recently applied for a role at your company and "
    #     "would love to learn about your experience there.\n\n"
    #     "Best regards,\nChirag"
    # )

    # Logging
    log_level: str = "INFO"

    # Stats tracking
    total_emails_sent: int = field(default=0, init=False)
    total_jobs_processed: int = field(default=0, init=False)
    failed_emails: list = field(default_factory=list, init=False)


# ──────────────────────────────────────────────
# Logger
# ──────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("JobrightBot")


# ──────────────────────────────────────────────
# Browser Setup
# ──────────────────────────────────────────────

def create_driver(config: Config) -> webdriver.Chrome:
    """Initialize Chrome WebDriver with optimal settings."""
    options = Options()

    if config.headless:
        options.add_argument("--headless=new")

    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # Reduce detection footprint
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    if USE_WDM:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    else:
        driver = webdriver.Chrome(options=options)

    driver.implicitly_wait(5)
    return driver


# ──────────────────────────────────────────────
# Helper Functions
# ──────────────────────────────────────────────

def safe_click(driver, element, retries=3):
    """Click with retry logic for intercepted clicks."""
    for attempt in range(retries):
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
            time.sleep(0.3)
            element.click()
            return True
        except ElementClickInterceptedException:
            time.sleep(1)
            try:
                driver.execute_script("arguments[0].click();", element)
                return True
            except Exception:
                pass
        except StaleElementReferenceException:
            time.sleep(1)
    return False


def wait_for(driver, by, value, timeout=10, condition="presence"):
    """Wait for an element with configurable condition."""
    wait = WebDriverWait(driver, timeout)
    if condition == "clickable":
        return wait.until(EC.element_to_be_clickable((by, value)))
    elif condition == "visible":
        return wait.until(EC.visibility_of_element_located((by, value)))
    else:
        return wait.until(EC.presence_of_element_located((by, value)))


def wait_for_all(driver, by, value, timeout=10):
    """Wait for multiple elements."""
    wait = WebDriverWait(driver, timeout)
    return wait.until(EC.presence_of_all_elements_located((by, value)))


def close_any_modal(driver):
    """Close any open modal/dialog."""
    close_selectors = [
        ".ant-modal-close",
        ".ant-modal [aria-label='Close']",
        ".ant-drawer-close",
    ]
    for sel in close_selectors:
        try:
            close_btn = driver.find_element(By.CSS_SELECTOR, sel)
            safe_click(driver, close_btn)
            time.sleep(0.5)
            return True
        except NoSuchElementException:
            continue
    return False


# ──────────────────────────────────────────────
# Login
# ──────────────────────────────────────────────

def login(driver, config: Config):
    """Log into Jobright.ai."""
    log.info("Navigating to Jobright...")
    driver.get(config.jobs_url)
    time.sleep(3)

    # Check if already logged in
    try:
        driver.find_element(By.CSS_SELECTOR, ".index_job-card__oqX1M")
        log.info("Already logged in!")
        return True
    except NoSuchElementException:
        pass

    log.info("Logging in...")

    try:
        # Look for login/sign-in button or redirect
        # Jobright may redirect to login automatically or show a button
        try:
            login_btn = wait_for(
                driver, By.XPATH,
                "//button[contains(text(),'Sign') or contains(text(),'Log')]",
                timeout=5, condition="clickable"
            )
            safe_click(driver, login_btn)
            time.sleep(2)
        except TimeoutException:
            # May already be on login page
            pass

        # Enter email
        email_input = wait_for(
            driver, By.CSS_SELECTOR,
            "input[type='email'], input[name='email'], input[placeholder*='email' i]",
            timeout=10, condition="visible"
        )
        email_input.clear()
        email_input.send_keys(config.email)
        time.sleep(0.5)

        # Enter password
        pwd_input = driver.find_element(
            By.CSS_SELECTOR,
            "input[type='password'], input[name='password']"
        )
        pwd_input.clear()
        pwd_input.send_keys(config.password)
        time.sleep(0.5)

        # Submit
        pwd_input.send_keys(Keys.RETURN)
        time.sleep(5)

        log.info("Login submitted — waiting for dashboard...")
        wait_for(driver, By.CSS_SELECTOR, ".index_job-card__oqX1M", timeout=15)
        log.info("✅ Logged in successfully!")
        return True

    except TimeoutException:
        log.warning(
            "Auto-login failed. Please log in manually in the browser window.\n"
            "You have 60 seconds..."
        )
        try:
            wait_for(driver, By.CSS_SELECTOR, ".index_job-card__oqX1M", timeout=60)
            log.info("✅ Manual login detected!")
            return True
        except TimeoutException:
            log.error("Login timed out.")
            return False


# ──────────────────────────────────────────────
# Navigate to Applied Tab
# ──────────────────────────────────────────────

def navigate_to_tab(driver, config: Config):
    """Click the Applied tab if configured."""
    if not config.applied_tab:
        return

    try:
        applied_tab = wait_for(
            driver, By.XPATH,
            "//div[contains(@class,'ant-segmented-item')][.//div[contains(text(),'Applied')]]"
            " | //span[contains(text(),'Applied')]/ancestor::*[contains(@class,'tab') or contains(@class,'segmented')]",
            timeout=5, condition="clickable"
        )
        safe_click(driver, applied_tab)
        log.info("Switched to Applied tab")
        time.sleep(3)
    except TimeoutException:
        log.info("Applied tab not found or already selected — continuing")


# ──────────────────────────────────────────────
# Expand Connection Categories
# ──────────────────────────────────────────────

def expand_connection_categories(driver, config: Config):
    """Click all 'View' buttons to reveal connections in each category."""
    try:
        view_buttons = driver.find_elements(
            By.CSS_SELECTOR, "#index_connect-button-id__fB_OV"
        )
        if not view_buttons:
            # Fallback: find buttons with "View" text inside connection cards
            view_buttons = driver.find_elements(
                By.XPATH,
                "//div[contains(@class,'insider-connection-card')]"
                "//button[.//span[text()='View']]"
            )

        for btn in view_buttons:
            try:
                safe_click(driver, btn)
                time.sleep(1.5)
            except Exception:
                pass

        if view_buttons:
            log.info(f"Expanded {len(view_buttons)} connection categories")

    except Exception as e:
        log.debug(f"Error expanding categories: {e}")


# ──────────────────────────────────────────────
# Email a Single Connection
# ──────────────────────────────────────────────

def email_connection(driver, config: Config, mail_button, person_name: str) -> bool:
    """Click the mail button, optionally customize message, and send."""
    try:
        safe_click(driver, mail_button)
        time.sleep(2.5)

        # Wait for compose modal
        try:
            modal = wait_for(
                driver, By.CSS_SELECTOR, ".ant-modal", timeout=5, condition="visible"
            )
        except TimeoutException:
            log.warning(f"  ⚠ No email modal appeared for {person_name}")
            return False

        # Customize message if configured
        if config.custom_message:
            first_name = person_name.split()[0] if person_name else "there"
            personalized_msg = config.custom_message.replace("{name}", first_name)

            # Try to find and fill the message textarea
            textarea_selectors = [
                ".ant-modal textarea",
                ".ant-modal .ant-input",
                ".ant-modal [contenteditable='true']",
                ".ant-modal input[type='text']",
            ]
            for sel in textarea_selectors:
                try:
                    textarea = modal.find_element(By.CSS_SELECTOR, sel)
                    textarea.clear()
                    textarea.send_keys(personalized_msg)
                    time.sleep(0.5)
                    log.debug(f"  → Filled custom message for {person_name}")
                    break
                except NoSuchElementException:
                    continue

        # Click Send
        send_selectors = [
            ".ant-modal .ant-btn-primary",
            ".ant-modal button[type='submit']",
            ".ant-modal-footer .ant-btn-primary",
        ]
        for sel in send_selectors:
            try:
                send_btn = modal.find_element(By.CSS_SELECTOR, sel)
                safe_click(driver, send_btn)
                time.sleep(2)
                log.info(f"  ✅ Email sent to {person_name}")
                config.total_emails_sent += 1
                return True
            except NoSuchElementException:
                continue

        log.warning(f"  ⚠ Could not find Send button for {person_name}")
        close_any_modal(driver)
        return False

    except Exception as e:
        log.error(f"  ❌ Error emailing {person_name}: {e}")
        config.failed_emails.append(person_name)
        close_any_modal(driver)
        return False


# ──────────────────────────────────────────────
# Process All Connections for Current Job
# ──────────────────────────────────────────────

def process_connections(driver, config: Config):
    """Find and email all visible connections in the current job detail."""
    expand_connection_categories(driver, config)
    time.sleep(1)

    # Find all mail icon buttons
    mail_buttons = driver.find_elements(By.CSS_SELECTOR, "img[alt='mail-icon']")
    if not mail_buttons:
        log.info("  No email buttons found for this job")
        return 0

    count = min(len(mail_buttons), config.max_emails_per_job)
    log.info(f"  Found {len(mail_buttons)} connections (processing {count})")

    sent = 0
    for i in range(count):
        # Re-fetch buttons each iteration (DOM may change after modal interactions)
        current_buttons = driver.find_elements(By.CSS_SELECTOR, "img[alt='mail-icon']")
        if i >= len(current_buttons):
            break

        mail_icon = current_buttons[i]
        btn = mail_icon.find_element(By.XPATH, "./ancestor::button")

        # Extract person name from the parent card
        person_name = f"Person {i + 1}"
        try:
            card = btn.find_element(
                By.XPATH,
                "./ancestor::div[contains(@class,'dropdown-list-item')]"
            )
            name_el = card.find_element(
                By.CSS_SELECTOR, ".index_count-info__zLABq"
            )
            person_name = name_el.text.strip()
        except NoSuchElementException:
            pass

        log.info(f"  [{i + 1}/{count}] → {person_name}")

        success = email_connection(driver, config, btn, person_name)
        if success:
            sent += 1

        time.sleep(config.delay_between_emails)

    return sent


# ──────────────────────────────────────────────
# Main: Loop Through Job Cards
# ──────────────────────────────────────────────

def process_all_jobs(driver, config: Config):
    """Iterate through job cards and email connections for each."""

    # Collect job card IDs first to avoid stale references
    job_cards = driver.find_elements(By.CSS_SELECTOR, ".index_job-card__oqX1M")
    job_ids = [card.get_attribute("id") for card in job_cards if card.get_attribute("id")]
    total = len(job_ids)

    if config.max_jobs > 0:
        job_ids = job_ids[:config.max_jobs]

    log.info(f"Found {total} job cards (processing {len(job_ids)})")

    for idx, job_id in enumerate(job_ids):
        log.info(f"\n{'='*50}")
        log.info(f"Job {idx + 1}/{len(job_ids)} (ID: {job_id})")
        log.info(f"{'='*50}")

        try:
            # Click the job card
            card = driver.find_element(By.ID, job_id)
            safe_click(driver, card)
            time.sleep(3)

            # Wait for the detail panel to load
            try:
                wait_for(
                    driver, By.CSS_SELECTOR,
                    ".index_jobDetailContent__rhs3U, .index_sectionContent__prVJT",
                    timeout=config.page_load_timeout
                )
            except TimeoutException:
                log.warning("Job detail panel didn't load — skipping")
                continue

            # Extract job title for logging
            try:
                title_el = driver.find_element(
                    By.CSS_SELECTOR, ".index_job-title__Ok618, h1.index_job-title__Ok618"
                )
                log.info(f"Job: {title_el.text}")
            except NoSuchElementException:
                pass

            # Scroll down to insider connections section
            try:
                conn_section = driver.find_element(By.ID, "insider-connection")
                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", conn_section
                )
                time.sleep(1)
            except NoSuchElementException:
                log.info("  No insider connection section — skipping")
                continue

            # Process all connections
            sent = process_connections(driver, config)
            config.total_jobs_processed += 1
            log.info(f"  Sent {sent} emails for this job")

        except Exception as e:
            log.error(f"Error processing job {job_id}: {e}")

        time.sleep(config.delay_between_jobs)

        # Scroll job list to load more if needed
        try:
            job_list = driver.find_element(
                By.CSS_SELECTOR,
                ".index_jobList__container, [class*='jobList']"
            )
            driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight;", job_list
            )
            time.sleep(1)
        except Exception:
            pass


# ──────────────────────────────────────────────
# Entry Point
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Jobright Email Bot")
    parser.add_argument("--email", help="Jobright login email")
    parser.add_argument("--password", help="Jobright login password")
    parser.add_argument("--headless", action="store_true", help="Run headless")
    parser.add_argument("--max-jobs", type=int, default=50, help="Max jobs to process")
    parser.add_argument("--dry-run", action="store_true", help="Click through without sending")
    args = parser.parse_args()

    config = Config()
    if args.email:
        config.email = args.email
    if args.password:
        config.password = args.password
    if args.headless:
        config.headless = True
    if args.max_jobs:
        config.max_jobs = args.max_jobs

    driver = None
    try:
        driver = create_driver(config)
        log.info("Browser started")

        if not login(driver, config):
            log.error("Could not log in. Exiting.")
            return

        navigate_to_tab(driver, config)
        time.sleep(2)

        process_all_jobs(driver, config)

        # Final summary
        log.info("\n" + "=" * 50)
        log.info("📊 SUMMARY")
        log.info("=" * 50)
        log.info(f"Jobs processed:  {config.total_jobs_processed}")
        log.info(f"Emails sent:     {config.total_emails_sent}")
        log.info(f"Failed:          {len(config.failed_emails)}")
        if config.failed_emails:
            log.info(f"Failed contacts: {', '.join(config.failed_emails)}")
        log.info("=" * 50)

    except KeyboardInterrupt:
        log.info("\n⛔ Interrupted by user")
    except Exception as e:
        log.error(f"Fatal error: {e}", exc_info=True)
    finally:
        if driver:
            log.info("Closing browser...")
            driver.quit()


if __name__ == "__main__":
    main()