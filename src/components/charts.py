import pandas as pd
import plotly.graph_objects as go


def _preparar_tendencias(df):
    """Prepara registros historicos validos para las graficas de tendencias."""
    if df is None or df.empty:
        return pd.DataFrame()

    requerido = {"PERIODO", "DEFINITIVA_ALMACENADA"}
    if not requerido.issubset(df.columns):
        return pd.DataFrame()

    trabajo = df.copy()
    if "CALIDAD_CIERRE" in trabajo.columns:
        trabajo = trabajo[
            ~trabajo["CALIDAD_CIERRE"].astype(str).str.upper().str.contains(
                "PERIODO_EN_CURSO_NO_FINAL", na=False
            )
        ].copy()
    if "TIPO_REGISTRO" in trabajo.columns:
        trabajo = trabajo[trabajo["TIPO_REGISTRO"] == "CON_BOLETIN"].copy()

    trabajo["DEFINITIVA_ALMACENADA"] = pd.to_numeric(
        trabajo["DEFINITIVA_ALMACENADA"], errors="coerce"
    )
    trabajo["PERIODO"] = trabajo["PERIODO"].astype(str).str.strip()
    trabajo = trabajo.dropna(subset=["PERIODO", "DEFINITIVA_ALMACENADA"]).copy()
    return trabajo


def _ordenar_periodos(periodos):
    return sorted(periodos, key=_clave_periodo)


def _clave_periodo(periodo):
    texto = str(periodo).strip()
    try:
        anio, semestre = texto.split("-", 1)
        return int(anio), int(semestre)
    except (ValueError, TypeError):
        return 9999, 9999


def _agrupar_tendencia(grupo):
    """Calcula promedio y cantidad de estudiantes por periodo."""
    agregaciones = {"promedio": ("DEFINITIVA_ALMACENADA", "mean")}
    if "ID_ESTUDIANTE" in grupo.columns:
        agregaciones["estudiantes"] = ("ID_ESTUDIANTE", "nunique")
    else:
        agregaciones["estudiantes"] = ("DEFINITIVA_ALMACENADA", "size")
    return grupo.groupby("PERIODO").agg(**agregaciones)


def _preparar_promedios_acumulados(trabajo):
    """Calcula el promedio historico acumulado de cada estudiante por periodo."""
    if "ID_ESTUDIANTE" not in trabajo.columns:
        return pd.DataFrame()

    periodos = _ordenar_periodos(trabajo["PERIODO"].unique())
    registros = []
    for periodo in periodos:
        historico = trabajo[
            trabajo["PERIODO"].map(
                lambda valor: _clave_periodo(valor) <= _clave_periodo(periodo)
            )
        ]
        acumulados = (
            historico.groupby("ID_ESTUDIANTE")["DEFINITIVA_ALMACENADA"]
            .mean()
            .rename("promedio_acumulado")
        )
        evaluados = trabajo[trabajo["PERIODO"] == periodo][
            ["ID_ESTUDIANTE"]
        ].drop_duplicates()
        evaluados = evaluados.merge(
            acumulados,
            left_on="ID_ESTUDIANTE",
            right_index=True,
            how="inner",
        )
        evaluados["PERIODO"] = periodo
        registros.append(evaluados)

    if not registros:
        return pd.DataFrame()
    return pd.concat(registros, ignore_index=True)


