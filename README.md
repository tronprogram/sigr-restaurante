# SIGR Restaurante — Pipeline CI/CD (Jenkins + Docker + SonarQube + Selenium)

Aplicación web y API REST en Python + Flask para el **Sistema Integral de Gestión de Restaurante (SIGR)**: consulta de disponibilidad de mesas, reservas con control de sobreventa y pedidos en línea, integrada con un pipeline declarativo de **12 etapas** en Jenkins.

## Arquitectura del Pipeline

1. **Checkout**: descarga de código desde GitHub y extracción de versión semántica (`app.__version__`).
2. **Preparar entorno**: entorno virtual aislado e instalación reproducible de dependencias.
3. **Calidad de código (en paralelo)**: `flake8` (estilo PEP 8) y `bandit` (análisis estático de seguridad).
4. **Pruebas de API**: batería automatizada con `pytest` y cobertura mínima del 80 %.
5. **Construir imagen**: empaquetado inmutable en Docker (`Dockerfile` con `gunicorn`).
6. **Ambiente de pruebas**: despliegue temporal en red Docker `ci` con verificación de `/api/salud`.
7. **Pruebas de interfaz y E2E**: flujos Selenium Grid sobre la imagen real construida.
8. **SonarQube y Quality Gate**: envío de métricas y cobertura; bloqueo automático ante fallos.
9. **Desplegar a staging**: publicación automática en `http://localhost:8001`.
10. **Aprobación manual**: compuerta interactiva (`input`) para control de cambios.
11. **Desplegar a producción**: promoción de la imagen validada a `http://localhost:8000`.
12. **Release**: etiquetado automático `vX.Y.Z` y push a GitHub.

## Ejecución local rápida

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python -m pytest -m api -v --cov=app
python -m pytest -m "ui or e2e" -v
```
