import pandas as pd
import plotly.graph_objects as go
from src.constants import NOTA_MINIMA_APROBACION
from src.services.periods import clave_periodo_academico


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
    return clave_periodo_academico(periodo)


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


def _graficar_tendencia_asignatura(
    trabajo,
    asignatura,
    periodos_visibles,
):
    """Muestra la tendencia de una asignatura por grupos acumulados."""
    materia = trabajo[trabajo["ASIGNATURA"] == asignatura].copy()
    if materia.empty or "ID_ESTUDIANTE" not in trabajo.columns:
        return go.Figure(layout={"title": "Sin datos disponibles"})

    periodos = _ordenar_periodos(materia["PERIODO"].unique())
    if periodos_visibles is not None:
        periodos = [
            periodo for periodo in _ordenar_periodos(periodos_visibles)
            if periodo in periodos
        ]
        materia = materia[materia["PERIODO"].isin(periodos)]
    if not periodos or materia.empty:
        return go.Figure(layout={"title": "Sin datos disponibles"})

    acumulados = _preparar_promedios_acumulados(trabajo)
    acumulados = acumulados.rename(columns={"promedio_acumulado": "acumulado"})
    evaluaciones = (
        materia.groupby(["PERIODO", "ID_ESTUDIANTE"])["DEFINITIVA_ALMACENADA"]
        .mean()
        .rename("nota_materia")
        .reset_index()
        .merge(
            acumulados[["PERIODO", "ID_ESTUDIANTE", "acumulado"]],
            on=["PERIODO", "ID_ESTUDIANTE"],
            how="inner",
        )
    )
    series = [
        ("Promedio materia", evaluaciones, "#1f77b4"),
        (
            f"Acumulado >= {NOTA_MINIMA_APROBACION:.1f}",
            evaluaciones[evaluaciones["acumulado"] >= NOTA_MINIMA_APROBACION],
            "#2ca02c",
        ),
        (
            f"Acumulado < {NOTA_MINIMA_APROBACION:.1f}",
            evaluaciones[evaluaciones["acumulado"] < NOTA_MINIMA_APROBACION],
            "#d62728",
        ),
    ]
    fig = go.Figure()
    for nombre, grupo, color in series:
        agrupado = grupo.groupby("PERIODO").agg(
            promedio=("nota_materia", "mean"),
            estudiantes=("ID_ESTUDIANTE", "nunique"),
        ).reindex(periodos)
        valores = agrupado["promedio"].round(2)
        conteos = agrupado["estudiantes"].fillna(0).astype(int)
        fig.add_trace(
            go.Scatter(
                name=nombre,
                x=periodos,
                y=valores,
                mode="lines+markers+text",
                text=[
                    f"{valor:.2f}" if pd.notna(valor) else ""
                    for valor in valores
                ],
                textposition="top center",
                customdata=conteos,
                line=dict(color=color, width=3),
                marker=dict(size=9),
                connectgaps=False,
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "Estudiantes: %{customdata}<br>"
                    "Promedio nota definitiva: %{y:.2f}<extra></extra>"
                ),
            )
        )
    fig.update_layout(
        title=f"Tendencia de {asignatura} por periodo",
        xaxis=dict(
            type="category",
            categoryorder="array",
            categoryarray=periodos,
            title="Periodo academico",
        ),
        yaxis=dict(
            range=[0, 5],
            title="Promedio de nota definitiva",
        ),
        hovermode="x unified",
        height=650,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


def graficar_tendencia_promedios(df, periodos_visibles=None):
    """Muestra siempre el promedio acumulado historico general."""
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
            f"Promedio acumulado >= {NOTA_MINIMA_APROBACION:.1f}",
            estudiantes[
                estudiantes["promedio_acumulado"] >= NOTA_MINIMA_APROBACION
            ],
            "#2ca02c",
        ),
        (
            f"Promedio acumulado < {NOTA_MINIMA_APROBACION:.1f}",
            estudiantes[
                estudiantes["promedio_acumulado"] < NOTA_MINIMA_APROBACION
            ],
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


def graficar_tendencia_promedio_materia(df, asignatura, periodos_visibles=None):
    """Muestra promedio general, aprobados y reprobados de una materia."""
    trabajo = _preparar_tendencias(df)
    fig = go.Figure()
    if trabajo.empty or not asignatura or asignatura == "Todas":
        fig.update_layout(
            title="Tendencia de la materia - Seleccione una asignatura",
            height=650,
        )
        return fig

    trabajo = trabajo[
        trabajo["ASIGNATURA"].astype(str).str.strip() == asignatura
    ].copy()
    if periodos_visibles is not None:
        periodos = [
            periodo for periodo in _ordenar_periodos(periodos_visibles)
            if periodo in trabajo["PERIODO"].unique()
        ]
        trabajo = trabajo[trabajo["PERIODO"].isin(periodos)]
    else:
        periodos = _ordenar_periodos(trabajo["PERIODO"].unique())

    if trabajo.empty or not periodos:
        fig.update_layout(
            title=f"{asignatura} - Sin datos disponibles",
            height=650,
        )
        return fig

    series = [
        ("Promedio general de la materia", trabajo, "#1f77b4"),
        (
            "Promedio de aprobados",
            trabajo[
                trabajo["DEFINITIVA_ALMACENADA"] >= NOTA_MINIMA_APROBACION
            ],
            "#2ca02c",
        ),
        (
            "Promedio de reprobados",
            trabajo[
                trabajo["DEFINITIVA_ALMACENADA"] < NOTA_MINIMA_APROBACION
            ],
            "#d62728",
        ),
    ]
    for nombre, grupo, color in series:
        agregaciones = {"promedio": ("DEFINITIVA_ALMACENADA", "mean")}
        if "ID_ESTUDIANTE" in grupo.columns:
            agregaciones["estudiantes"] = ("ID_ESTUDIANTE", "nunique")
        else:
            agregaciones["estudiantes"] = (
                "DEFINITIVA_ALMACENADA",
                "size",
            )
        agrupado = grupo.groupby("PERIODO").agg(**agregaciones).reindex(periodos)
        valores = agrupado["promedio"].round(2)
        conteos = agrupado["estudiantes"].fillna(0).astype(int)
        fig.add_trace(
            go.Scatter(
                name=nombre,
                x=periodos,
                y=valores,
                mode="lines+markers+text",
                text=[
                    f"{valor:.2f}" if pd.notna(valor) else ""
                    for valor in valores
                ],
                textposition="top center",
                customdata=conteos,
                line=dict(color=color, width=3),
                marker=dict(size=9),
                connectgaps=False,
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "Estudiantes: %{customdata}<br>"
                    "Promedio nota definitiva: %{y:.2f}<extra></extra>"
                ),
            )
        )
    fig.update_layout(
        title=f"Promedio de {asignatura} por periodo",
        xaxis=dict(
            type="category",
            categoryorder="array",
            categoryarray=periodos,
            title="Periodo academico",
        ),
        yaxis=dict(range=[0, 5], title="Promedio de nota definitiva"),
        hovermode="x unified",
        height=650,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


def graficar_reprobados_por_corte(df, asignatura, periodos_seleccionados):
    """Compara reprobados y su nota media en cada corte por periodo."""
    trabajo = _preparar_tendencias(df)
    fig = go.Figure()
    cortes = [
        ("Primer corte", "PRIMER_PARCIAL"),
        ("Segundo corte", "SEGUNDO_PARCIAL"),
        ("Examen final", "EXAMEN_FINAL"),
    ]
    requeridas = {"ASIGNATURA", "ID_ESTUDIANTE"}
    if trabajo.empty or not requeridas.issubset(trabajo.columns):
        fig.update_layout(title="Reprobacion por corte - Sin datos disponibles")
        return fig

    trabajo = trabajo[
        trabajo["ASIGNATURA"].astype(str).str.strip() == str(asignatura).strip()
    ].copy()
    periodos = [
        periodo for periodo in _ordenar_periodos(periodos_seleccionados or [])
        if periodo in set(trabajo["PERIODO"])
    ]
    if trabajo.empty or not periodos:
        fig.update_layout(
            title=f"Reprobacion por corte de {asignatura} - Sin datos disponibles"
        )
        return fig

    colores = ["#2563eb", "#dc2626", "#16a34a", "#7c3aed", "#0891b2"]
    for indice, periodo in enumerate(periodos):
        periodo_df = trabajo[trabajo["PERIODO"] == periodo]
        valores = []
        promedios = []
        for _, columna in cortes:
            notas = periodo_df[["ID_ESTUDIANTE", columna]].copy()
            notas[columna] = pd.to_numeric(notas[columna], errors="coerce")
            notas = notas.dropna(subset=[columna])
            notas = notas.groupby("ID_ESTUDIANTE", as_index=False)[columna].mean()
            reprobados = notas[notas[columna] < NOTA_MINIMA_APROBACION]
            valores.append(len(reprobados))
            promedios.append(
                reprobados[columna].mean() if not reprobados.empty else None
            )
        fig.add_trace(
            go.Scatter(
                name=str(periodo),
                x=[nombre for nombre, _ in cortes],
                y=valores,
                mode="lines+markers+text",
                text=[str(valor) for valor in valores],
                textposition="top center",
                customdata=[
                    [promedio if promedio is not None else float("nan")]
                    for promedio in promedios
                ],
                line=dict(color=colores[indice % len(colores)], width=3),
                marker=dict(size=9),
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    f"Periodo: {periodo}<br>"
                    "Estudiantes reprobados: %{y}<br>"
                    "Promedio de sus notas: %{customdata[0]:.2f}"
                    "<extra></extra>"
                ),
            )
        )
    fig.update_layout(
        title=f"Reprobados por corte - {asignatura}",
        xaxis=dict(type="category", title="Corte academico"),
        yaxis=dict(title="Cantidad de estudiantes reprobados", rangemode="tozero"),
        hovermode="x unified",
        height=650,
        legend=dict(title="Periodo academico"),
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
        (
            "Aprobados",
            trabajo["DEFINITIVA_ALMACENADA"] >= NOTA_MINIMA_APROBACION,
            "#2ca02c",
        ),
        (
            "Reprobados",
            trabajo["DEFINITIVA_ALMACENADA"] < NOTA_MINIMA_APROBACION,
            "#d62728",
        ),
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


def graficar_mapa_reprobacion(df, semestres_curriculares=None):
    """Muestra el porcentaje de reprobacion por asignatura y periodo."""
    trabajo = _preparar_tendencias(df)
    requerido = {"ASIGNATURA", "ID_ESTUDIANTE"}
    fig = go.Figure()
    if trabajo.empty or not requerido.issubset(trabajo.columns):
        fig.update_layout(
            title="Mapa de reprobacion - Sin datos disponibles",
            height=650,
        )
        return fig

    trabajo["ASIGNATURA"] = trabajo["ASIGNATURA"].astype(str).str.strip()
    trabajo = trabajo[~trabajo["ASIGNATURA"].isin(["", "nan"])].copy()
    if semestres_curriculares is not None and "SEMESTRE_ASIGNATURA" in trabajo.columns:
        trabajo["SEMESTRE_ASIGNATURA"] = (
            trabajo["SEMESTRE_ASIGNATURA"].astype(str).str.strip()
        )
        trabajo = trabajo[
            trabajo["SEMESTRE_ASIGNATURA"].isin(semestres_curriculares)
        ].copy()
    if trabajo.empty:
        fig.update_layout(
            title="Mapa de reprobacion - Sin datos disponibles",
            height=650,
        )
        return fig

    trabajo["ID_REPROBADO"] = trabajo["ID_ESTUDIANTE"].where(
        trabajo["DEFINITIVA_ALMACENADA"] < NOTA_MINIMA_APROBACION
    )
    resumen = (
        trabajo.groupby(["ASIGNATURA", "PERIODO"])
        .agg(
            evaluados=("ID_ESTUDIANTE", "nunique"),
            reprobados=("ID_REPROBADO", "nunique"),
            promedio=("DEFINITIVA_ALMACENADA", "mean"),
        )
        .reset_index()
    )
    resumen["porcentaje_reprobacion"] = (
        resumen["reprobados"] / resumen["evaluados"] * 100
    ).round(2)

    periodos = _ordenar_periodos(resumen["PERIODO"].unique())
    asignaturas = (
        resumen.groupby("ASIGNATURA")["porcentaje_reprobacion"]
        .mean()
        .sort_values(ascending=False)
        .index.tolist()
    )
    indice = pd.MultiIndex.from_product(
        [asignaturas, periodos],
        names=["ASIGNATURA", "PERIODO"],
    )
    datos = resumen.set_index(["ASIGNATURA", "PERIODO"]).reindex(indice)
    z = datos["porcentaje_reprobacion"].to_numpy().reshape(
        len(asignaturas),
        len(periodos),
    )
    customdata = datos[
        ["evaluados", "reprobados", "promedio"]
    ].fillna(0).to_numpy().reshape(
        len(asignaturas),
        len(periodos),
        3,
    )

    fig.add_trace(
        go.Heatmap(
            x=periodos,
            y=asignaturas,
            z=z,
            customdata=customdata,
            colorscale=[
                [0.0, "#16a34a"],
                [0.2, "#86efac"],
                [0.4, "#facc15"],
                [0.6, "#f97316"],
                [1.0, "#dc2626"],
            ],
            zmin=0,
            zmax=100,
            colorbar=dict(title="% reprobacion"),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Periodo: %{x}<br>"
                "Reprobacion: %{z:.2f}%<br>"
                "Reprobados: %{customdata[1]:.0f}<br>"
                "Evaluados: %{customdata[0]:.0f}<br>"
                "Promedio definitivo: %{customdata[2]:.2f}"
                "<extra></extra>"
            ),
            hoverongaps=False,
        )
    )
    fig.update_layout(
        title="Mapa de reprobacion por materia y periodo",
        xaxis=dict(
            type="category",
            categoryorder="array",
            categoryarray=periodos,
            title="Periodo academico",
        ),
        yaxis=dict(
            type="category",
            categoryorder="array",
            categoryarray=asignaturas,
            title="Asignatura",
        ),
        height=max(650, 32 * len(asignaturas) + 180),
        margin=dict(l=260, r=80, t=80, b=100),
    )
    return fig
