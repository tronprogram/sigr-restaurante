"""
SIGR - Sistema Integral de Gestion de Restaurante (Modulo Reservas y Pedidos).

  - API REST   /api/mesas, /api/reservas, /api/menu, /api/pedidos
  - Salud      /api/salud (estado, servicio, version y ambiente)
  - Web        /reservas y /pedidos
"""
import os
import re

from flask import Flask, jsonify, redirect, render_template, request, url_for

from app import __version__

PATRON_CORREO = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PATRON_FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PATRON_HORA = re.compile(r"^\d{2}:\d{2}$")

MESAS_BASE = [
    {"id": "M1", "capacidad": 2},
    {"id": "M2", "capacidad": 2},
    {"id": "M3", "capacidad": 4},
    {"id": "M4", "capacidad": 4},
    {"id": "M5", "capacidad": 6},
    {"id": "M6", "capacidad": 6},
]

MENU = {
    "pasta": {"nombre": "Pasta Alfredo", "precio": 32000},
    "hamburguesa": {"nombre": "Hamburguesa SIGR", "precio": 28000},
    "ensalada": {"nombre": "Ensalada Cesar", "precio": 24000},
    "limonada": {"nombre": "Limonada de Coco", "precio": 11000},
}

ESTADOS_PEDIDO = ["Recibido", "En preparacion", "Listo", "Entregado"]
ESTADOS_RESERVA = ["Confirmada", "Cancelada", "Completada"]


