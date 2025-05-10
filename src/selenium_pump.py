# src/selenium_pump.py

import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class PumpSeleniumBot:
    """
    Бот на Selenium, эмулирующий UI pump.fun для создания токена.
    Профиль Chrome должен уже иметь импортированный Phantom-кошелёк.
    """
    def __init__(
        self,
        profile_dir: str,
        driver_path: str = "chromedriver",
        headless: bool = False,
    ):
        opts = Options()
        opts.add_argument(f"--user-data-dir={profile_dir}")
        opts.add_argument("--disable-popup-blocking")
        if headless:
            # для новых версий Selenium/Chrome
            opts.add_argument("--headless=new")
        self.driver = webdriver.Chrome(executable_path=driver_path, options=opts)
        self.wait = WebDriverWait(self.driver, 30)

    def connect_wallet(self):
        """
        Нажимает Connect Wallet и подтверждает в Phantom.
        """
        self.driver.get("https://pump.fun")
        btn = self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(text(),'Connect')]")
        ))
        btn.click()

        # ждём всплытие окна Phantom и переключаемся
        time.sleep(2)
        handles = self.driver.window_handles
        if len(handles) < 2:
            raise RuntimeError("Не смогли открыть окно Phantom для подключения")
        main, popup = handles[0], handles[-1]
        self.driver.switch_to.window(popup)
        # кнопка Connect в окне Phantom
        self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(.,'Connect')]")
        )).click()
        # возвращаемся
        self.driver.switch_to.window(main)

    def create_token(
        self,
        name: str,
        ticker: str,
        price_usd: float,
        description: str,
        image_path: str,
        fee_pct: float = None,
        curve_exponent: float = None,
        initial_reserve_sol: float = None
    ):
        """
        Заполняет форму https://pump.fun/create и подписывает транзакцию.
        """
        self.driver.get("https://pump.fun/create")
        # ждём форму
        self.wait.until(EC.presence_of_element_located((By.NAME, "name")))

        # базовые поля
        self.driver.find_element(By.NAME, "name").send_keys(name)
        self.driver.find_element(By.NAME, "ticker").send_keys(ticker)
        price_f = self.driver.find_element(By.NAME, "price")
        price_f.clear(); price_f.send_keys(str(price_usd))
        self.driver.find_element(By.NAME, "description").send_keys(description)

        # загрузка изображения
        file_input = self.driver.find_element(By.XPATH, "//input[@type='file']")
        file_input.send_keys(os.path.abspath(image_path))

        # опциональные поля
        if any([fee_pct, curve_exponent, initial_reserve_sol]):
            self.driver.find_element(
                By.XPATH, "//button[contains(text(),'Show more options')]"
            ).click()
            time.sleep(1)
            if fee_pct is not None:
                fld = self.driver.find_element(By.NAME, "fee"); fld.clear(); fld.send_keys(str(fee_pct))
            if curve_exponent is not None:
                fld = self.driver.find_element(By.NAME, "curveExponent"); fld.clear(); fld.send_keys(str(curve_exponent))
            if initial_reserve_sol is not None:
                fld = self.driver.find_element(By.NAME, "initialReserve"); fld.clear(); fld.send_keys(str(initial_reserve_sol))

        # создаём монету
        self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(text(),'Create coin')]")
        )).click()

        # подтверждаем транзакцию в Phantom
        time.sleep(2)
        handles = self.driver.window_handles
        if len(handles) < 2:
            raise RuntimeError("Не открылось окно Phantom для подписи")
        main, popup = handles[0], handles[-1]
        self.driver.switch_to.window(popup)
        self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(text(),'Sign')]")
        )).click()
        self.driver.switch_to.window(main)

        # даём время на подтверждение в сети
        time.sleep(30)

    def close(self):
        """Закрыть браузер."""
        self.driver.quit()
