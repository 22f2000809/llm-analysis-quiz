# scraper.py
import base64
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def extract_question(url: str) -> str:
    print(f"🌐 Opening quiz page: {url}")

    chrome_opts = Options()
    chrome_opts.add_argument("--headless=new")  # comment out if debugging visually
    chrome_opts.add_argument("--no-sandbox")
    chrome_opts.add_argument("--disable-dev-shm-usage")
    chrome_opts.add_argument("--disable-gpu")
    chrome_opts.add_argument("--window-size=1920,1080")

    # 🔥 Automatically install and manage correct ChromeDriver version
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_opts)

    try:
        driver.get(url)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(3)

        html = driver.page_source
        print(f"✅ Page loaded ({len(html)} chars)")

        match = re.search(r"atob\((?:'|\"|`)([^'\"`]+)(?:'|\"|`)\)", html)
        if match:
            encoded = match.group(1)
            decoded = base64.b64decode(encoded).decode("utf-8", errors="ignore")
            print("✅ Successfully decoded base64 content!")
            return decoded.strip()
        else:
            print("⚠️ No base64 found, returning visible text.")
            return driver.find_element(By.TAG_NAME, "body").text

    except Exception as e:
        print(f"❌ Error while scraping: {e}")
        return ""

    finally:
        try:
            driver.quit()
        except:
            pass
