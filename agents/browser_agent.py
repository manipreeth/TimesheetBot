import os
import time
import asyncio
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# -----------------------------
# Utility Functions
# -----------------------------
def safe_send_keys(driver, by, value, text, retries=3):
    """Retry typing into element with re-location to avoid stale references."""
    for attempt in range(retries):
        try:
            elem = WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((by, value))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", elem)
            elem.clear()
            elem.send_keys(text)
            return True
        except Exception as e:
            logging.warning(f"Retry {attempt+1}/{retries} typing into {value}: {e}")
            time.sleep(1)
    return False


def safe_select(driver, by, value, option, retries=3):
    """Retry selecting a dropdown value with re-location and retries."""
    for attempt in range(retries):
        try:
            elem = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((by, value))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", elem)
            Select(elem).select_by_value(str(option))
            return True
        except Exception as e:
            logging.warning(f"Retry {attempt+1}/{retries} selecting {value}: {e}")
            time.sleep(1)
    return False


def normalize_hours(hours_val):
    """Normalize hours to H:MM format (string)."""
    if isinstance(hours_val, (int, float)):
        return f"{int(hours_val)}:00"
    s = str(hours_val).strip()
    return f"{s}:00" if s.isdigit() else s


def normalize_timesheet(data):
    """Group same project+activity across all days into one row."""
    app_code = data.get("application_code", "").strip()

    day_map = {
        "monday": "MonHours",
        "tuesday": "TueHours",
        "wednesday": "WedHours",
        "thursday": "ThuHours",
        "friday": "FriHours",
    }

    rows = []
    key_map = {}  # (app, project, activity) -> row

    for day_key, base_id in day_map.items():
        for item in data.get(day_key, []):
            proj = item.get("project", "").strip()
            activity = str(item.get("activity", "")).strip()
            hours_str = normalize_hours(item.get("hours", 0))

            key = (app_code, proj, activity)
            if key not in key_map:
                row = {
                    "application": app_code,
                    "project": proj,
                    "activity": activity,
                    "hours": {}
                }
                key_map[key] = row
                rows.append(row)

            # merge into same row
            key_map[key]["hours"][base_id] = hours_str

    return rows


def prepare_rows(data):
    """Each project-day combination is its own row (no grouping)."""
    app_code = data.get("application_code", "").strip()

    day_map = {
        "monday": "MonHours",
        "tuesday": "TueHours",
        "wednesday": "WedHours",
        "thursday": "ThuHours",
        "friday": "FriHours",
    }

    rows = []
    for day_key, base_id in day_map.items():
        for item in data.get(day_key, []):
            proj = item.get("project", "").strip()
            activity = str(item.get("activity", "")).strip()
            hours_str = normalize_hours(item.get("hours", 0))

            row = {
                "application": app_code,
                "project": proj,
                "activity": activity,
                "hours": {base_id: hours_str}
            }
            rows.append(row)

    return rows

# -----------------------------
# Main Function
# -----------------------------
async def fill_timesheet(timesheet_data, preview_only=True, group=True):
    """Fill timesheet rows in browser with Selenium."""
    def _run():
        rows = normalize_timesheet(timesheet_data) if group else prepare_rows(timesheet_data)
        logging.info(f"Prepared {len(rows)} rows for filling: {rows}")

        options = webdriver.ChromeOptions()
        # options.add_argument("--headless=new")  # Uncomment for headless mode
        options.add_argument("--window-size=1400,900")

        driver = None
        try:
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options
            )

            driver.get("http://127.0.0.1:5500/templates/timesheet.html")

            wait = WebDriverWait(driver, 15)
            wait.until(EC.presence_of_element_located((By.ID, "timesheetTable")))

            logging.info("Page loaded. Title: %s", driver.title)

            os.makedirs("static", exist_ok=True)
            before_path = "static/timesheet_before.png"
            driver.save_screenshot(before_path)
            logging.info(f"Saved pre-fill screenshot: {before_path}")

            if preview_only:
                driver.quit()
                return before_path, None

            for idx, row in enumerate(rows, start=1):
                if idx > 1:
                    add_btn = wait.until(EC.element_to_be_clickable((By.ID, "addRowBtn")))
                    add_btn.click()
                    wait.until(lambda d: d.find_element(By.ID, f"applicationId{idx}"))

                safe_send_keys(driver, By.ID, f"applicationId{idx}", row["application"])
                safe_send_keys(driver, By.ID, f"projectId{idx}", row["project"])

                if row["activity"]:
                    safe_select(driver, By.ID, f"activityId{idx}", row["activity"])

                for base_key, val in row["hours"].items():
                    element_id = f"{base_key}{idx}"
                    safe_send_keys(driver, By.ID, element_id, val)

            after_path = "static/timesheet_filled.png"
            driver.save_screenshot(after_path)
            logging.info(f"Saved filled screenshot: {after_path}")

            driver.quit()
            return after_path, "submitted"

        except Exception as e:
            if driver:
                err_path = "static/error.png"
                driver.save_screenshot(err_path)
                logging.error(f"Error occurred! Screenshot saved to {err_path}", exc_info=True)
                driver.quit()
            raise e

    return await asyncio.to_thread(_run)
