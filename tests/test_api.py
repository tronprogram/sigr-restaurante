"""Pruebas unitarias y de contrato REST para SIGR Restaurante."""
import pytest
import requests

pytestmark = pytest.mark.api


def payload_reserva(correo, **cambios):
    datos = {
        "cliente": "Laura Gomez",
        "correo": correo,
        "fecha": "2026-12-05",
        "hora": "19:30",
        "personas": 2,
    }
    datos.update(cambios)
    return datos


def test_salud(base_url):
    r = requests.get(f"{base_url}/api/salud", timeout=5)
    assert r.status_code == 200
    body = r.json()
    assert body["estado"] == "ok"
    assert body["servicio"] == "sigr-restaurante"


def test_listar_mesas_y_menu(base_url):
    r_mesas = requests.get(f"{base_url}/api/mesas", timeout=5)
    assert r_mesas.status_code == 200
    assert len(r_mesas.json()) == 6

    r_menu = requests.get(f"{base_url}/api/menu", timeout=5)
    assert r_menu.status_code == 200
    assert "hamburguesa" in r_menu.json()


def test_crear_y_consultar_reserva(api_reservas, correo_unico):
    r = requests.post(api_reservas, json=payload_reserva(correo_unico), timeout=5)
    assert r.status_code == 201
    creada = r.json()
    assert creada["codigo"].startswith("RES-")
    assert creada["estado"] == "Confirmada"

    r_get = requests.get(f"{api_reservas}/{creada['id']}", timeout=5)
    assert r_get.status_code == 200
    assert r_get.json()["correo"] == correo_unico


def test_reserva_correo_normalizado_y_filtro(api_reservas, correo_unico):
    r = requests.post(
        api_reservas,
        json=payload_reserva(f"  {correo_unico.upper()} ", fecha="2026-12-06"),
        timeout=5,
    )
    assert r.status_code == 201
    assert r.json()["correo"] == correo_unico

    r_list = requests.get(api_reservas, params={"estado": "Confirmada"}, timeout=5)
    assert r_list.status_code == 200
    assert correo_unico in [item["correo"] for item in r_list.json()]


def test_prevencion_sobreventa_mesa_especifica(api_reservas, correo_unico):
    primer = payload_reserva(correo_unico, fecha="2026-12-10", hora="20:00", mesa="M1")
    assert requests.post(api_reservas, json=primer, timeout=5).status_code == 201

    segundo = payload_reserva(f"otro.{correo_unico}", fecha="2026-12-10", hora="20:00", mesa="M1")
    r_dup = requests.post(api_reservas, json=segundo, timeout=5)
    assert r_dup.status_code == 409


@pytest.mark.parametrize("personas, esperado", [(0, 422), (1, 201), (6, 201), (7, 422), ("dos", 422)])
def test_reserva_personas_limites(api_reservas, correo_unico, personas, esperado):
    hora = f"1{personas}:00" if str(personas).isdigit() else "12:00"
    r = requests.post(
        api_reservas,
        json=payload_reserva(correo_unico, fecha="2026-12-11", hora=hora, personas=personas),
        timeout=5,
    )
    assert r.status_code == esperado


@pytest.mark.parametrize(
    "campo, valor",
    [
        ("cliente", "Jo"),
        ("correo", "correo-invalido"),
        ("fecha", "26-11-2026"),
        ("hora", "9am"),
        ("mesa", "M99"),
    ],
)
def test_reserva_datos_invalidos_422(api_reservas, correo_unico, campo, valor):
    datos = payload_reserva(correo_unico)
    datos[campo] = valor
    r = requests.post(api_reservas, json=datos, timeout=5)
    assert r.status_code == 422
    assert campo in r.json()["errores"]


def test_reserva_cuerpo_no_json_y_404(api_reservas):
    r_bad = requests.post(api_reservas, data="texto plano", timeout=5)
    assert r_bad.status_code == 400
    assert requests.get(f"{api_reservas}/99999", timeout=5).status_code == 404
    assert requests.patch(f"{api_reservas}/99999", json={"estado": "Cancelada"}, timeout=5).status_code == 404
    assert requests.delete(f"{api_reservas}/99999", timeout=5).status_code == 404


def test_actualizar_y_eliminar_reserva(api_reservas, correo_unico):
    r = requests.post(api_reservas, json=payload_reserva(correo_unico, fecha="2026-12-12"), timeout=5)
    rid = r.json()["id"]

    r_bad = requests.patch(f"{api_reservas}/{rid}", json={"estado": "Desconocido"}, timeout=5)
    assert r_bad.status_code == 422

    r_ok = requests.patch(f"{api_reservas}/{rid}", json={"estado": "Cancelada"}, timeout=5)
    assert r_ok.status_code == 200
    assert r_ok.json()["estado"] == "Cancelada"

    r_del = requests.delete(f"{api_reservas}/{rid}", timeout=5)
    assert r_del.status_code == 204
    assert requests.get(f"{api_reservas}/{rid}", timeout=5).status_code == 404


def test_crear_y_transicionar_pedido(api_pedidos):
    pedido = {
        "cliente": "Carlos Mendez",
        "tipo": "domicilio",
        "items": [{"plato": "hamburguesa", "cantidad": 2}, {"plato": "limonada", "cantidad": 1}],
    }
    r = requests.post(api_pedidos, json=pedido, timeout=5)
    assert r.status_code == 201
    creado = r.json()
    assert creado["codigo"].startswith("PED-")
    assert creado["total"] == 67000
    assert creado["estado"] == "Recibido"

    r_patch = requests.patch(f"{api_pedidos}/{creado['id']}", json={"estado": "En preparacion"}, timeout=5)
    assert r_patch.status_code == 200
    assert r_patch.json()["estado"] == "En preparacion"

    r_list = requests.get(api_pedidos, timeout=5)
    assert r_list.status_code == 200
    assert any(p["codigo"] == creado["codigo"] for p in r_list.json())


def test_pedido_validaciones_errores(api_pedidos):
    assert requests.post(api_pedidos, data="no json", timeout=5).status_code == 400
    bad = {"cliente": "A", "tipo": "avion", "items": []}
    r = requests.post(api_pedidos, json=bad, timeout=5)
    assert r.status_code == 422
    assert {"cliente", "tipo", "items"} <= set(r.json()["errores"])

    bad_plato = {"cliente": "Pedro", "tipo": "mesa", "items": [{"plato": "sopa", "cantidad": 1}]}
    assert requests.post(api_pedidos, json=bad_plato, timeout=5).status_code == 422

    bad_cant = {"cliente": "Pedro", "tipo": "mesa", "items": [{"plato": "pasta", "cantidad": 0}]}
    assert requests.post(api_pedidos, json=bad_cant, timeout=5).status_code == 422

    assert requests.patch(f"{api_pedidos}/99999", json={"estado": "Listo"}, timeout=5).status_code == 404
