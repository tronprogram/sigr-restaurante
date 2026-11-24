"""Pruebas de interfaz y flujos E2E con Selenium para SIGR Restaurante."""
import pytest
import requests

from pages.pedidos_page import PedidosPage
from pages.reservas_page import ReservasPage

pytestmark = pytest.mark.e2e


def test_reserva_web_aparece_en_api(driver, base_url, api_reservas, correo_unico, evidencia):
    pagina = ReservasPage(driver, base_url).abrir()
    pagina.reservar("Sofia Mora", correo_unico, "2026-12-20", "19:00", 2)
    assert "RES-" in pagina.texto_confirmacion()
    evidencia("reserva_web_confirmada")

    correos = [r["correo"] for r in requests.get(api_reservas, timeout=5).json()]
    assert correo_unico in correos


def test_reserva_api_aparece_en_tabla_web(driver, base_url, api_reservas, correo_unico, evidencia):
    datos = {
        "cliente": "Julian Rey",
        "correo": correo_unico,
        "fecha": "2026-12-21",
        "hora": "20:00",
        "personas": 4,
    }
    assert requests.post(api_reservas, json=datos, timeout=5).status_code == 201
    pagina = ReservasPage(driver, base_url).abrir()
    evidencia("tabla_reservas")
    assert correo_unico in pagina.correos_en_tabla()


def test_sobreventa_web_muestra_error(driver, base_url, correo_unico, evidencia):
    pagina = ReservasPage(driver, base_url).abrir()
    # Solo hay 2 mesas para 6 personas (M5 y M6): la tercera reserva en el mismo horario falla
    pagina.reservar("Grupo Uno", f"g1.{correo_unico}", "2026-12-24", "21:00", 6)
    pagina.reservar("Grupo Dos", f"g2.{correo_unico}", "2026-12-24", "21:00", 6)
    pagina.reservar("Grupo Tres", f"g3.{correo_unico}", "2026-12-24", "21:00", 6)
    evidencia("sobreventa_bloqueada")
    assert "No hay mesas disponibles" in pagina.error("mesa")


def test_pedido_web_aparece_en_api(driver, base_url, api_pedidos, evidencia):
    pagina = PedidosPage(driver, base_url).abrir()
    pagina.ordenar("Andrea Silva", "domicilio", "pasta", 2)
    assert "PED-" in pagina.texto_confirmacion()
    assert "$64000" in pagina.texto_confirmacion()
    evidencia("pedido_web_confirmado")

    pedidos = requests.get(api_pedidos, timeout=5).json()
    assert any(p["cliente"] == "Andrea Silva" and p["total"] == 64000 for p in pedidos)


def test_navegacion_reservas_a_pedidos(driver, base_url):
    driver.get(f"{base_url}/reservas")
    assert "SIGR Restaurante" in driver.page_source
    driver.get(f"{base_url}/pedidos")
    assert "Cola de cocina" in driver.page_source