def graficar_tendencia_promedios(df, periodos_visibles=None):
    """Muestra promedios acumulados generales, aprobados y reprobados."""
    trabajo = _preparar_tendencias(df)
    fig = go.Figure()
    estudiantes = _preparar_promedios_acumulados(trabajo)
    if estudiantes.empty:
        fig.update_layout(
            title="Tendencia de promedios - Sin datos disponibles",
            height=650,
        )
        return fig

    periodos = _ordenar_periodos(estudiantes["PERIODO"].unique())
    if periodos_visibles is not None:
        periodos = [
            periodo for periodo in _ordenar_periodos(periodos_visibles)
            if periodo in periodos
        ]
        estudiantes = estudiantes[estudiantes["PERIODO"].isin(periodos)]
    if not periodos or estudiantes.empty:
        fig.update_layout(
            title="Tendencia de promedios - Sin datos disponibles",
            height=650,
        )
        return fig
    series = [
        ("Promedio general", estudiantes, "#1f77b4"),
        (
            "Promedio acumulado >= 3.0",
            estudiantes[estudiantes["promedio_acumulado"] >= 3.0],
            "#2ca02c",
        ),
        (
            "Promedio acumulado < 3.0",
            estudiantes[estudiantes["promedio_acumulado"] < 3.0],
            "#d62728",
        ),
    ]

    for nombre, grupo, color in series:
        agrupado = grupo.groupby("PERIODO").agg(
            promedio=("promedio_acumulado", "mean"),
            estudiantes=("ID_ESTUDIANTE", "nunique"),
        )
        promedios = agrupado.reindex(periodos)
        valores = promedios["promedio"].round(2)
        conteos = promedios["estudiantes"].fillna(0).astype(int)
        fig.add_trace(
            go.Scatter(
                name=nombre,
                x=periodos,
                y=valores,
                mode="lines+markers+text",
                text=[f"{valor:.2f}" if pd.notna(valor) else "" for valor in valores],
                textposition="top center",
                customdata=conteos,
                line=dict(color=color, width=3),
                marker=dict(size=9),
                connectgaps=False,
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "Estudiantes evaluados: %{customdata}<br>"
                    "Promedio acumulado: %{y:.2f}<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title="Tendencia de promedios por periodo",
        xaxis=dict(
            type="category",
            categoryorder="array",
            categoryarray=periodos,
            title="Periodo academico",
        ),
        yaxis_title="Promedio acumulado historico (0.0 - 5.0)",
        yaxis=dict(range=[0, 5]),
        hovermode="x unified",
        height=650,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


def graficar_tendencia_cantidades(df, periodos_visibles=None):
    """Muestra aprobados y reprobados por materia y periodo."""
    trabajo = _preparar_tendencias(df)
    if trabajo.empty:
        fig = go.Figure()
        fig.update_layout(title="Tendencia de cantidades - Sin datos disponibles")
        return fig

    periodos = _ordenar_periodos(trabajo["PERIODO"].dropna().unique())
    if periodos_visibles is not None:
        periodos = [
            periodo for periodo in _ordenar_periodos(periodos_visibles)
            if periodo in periodos
        ]
        trabajo = trabajo[trabajo["PERIODO"].isin(periodos)]
    if not periodos or trabajo.empty:
        fig.update_layout(title="Tendencia de cantidades - Sin datos disponibles")
        return fig
    fig = go.Figure()

    for nombre, condicion, color in (
        ("Aprobados", trabajo["DEFINITIVA_ALMACENADA"] >= 3.0, "#2ca02c"),
        ("Reprobados", trabajo["DEFINITIVA_ALMACENADA"] < 3.0, "#d62728"),
    ):
        grupo = trabajo[condicion]
        columna_conteo = (
            "ID_ESTUDIANTE"
            if "ID_ESTUDIANTE" in grupo.columns
            else "DEFINITIVA_ALMACENADA"
        )
        agrupado = grupo.groupby("PERIODO").agg(
            cantidad=(columna_conteo, "nunique" if "ID_ESTUDIANTE" in grupo.columns else "size"),
            promedio=("DEFINITIVA_ALMACENADA", "mean"),
        ).reindex(periodos)
        conteos = agrupado["cantidad"].fillna(0).astype(int)
        promedios = agrupado["promedio"].round(2)
        customdata = list(zip(conteos, promedios))
        fig.add_trace(
            go.Scatter(
                name=nombre,
                x=periodos,
                y=conteos,
                mode="lines+markers+text",
                text=conteos.astype(str),
                textposition="top center",
                customdata=customdata,
                line=dict(color=color, width=3),
                marker=dict(size=9),
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "Estudiantes: %{customdata[0]}<br>"
                    "Promedio nota definitiva: %{customdata[1]:.2f}"
                    "<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title="Tendencia de aprobados y reprobados por periodo",
        xaxis=dict(
            type="category",
            categoryorder="array",
            categoryarray=periodos,
            title="Periodo academico",
        ),
        yaxis_title="Cantidad de estudiantes",
        hovermode="x unified",
        height=650,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig
