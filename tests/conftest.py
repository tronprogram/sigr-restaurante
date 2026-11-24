"""
Fixtures compartidas para API, UI y pruebas E2E de SIGR Restaurante.

Variables de entorno (opcionales):
  BASE_URL      URL de una app desplegada en contenedor. Sin ella levanta servidor local.
  SELENIUM_URL  Selenium Grid remoto (ej. http://selenium:4444).
  HEADLESS=0    Ver Chrome local en pruebas sin Grid.
"""
import os
import threading
import uuid
from pathlib import Path

import pytest
from selenium import webdriver
from werkzeug.serving import make_server

from app.servidor import crear_app

CARPETA_EVIDENCIAS = Path("evidencias")


@pytest.fixture(scope="session")
def base_url():
    externa = os.environ.get("BASE_URL")
    if externa:
        yield externa.rstrip("/")
        return
    servidor = make_server("127.0.0.1", 0, crear_app(), threaded=True)
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    yield f"http://127.0.0.1:{servidor.server_port}"
    servidor.shutdown()


@pytest.fixture(scope="session")
def api_reservas(base_url):
    return f"{base_url}/api/reservas"


@pytest.fixture(scope="session")
def api_pedidos(base_url):
    return f"{base_url}/api/pedidos"


@pytest.fixture
def correo_unico():
    return f"cliente.{uuid.uuid4().hex[:8]}@correo.com"


@pytest.fixture(scope="session")
def driver():
    opciones = webdriver.ChromeOptions()
    opciones.add_argument("--window-size=1280,900")
    remoto = os.environ.get("SELENIUM_URL")
    if remoto:
        navegador = webdriver.Remote(command_executor=remoto, options=opciones)
    else:
        if os.environ.get("HEADLESS", "1") != "0":
            opciones.add_argument("--headless=new")
        opciones.add_argument("--no-sandbox")
        if os.environ.get("CHROME_BIN"):
            opciones.binary_location = os.environ["CHROME_BIN"]
        navegador = webdriver.Chrome(options=opciones)
    yield navegador
    navegador.quit()


@pytest.fixture
def evidencia(driver, request):
    CARPETA_EVIDENCIAS.mkdir(exist_ok=True)

    def capturar(paso):
        driver.save_screenshot(str(CARPETA_EVIDENCIAS / f"{request.node.name}__{paso}.png"))

    return capturar


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    resultado = (yield).get_result()
    if resultado.when == "call" and resultado.failed and "driver" in item.fixturenames:
        CARPETA_EVIDENCIAS.mkdir(exist_ok=True)
        navegador = item.funcargs["driver"]
        navegador.save_screenshot(str(CARPETA_EVIDENCIAS / f"FALLO__{item.name}.png"))
