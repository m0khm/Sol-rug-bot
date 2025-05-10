# src/selenium_pump.py

import os, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class PumpSeleniumBot:
    def __init__(self,
                 profile_dir: str,
                 driver_path: str = "chromedriver",
                 headless: bool = False):
        opts = Options()
        opts.add_argument(f"--user-data-dir={profile_dir}")
        opts.add_argument("--disable-popup-blocking")
        if headless:
            opts.add_argument("--headless=new")
        self.driver = webdriver.Chrome(executable_path=driver_path, options=opts)
        self.wait = WebDriverWait(self.driver, 30)

    def connect_wallet(self):
        self.driver.get("https://pump.fun")
        btn = self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(text(),'Connect')]")
        ))
        btn.click()
        time.sleep(2)
        main, popup = self.driver.window_handles[:2]
        self.driver.switch_to.window(popup)
        self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'Connect')]"))).click()
        self.driver.switch_to.window(main)

    def create_token(self, name: str, ticker: str,
                     price_usd: float, description: str,
                     image_path: str,
                     fee_pct: float = None,
                     curve_exponent: float = None,
                     initial_reserve_sol: float = None):
        self.driver.get("https://pump.fun/create")
        self.wait.until(EC.presence_of_element_located((By.NAME, "name")))

        self.driver.find_element(By.NAME, "name").send_keys(name)
        self.driver.find_element(By.NAME, "ticker").send_keys(ticker)
        self.driver.find_element(By.NAME, "price").clear()
        self.driver.find_element(By.NAME, "price").send_keys(str(price_usd))
        self.driver.find_element(By.NAME, "description").send_keys(description)

        self.driver.find_element(By.XPATH, "//input[@type='file']")\
            .send_keys(os.path.abspath(image_path))

        if any([fee_pct, curve_exponent, initial_reserve_sol]):
            self.driver.find_element(By.XPATH, "//button[contains(text(),'Show more options')]").click()
            time.sleep(1)
            if fee_pct is not None:
                fld = self.driver.find_element(By.NAME, "fee"); fld.clear(); fld.send_keys(str(fee_pct))
            if curve_exponent is not None:
                fld = self.driver.find_element(By.NAME, "curveExponent"); fld.clear(); fld.send_keys(str(curve_exponent))
            if initial_reserve_sol is not None:
                fld = self.driver.find_element(By.NAME, "initialReserve"); fld.clear(); fld.send_keys(str(initial_reserve_sol))

        self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Create coin')]"))).click()
        time.sleep(2)
        main, popup = self.driver.window_handles[:2]
        self.driver.switch_to.window(popup)
        self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Sign')]"))).click()
        self.driver.switch_to.window(main)
        time.sleep(60)

    def close(self):
        self.driver.quit()
