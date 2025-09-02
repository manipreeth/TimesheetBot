import os
import time
import asyncio
import logging
import cv2, numpy as np, mss

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# -----------------------------
# Logging
# -----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# -----------------------------
# Screen Recorder
# -----------------------------
def record_screen(filename="record.avi", duration=30, fps=20):
    """Record the full screen for `duration` seconds into a video file."""
    sct = mss.mss()
    monitor = sct.monitors[1]  # full screen
    fourcc = cv2.VideoWriter_fourcc(*"XVID")
    out = cv2.VideoWriter(filename, fourcc, fps, (monitor["width"], monitor["height"]))

    start = time.time()
    while time.time() - start < duration:
        img = np.array(sct.grab(monitor))
        frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        out.write(frame)

    out.release()
    cv2.destroyAllWindows()


# -----------------------------
# Utility Functions
# -----------------------------
def safe_send_keys(driver, by, value, text, retries=3):
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
    if isinstance(hours_val, (int, float)):
        return f"{int(hours_val)}:00"
    s = str(hours_val).strip()
    return f"{s}:00" if s.isdigit() else s


def normalize_timesheet(data):
    app_code = data.get("application_code", "").strip()
    day_map = {
        "monday": "MonHours",
        "tuesday": "TueHours",
        "wednesday": "WedHours",
        "thursday": "ThuHours",
        "friday": "FriHours",
    }
    rows, key_map = [], {}
    for day_key, base_id in day_map.items():
        for item in data.get(day_key, []):
            proj = item.get("project", "").strip()
            activity = str(item.get("activity", "")).strip()
            hours_str = normalize_hours(item.get("hours", 0))
            key = (app_code, proj, activity)
            if key not in key_map:
                row = {"application": app_code, "project": proj, "activity": activity, "hours": {}}
                key_map[key] = row
                rows.append(row)
            key_map[key]["hours"][base_id] = hours_str
    return rows


def prepare_rows(data):
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
            row = {"application": app_code, "project": proj, "activity": activity, "hours": {base_id: hours_str}}
            rows.append(row)
    return rows

# -----------------------------
# Main Function
# -----------------------------
async def fill_timesheet(timesheet_data, preview_only=True, group=True, record=True, record_duration=30):
    def _run():
        rows = normalize_timesheet(timesheet_data) if group else prepare_rows(timesheet_data)
        logging.info(f"Prepared {len(rows)} rows for filling: {rows}")

        options = webdriver.ChromeOptions()
        # options.add_argument("--headless=new")  # Uncomment for headless
        options.add_argument("--window-size=1400,900")

        driver = None
        try:
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options
            )

            # Start recording if enabled
            if record:
                os.makedirs("static", exist_ok=True)
                video_path = "static/timesheet_record.avi"
                import threading
                recorder = threading.Thread(target=record_screen, args=(video_path, record_duration))
                recorder.start()
                logging.info(f"Recording started: {video_path}")

            driver.get("http://127.0.0.1:5500/templates/timesheet.html")
            wait = WebDriverWait(driver, 15)
            wait.until(EC.presence_of_element_located((By.ID, "timesheetTable")))
            logging.info("Page loaded. Title: %s", driver.title)

            before_path = "static/timesheet_before.png"
            driver.save_screenshot(before_path)

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