def crear_app():
    app = Flask(__name__)
    app.json.ensure_ascii = False
    reservas = {}
    pedidos = {}
    contadores = {"reserva": 0, "pedido": 0}
    ambiente = os.environ.get("AMBIENTE", "local")

    def mesas_ocupadas(fecha, hora):
        return {
            r["mesa"]
            for r in reservas.values()
            if r["fecha"] == fecha and r["hora"] == hora and r["estado"] == "Confirmada"
        }

    def asignar_mesa(personas, fecha, hora, mesa_solicitada=None):
        ocupadas = mesas_ocupadas(fecha, hora)
        if mesa_solicitada:
            mesa_obj = next((m for m in MESAS_BASE if m["id"] == mesa_solicitada), None)
            if not mesa_obj or mesa_obj["capacidad"] < personas or mesa_solicitada in ocupadas:
                return None
            return mesa_solicitada
        candidatas = sorted(
            (m for m in MESAS_BASE if m["capacidad"] >= personas and m["id"] not in ocupadas),
            key=lambda m: m["capacidad"],
        )
        return candidatas[0]["id"] if candidatas else None

    def validar_reserva(datos):
        errores = {}
        cliente = str(datos.get("cliente") or "").strip()
        correo = str(datos.get("correo") or "").strip().lower()
        fecha = str(datos.get("fecha") or "").strip()
        hora = str(datos.get("hora") or "").strip()
        mesa_pref = str(datos.get("mesa") or "").strip().upper() or None
        personas = datos.get("personas")

        if len(cliente) < 3:
            errores["cliente"] = "El nombre debe tener al menos 3 caracteres"
        if not PATRON_CORREO.match(correo):
            errores["correo"] = "Correo invalido"
        if not PATRON_FECHA.match(fecha):
            errores["fecha"] = "Formato de fecha invalido (YYYY-MM-DD)"
        if not PATRON_HORA.match(hora):
            errores["hora"] = "Formato de hora invalido (HH:MM)"
        try:
            if isinstance(personas, bool):
                raise ValueError
            personas = int(personas)
            if not 1 <= personas <= 6:
                raise ValueError
        except (TypeError, ValueError):
            errores["personas"] = "Las personas deben ser entre 1 y 6"

        if mesa_pref and not any(m["id"] == mesa_pref for m in MESAS_BASE):
            errores["mesa"] = "Mesa inexistente"

        limpio = {
            "cliente": cliente,
            "correo": correo,
            "fecha": fecha,
            "hora": hora,
            "personas": personas,
            "mesa_pref": mesa_pref,
        }
        return errores, limpio

    def guardar_reserva(limpio, mesa_asignada):
        contadores["reserva"] += 1
        rid = contadores["reserva"]
        reserva = {
            "id": rid,
            "codigo": f"RES-{rid:04d}",
            "cliente": limpio["cliente"],
            "correo": limpio["correo"],
            "fecha": limpio["fecha"],
            "hora": limpio["hora"],
            "personas": limpio["personas"],
            "mesa": mesa_asignada,
            "estado": "Confirmada",
        }
        reservas[rid] = reserva
        return reserva

    def validar_pedido(datos):
        errores = {}
        cliente = str(datos.get("cliente") or "").strip()
        tipo = str(datos.get("tipo") or "").strip().lower()
        items_raw = datos.get("items")

        if len(cliente) < 3:
            errores["cliente"] = "El cliente debe tener al menos 3 caracteres"
        if tipo not in {"mesa", "domicilio"}:
            errores["tipo"] = "Tipo debe ser mesa o domicilio"

        items_limpios = []
        total = 0
        if not isinstance(items_raw, list) or not items_raw:
            errores["items"] = "Debe incluir al menos un plato"
        else:
            for item in items_raw:
                plato = str((item or {}).get("plato") or "").strip().lower()
                try:
                    cant = int((item or {}).get("cantidad"))
                    if cant < 1 or cant > 20:
                        raise ValueError
                except (TypeError, ValueError):
                    errores["items"] = "Cantidad invalida (1-20)"
                    break
                if plato not in MENU:
                    errores["items"] = f"Plato desconocido: {plato}"
                    break
                subtotal = MENU[plato]["precio"] * cant
                total += subtotal
                items_limpios.append({
                    "plato": plato,
                    "nombre": MENU[plato]["nombre"],
                    "cantidad": cant,
                    "subtotal": subtotal,
                })

        return errores, {"cliente": cliente, "tipo": tipo, "items": items_limpios, "total": total}

    def guardar_pedido(limpio):
        contadores["pedido"] += 1
        pid = contadores["pedido"]
        pedido = {"id": pid, "codigo": f"PED-{pid:04d}", **limpio, "estado": "Recibido"}
        pedidos[pid] = pedido
        return pedido

    @app.context_processor
    def datos_globales():
        return {"version": __version__, "ambiente": ambiente}

    @app.get("/api/salud")
    def salud():
        return jsonify({
            "estado": "ok",
            "servicio": "sigr-restaurante",
            "version": __version__,
            "ambiente": ambiente,
        }), 200

    @app.get("/api/mesas")
    def listar_mesas():
        fecha = request.args.get("fecha", "")
        hora = request.args.get("hora", "")
        ocupadas = mesas_ocupadas(fecha, hora) if fecha and hora else set()
        resultado = [
            {**m, "disponible": m["id"] not in ocupadas} for m in MESAS_BASE
        ]
        return jsonify(resultado), 200

    @app.get("/api/reservas")
    def listar_reservas():
        estado = request.args.get("estado")
        datos = [r for r in reservas.values() if not estado or r["estado"] == estado]
        return jsonify(datos), 200

    @app.get("/api/reservas/<int:rid>")
    def obtener_reserva(rid):
        reserva = reservas.get(rid)
        if not reserva:
            return jsonify({"error": "Reserva no encontrada"}), 404
        return jsonify(reserva), 200

    @app.post("/api/reservas")
    def crear_reserva():
        datos = request.get_json(silent=True)
        if not isinstance(datos, dict):
            return jsonify({"error": "Se requiere cuerpo JSON"}), 400
        errores, limpio = validar_reserva(datos)
        if errores:
            return jsonify({"errores": errores}), 422
        mesa = asignar_mesa(
            limpio["personas"], limpio["fecha"], limpio["hora"], limpio["mesa_pref"]
        )
        if not mesa:
            return jsonify({
                "errores": {"mesa": "No hay mesas disponibles para ese horario y capacidad"}
            }), 409
        return jsonify(guardar_reserva(limpio, mesa)), 201

    @app.patch("/api/reservas/<int:rid>")
    def actualizar_reserva(rid):
        reserva = reservas.get(rid)
        if not reserva:
            return jsonify({"error": "Reserva no encontrada"}), 404
        datos = request.get_json(silent=True) or {}
        nuevo_estado = str(datos.get("estado") or "").strip()
        if nuevo_estado not in ESTADOS_RESERVA:
            return jsonify({"errores": {"estado": "Estado no valido"}}), 422
        reserva["estado"] = nuevo_estado
        return jsonify(reserva), 200

    @app.delete("/api/reservas/<int:rid>")
    def eliminar_reserva(rid):
        if rid not in reservas:
            return jsonify({"error": "Reserva no encontrada"}), 404
        del reservas[rid]
        return "", 204

    @app.get("/api/menu")
    def ver_menu():
        return jsonify(MENU), 200

    @app.get("/api/pedidos")
    def listar_pedidos():
        return jsonify(list(pedidos.values())), 200

    @app.post("/api/pedidos")
    def crear_pedido():
        datos = request.get_json(silent=True)
        if not isinstance(datos, dict):
            return jsonify({"error": "Se requiere cuerpo JSON"}), 400
        errores, limpio = validar_pedido(datos)
        if errores:
            return jsonify({"errores": errores}), 422
        return jsonify(guardar_pedido(limpio)), 201

    @app.patch("/api/pedidos/<int:pid>")
    def avanzar_pedido(pid):
        pedido = pedidos.get(pid)
        if not pedido:
            return jsonify({"error": "Pedido no encontrado"}), 404
        datos = request.get_json(silent=True) or {}
        estado = str(datos.get("estado") or "").strip()
        if estado not in ESTADOS_PEDIDO:
            return jsonify({"errores": {"estado": "Estado de pedido invalido"}}), 422
        pedido["estado"] = estado
        return jsonify(pedido), 200

    # ------------------------- VISTAS WEB -------------------------
    @app.get("/")
    def inicio():
        return redirect(url_for("vista_reservas"))

    @app.route("/reservas", methods=["GET", "POST"])
    def vista_reservas():
        errores = {}
        confirmacion = None
        valores = {"cliente": "", "correo": "", "fecha": "2026-11-26", "hora": "19:00", "personas": "2"}
        if request.method == "POST":
            valores = {
                "cliente": request.form.get("cliente", ""),
                "correo": request.form.get("correo", ""),
                "fecha": request.form.get("fecha", ""),
                "hora": request.form.get("hora", ""),
                "personas": request.form.get("personas", ""),
            }
            errores, limpio = validar_reserva(valores)
            if not errores:
                mesa = asignar_mesa(limpio["personas"], limpio["fecha"], limpio["hora"])
                if not mesa:
                    errores["mesa"] = "No hay mesas disponibles para ese horario"
                else:
                    confirmacion = guardar_reserva(limpio, mesa)
        lista = sorted(reservas.values(), key=lambda r: r["id"], reverse=True)
        return render_template(
            "reservas.html", errores=errores, confirmacion=confirmacion, valores=valores, reservas=lista
        )

    @app.route("/pedidos", methods=["GET", "POST"])
    def vista_pedidos():
        errores = {}
        confirmacion = None
        valores = {"cliente": "", "tipo": "mesa", "plato": "hamburguesa", "cantidad": "1"}
        if request.method == "POST":
            valores = {
                "cliente": request.form.get("cliente", ""),
                "tipo": request.form.get("tipo", ""),
                "plato": request.form.get("plato", ""),
                "cantidad": request.form.get("cantidad", "1"),
            }
            payload = {
                "cliente": valores["cliente"],
                "tipo": valores["tipo"],
                "items": [{"plato": valores["plato"], "cantidad": valores["cantidad"]}],
            }
            errores, limpio = validar_pedido(payload)
            if not errores:
                confirmacion = guardar_pedido(limpio)
        lista = sorted(pedidos.values(), key=lambda p: p["id"], reverse=True)
        return render_template(
            "pedidos.html",
            errores=errores,
            confirmacion=confirmacion,
            valores=valores,
            menu=MENU,
            pedidos=lista,
        )

    return app


if __name__ == "__main__":
    crear_app().run(host="127.0.0.1", port=5000, debug=False)
