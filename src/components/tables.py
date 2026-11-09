"""Configuracion y estilos reutilizables para tablas del dashboard."""


def colorear_riesgo(fila):
    nota_necesaria = fila.get("Necesita examen final", 0)
    if nota_necesaria > 5.0:
        fondo = "#fecaca"
    elif nota_necesaria >= 4.0:
        fondo = "#fed7aa"
    else:
        fondo = "#fef3c7"
    return [f"background-color: {fondo}; color: #111827"] * len(fila)
