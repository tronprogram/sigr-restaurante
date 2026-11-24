"""Page Object de la vista /reservas."""
import os
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class ReservasPage:
    def __init__(self, driver, base_url):
        self.driver = driver
        self.url = f"{base_url}/reservas"

    def _pausa(self):
        if os.environ.get("PAUSA_DEMO") == "1":
            time.sleep(1)

    def abrir(self):
        self.driver.get(self.url)
        return self

    def reservar(self, cliente, correo, fecha, hora, personas):
        self.driver.find_element(By.ID, "cliente").clear()
        self.driver.find_element(By.ID, "cliente").send_keys(cliente)
        self.driver.find_element(By.ID, "correo").clear()
        self.driver.find_element(By.ID, "correo").send_keys(correo)
        self.driver.execute_script(
            "document.getElementById('fecha').value = arguments[0];"
            "document.getElementById('hora').value = arguments[1];",
            fecha,
            hora,
        )
        campo_p = self.driver.find_element(By.ID, "personas")
        campo_p.clear()
        campo_p.send_keys(str(personas))
        self._pausa()
        boton = self.driver.find_element(By.ID, "btn-reservar")
        boton.click()
        WebDriverWait(self.driver, 5).until(EC.staleness_of(boton))
        return self

    def texto_confirmacion(self):
        return WebDriverWait(self.driver, 5).until(
            EC.visibility_of_element_located((By.ID, "confirmacion"))
        ).text

    def error(self, campo):
        return WebDriverWait(self.driver, 5).until(
            EC.visibility_of_element_located((By.ID, f"err-{campo}"))
        ).text

    def correos_en_tabla(self):
        return [el.text for el in self.driver.find_elements(By.CSS_SELECTOR, "td.col-correo")]
