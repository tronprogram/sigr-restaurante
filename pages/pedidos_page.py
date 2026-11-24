"""Page Object de la vista /pedidos."""
import os
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait


class PedidosPage:
    def __init__(self, driver, base_url):
        self.driver = driver
        self.url = f"{base_url}/pedidos"

    def _pausa(self):
        if os.environ.get("PAUSA_DEMO") == "1":
            time.sleep(1)

    def abrir(self):
        self.driver.get(self.url)
        return self

    def ordenar(self, cliente, tipo, plato, cantidad):
        self.driver.find_element(By.ID, "cliente").clear()
        self.driver.find_element(By.ID, "cliente").send_keys(cliente)
        Select(self.driver.find_element(By.ID, "tipo")).select_by_value(tipo)
        Select(self.driver.find_element(By.ID, "plato")).select_by_value(plato)
        campo_c = self.driver.find_element(By.ID, "cantidad")
        campo_c.clear()
        campo_c.send_keys(str(cantidad))
        self._pausa()
        boton = self.driver.find_element(By.ID, "btn-ordenar")
        boton.click()
        WebDriverWait(self.driver, 5).until(EC.staleness_of(boton))
        return self

    def texto_confirmacion(self):
        return WebDriverWait(self.driver, 5).until(
            EC.visibility_of_element_located((By.ID, "confirmacion-pedido"))
        ).text

    def codigos_en_tabla(self):
        return [el.text for el in self.driver.find_elements(By.CSS_SELECTOR, "td.col-codigo")]
