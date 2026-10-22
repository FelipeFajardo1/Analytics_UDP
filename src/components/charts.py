import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np


COLORES_INSTITUCIONALES = {
    'azul': '#1f77b4',
    'rojo': '#d62728',
    'verde': '#2ca02c',
    'naranja': '#ff7f0e',
    'morado': '#9467bd',
    'cafe': '#8c564b'
}


def graficar_evolucion_historica(df):
    """
    Gráfico combinado. Barras apiladas 100% (Aprobó/Perdió) y una línea 
    superpuesta para el Promedio y Mediana a lo largo del 'PERIODO'.
    """
    if df is None or df.empty:
        fig = go.Figure()
        fig.update_layout(title="Evolución Histórica - Sin datos disponibles")
        return fig
    
    df_trabajo = df.copy()
    
    # Filtrar periodos históricos
    if 'CALIDAD_CIERRE' in df_trabajo.columns:
        df_trabajo = df_trabajo[
            ~df_trabajo['CALIDAD_CIERRE'].astype(str).str.upper().str.contains('PERIODO_EN_CURSO_NO_FINAL', na=False)
        ].copy()
    
    # Filtrar CON_BOLETIN
    if 'TIPO_REGISTRO' in df_trabajo.columns:
        df_trabajo = df_trabajo[df_trabajo['TIPO_REGISTRO'] == 'CON_BOLETIN'].copy()
    
    if df_trabajo.empty or 'PERIODO' not in df_trabajo.columns:
        fig = go.Figure()
        fig.update_layout(title="Evolución Histórica - Sin datos disponibles")
        return fig
    
    periodos = sorted(df_trabajo['PERIODO'].dropna().unique())
    fig = go.Figure()
    
    aprobados_pct = []
    reprobados_pct = []
    promedios = []
    medianas = []
    
    for periodo in periodos:
        df_p = df_trabajo[df_trabajo['PERIODO'] == periodo]
        total = len(df_p)
        
        if total > 0 and 'ESTADO_MATERIA' in df_p.columns:
            aprob = len(df_p[df_p['ESTADO_MATERIA'].astype(str).str.upper().str.contains('APROBO', na=False)])
            rep = len(df_p[df_p['ESTADO_MATERIA'].astype(str).str.upper().str.contains('PERDIO', na=False)])
            otros = total - aprob - rep
            if aprob + rep > 0:
                aprobados_pct.append((aprob / (aprob + rep)) * 100)
                reprobados_pct.append((rep / (aprob + rep)) * 100)
            else:
                aprobados_pct.append(0)
                reprobados_pct.append(0)
        else:
            aprobados_pct.append(0)
            reprobados_pct.append(0)
        
        if 'DEFINITIVA_ALMACENADA' in df_p.columns:
            notas = df_p['DEFINITIVA_ALMACENADA'].dropna()
            if not notas.empty:
                promedios.append(notas.mean())
                medianas.append(notas.median())
            else:
                promedios.append(np.nan)
                medianas.append(np.nan)
        else:
            promedios.append(np.nan)
            medianas.append(np.nan)
    
    # Barras apiladas 100%
    fig.add_trace(go.Bar(
        name='Aprobó',
        x=periodos,
        y=aprobados_pct,
        marker_color=COLORES_INSTITUCIONALES['verde'],
        text=[f'{x:.1f}%' for x in aprobados_pct],
        textposition='inside'
    ))
    
    fig.add_trace(go.Bar(
        name='Perdió',
        x=periodos,
        y=reprobados_pct,
        marker_color=COLORES_INSTITUCIONALES['rojo'],
        text=[f'{x:.1f}%' for x in reprobados_pct],
        textposition='inside'
    ))
    
    # Líneas superpuestas para promedio y mediana
    fig.add_trace(go.Scatter(
        name='Promedio',
        x=periodos,
        y=promedios,
        mode='lines+markers',
        yaxis='y2',
        line=dict(color=COLORES_INSTITUCIONALES['azul'], width=3),
        marker=dict(size=8)
    ))
    
    fig.add_trace(go.Scatter(
        name='Mediana',
        x=periodos,
        y=medianas,
        mode='lines+markers',
        yaxis='y2',
        line=dict(color=COLORES_INSTITUCIONALES['naranja'], width=3, dash='dash'),
        marker=dict(size=8)
    ))
    
    fig.update_layout(
        title='Evolución Histórica - Aprobación/Reprobación y Promedio',
        barmode='stack',
        xaxis_title='Periodo Académico',
        yaxis_title='% de Estudiantes',
        yaxis=dict(range=[0, 100]),
        yaxis2=dict(
            title='Nota (0.0 - 5.0)',
            overlaying='y',
            side='right',
            range=[0, 5]
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig


def graficar_ranking_causas(df):
    """
    Gráfico de barras horizontales ordenado por % de reprobación,
    dividiendo las barras por causa (Pérdida Activa vs. 'TODOS_EN_CERO_VERIFICAR').
    """
    if df is None or df.empty:
        fig = go.Figure()
        fig.update_layout(title="Ranking de Causas de Reprobación - Sin datos disponibles")
        return fig
    
    df_trabajo = df.copy()
    
    # Filtrar periodos históricos
    if 'CALIDAD_CIERRE' in df_trabajo.columns:
        df_trabajo = df_trabajo[
            ~df_trabajo['CALIDAD_CIERRE'].astype(str).str.upper().str.contains('PERIODO_EN_CURSO_NO_FINAL', na=False)
        ].copy()
    
    if 'TIPO_REGISTRO' in df_trabajo.columns:
        df_trabajo = df_trabajo[df_trabajo['TIPO_REGISTRO'] == 'CON_BOLETIN'].copy()
    
    if df_trabajo.empty or 'ASIGNATURA' not in df_trabajo.columns:
        fig = go.Figure()
        fig.update_layout(title="Ranking de Causas - Sin datos disponibles")
        return fig
    
    resultados = []
    
    for asignatura, grupo in df_trabajo.groupby('ASIGNATURA'):
        reprobados = grupo
        if 'ESTADO_MATERIA' in grupo.columns:
            reprobados = grupo[grupo['ESTADO_MATERIA'].astype(str).str.upper().str.contains('PERDIO', na=False)]
        
        if reprobados.empty:
            continue
        
        total_reprobados = len(reprobados)
        perdida_activa = 0
        cero_verificar = 0
        
        if 'OBSERVACION_NOTAS' in reprobados.columns:
            perdida_activa = len(reprobados[~reprobados['OBSERVACION_NOTAS'].astype(str).str.upper().str.contains('TODOS_EN_CERO_VERIFICAR', na=False)])
            cero_verificar = len(reprobados[reprobados['OBSERVACION_NOTAS'].astype(str).str.upper().str.contains('TODOS_EN_CERO_VERIFICAR', na=False)])
        else:
            perdida_activa = total_reprobados
        
        if 'DEFINITIVA_ALMACENADA' in grupo.columns:
            notas_grp = grupo['DEFINITIVA_ALMACENADA'].dropna()
            if not notas_grp.empty:
                total_inscritos = len(notas_grp)
            else:
                total_inscritos = len(grupo)
        else:
            total_inscritos = len(grupo)
        
        if total_inscritos == 0:
            continue
        
        pct_reprobacion = (total_reprobados / total_inscritos) * 100
        
        resultados.append({
            'ASIGNATURA': str(asignatura)[:50] + '...' if len(str(asignatura)) > 50 else str(asignatura),
            'perdida_activa': perdida_activa,
            'cero_verificar': cero_verificar,
            'pct_reprobacion': pct_reprobacion
        })
    
    if not resultados:
        fig = go.Figure()
        fig.update_layout(title="Ranking de Causas - Sin reprobados")
        return fig
    
    df_res = pd.DataFrame(resultados)
    df_res = df_res.sort_values('pct_reprobacion', ascending=True).tail(15)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Pérdida Activa',
        y=df_res['ASIGNATURA'],
        x=df_res['perdida_activa'],
        orientation='h',
        marker_color=COLORES_INSTITUCIONALES['naranja']
    ))
    
    fig.add_trace(go.Bar(
        name='TODOS_EN_CERO_VERIFICAR',
        y=df_res['ASIGNATURA'],
        x=df_res['cero_verificar'],
        orientation='h',
        marker_color=COLORES_INSTITUCIONALES['rojo']
    ))
    
    fig.update_layout(
        title='Ranking de Causas de Reprobación (Top 15)',
        barmode='stack',
        xaxis_title='Número de Estudiantes Reprobados',
        yaxis_title='Asignatura',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig


def graficar_mapa_calor(df):
    """
    Heatmap matricial cruzando 'SEMESTRE_ASIGNATURA' vs 'PERIODO',
    donde la intensidad del color refleje el % de reprobación.
    """
    if df is None or df.empty:
        fig = go.Figure()
        fig.update_layout(title="Mapa de Calor Curricular - Sin datos disponibles")
        return fig
    
    df_trabajo = df.copy()
    
    if 'TIPO_REGISTRO' in df_trabajo.columns:
        df_trabajo = df_trabajo[df_trabajo['TIPO_REGISTRO'] == 'CON_BOLETIN'].copy()
    
    if df_trabajo.empty or 'SEMESTRE_ASIGNATURA' not in df_trabajo.columns or 'PERIODO' not in df_trabajo.columns:
        fig = go.Figure()
        fig.update_layout(title="Mapa de Calor Curricular - Sin datos suficientes")
        return fig
    
    # Crear matriz
    semestres = sorted(df_trabajo['SEMESTRE_ASIGNATURA'].dropna().unique())
    periodos = sorted(df_trabajo['PERIODO'].dropna().unique())
    
    matriz = np.zeros((len(semestres), len(periodos)))
    
    for i, sem in enumerate(semestres):
        for j, per in enumerate(periodos):
            df_cell = df_trabajo[(df_trabajo['SEMESTRE_ASIGNATURA'] == sem) & (df_trabajo['PERIODO'] == per)]
            if df_cell.empty:
                matriz[i, j] = np.nan
                continue
            
            reprobados = 0
            total = len(df_cell)
            if 'ESTADO_MATERIA' in df_cell.columns:
                reprobados = len(df_cell[df_cell['ESTADO_MATERIA'].astype(str).str.upper().str.contains('PERDIO', na=False)])
            elif 'DEFINITIVA_ALMACENADA' in df_cell.columns:
                notas = df_cell['DEFINITIVA_ALMACENADA'].dropna()
                reprobados = len(notas[notas < 3.0])
                total = len(notas) if len(notas) > 0 else total
            
            if total > 0:
                matriz[i, j] = (reprobados / total) * 100
            else:
                matriz[i, j] = np.nan
    
    fig = go.Figure(data=go.Heatmap(
        z=matriz,
        x=periodos,
        y=[str(s) for s in semestres],
        colorscale='Reds',
        text=np.round(matriz, 1),
        texttemplate='%{text}%',
        colorbar=dict(title="% Reprobación")
    ))
    
    fig.update_layout(
        title='Mapa de Calor Curricular - % de Reprobación por Semestre y Periodo',
        xaxis_title='Periodo Académico',
        yaxis_title='Semestre'
    )
    
    return fig


def graficar_distribucion_notas(df):
    """
    Boxplots de 'DEFINITIVA_ALMACENADA' agrupados por 'GRUPO' o 'DOCENTE' 
    para comparar la dispersión.
    """
    if df is None or df.empty:
        fig = go.Figure()
        fig.update_layout(title="Distribución de Notas - Sin datos disponibles")
        return fig
    
    df_trabajo = df.copy()
    
    if 'TIPO_REGISTRO' in df_trabajo.columns:
        df_trabajo = df_trabajo[df_trabajo['TIPO_REGISTRO'] == 'CON_BOLETIN'].copy()
    
    if df_trabajo.empty or 'DEFINITIVA_ALMACENADA' not in df_trabajo.columns:
        fig = go.Figure()
        fig.update_layout(title="Distribución de Notas - Sin datos disponibles")
        return fig
    
    # Preferir agrupar por GRUPO, sino por DOCENTE
    grupo_col = None
    if 'GRUPO' in df_trabajo.columns and df_trabajo['GRUPO'].notna().sum() > 0:
        grupo_col = 'GRUPO'
    elif 'DOCENTE' in df_trabajo.columns:
        grupo_col = 'DOCENTE'
    
    if grupo_col is None:
        fig = px.box(df_trabajo, y='DEFINITIVA_ALMACENADA', title='Distribución de Notas')
        fig.update_layout(yaxis_title='Nota Definitiva', yaxis_range=[0, 5])
        return fig
    
    # Limitar a top grupos/docentes con más datos
    top_items = df_trabajo[grupo_col].value_counts().head(10).index
    df_plot = df_trabajo[df_trabajo[grupo_col].isin(top_items)].copy()
    
    fig = px.box(
        df_plot,
        x=grupo_col,
        y='DEFINITIVA_ALMACENADA',
        title=f'Distribución de Notas por {grupo_col}',
        color=grupo_col
    )
    
    fig.update_layout(
        xaxis_title=grupo_col,
        yaxis_title='Nota Definitiva',
        yaxis_range=[0, 5],
        showlegend=False
    )
    
    return fig


def graficar_curva_progreso(df):
    """
    Gráfico de líneas que muestre la caída del promedio desde 'PRIMER_PARCIAL' 
    a 'SEGUNDO_PARCIAL' hasta 'EXAMEN_FINAL'.
    """
    if df is None or df.empty:
        fig = go.Figure()
        fig.update_layout(title="Curva de Progreso por Cortes - Sin datos disponibles")
        return fig
    
    df_trabajo = df.copy()
    
    if 'TIPO_REGISTRO' in df_trabajo.columns:
        df_trabajo = df_trabajo[df_trabajo['TIPO_REGISTRO'] == 'CON_BOLETIN'].copy()
    
    cortes = ['PRIMER_PARCIAL', 'SEGUNDO_PARCIAL', 'EXAMEN_FINAL']
    promedios_cortes = []
    
    for corte in cortes:
        if corte in df_trabajo.columns:
            notas = df_trabajo[corte].dropna()
            # Excluir ceros en segundo parcial/examen final si son mayoritariamente ceros
            if corte in ['SEGUNDO_PARCIAL', 'EXAMEN_FINAL']:
                notas_validas = notas[notas > 0]
                if not notas_validas.empty:
                    promedios_cortes.append(notas_validas.mean())
                else:
                    promedios_cortes.append(np.nan)
            else:
                notas_validas = notas[notas >= 0]
                if not notas_validas.empty:
                    promedios_cortes.append(notas_validas.mean())
                else:
                    promedios_cortes.append(np.nan)
        else:
            promedios_cortes.append(np.nan)
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=['Primer Parcial', 'Segundo Parcial', 'Examen Final'],
        y=promedios_cortes,
        mode='lines+markers',
        name='Promedio',
        line=dict(color=COLORES_INSTITUCIONALES['azul'], width=3),
        marker=dict(size=10)
    ))
    
    fig.update_layout(
        title='Curva de Progreso por Cortes Evaluativos',
        xaxis_title='Corte Evaluativo',
        yaxis_title='Promedio',
        yaxis_range=[0, 5]
    )
    
    return fig


def graficar_matriz_riesgo(df):
    """
    Gráfico de burbujas. Eje X: Número de inscritos. Eje Y: % de reprobación.
    Tamaño de burbuja: Estudiantes inscritos. Color: Semestre de la asignatura.
    """
    if df is None or df.empty:
        fig = go.Figure()
        fig.update_layout(title="Matriz de Riesgo vs Volumen - Sin datos disponibles")
        return fig
    
    df_trabajo = df.copy()
    
    if 'TIPO_REGISTRO' in df_trabajo.columns:
        df_trabajo = df_trabajo[df_trabajo['TIPO_REGISTRO'] == 'CON_BOLETIN'].copy()
    
    if df_trabajo.empty or 'ASIGNATURA' not in df_trabajo.columns:
        fig = go.Figure()
        fig.update_layout(title="Matriz de Riesgo vs Volumen - Sin datos disponibles")
        return fig
    
    resultados = []
    
    for asignatura, grupo in df_trabajo.groupby('ASIGNATURA'):
        num_inscritos = len(grupo)
        if num_inscritos < 5:  # Filtrar con mínimo de inscritos
            continue
        
        reprobados = 0
        if 'ESTADO_MATERIA' in grupo.columns:
            reprobados = len(grupo[grupo['ESTADO_MATERIA'].astype(str).str.upper().str.contains('PERDIO', na=False)])
        elif 'DEFINITIVA_ALMACENADA' in grupo.columns:
            notas = grupo['DEFINITIVA_ALMACENADA'].dropna()
            reprobados = len(notas[notas < 3.0])
            num_inscritos = len(notas)
        
        if num_inscritos == 0:
            continue
        
        pct_reprobacion = (reprobados / num_inscritos) * 100
        semestre = grupo['SEMESTRE_ASIGNATURA'].iloc[0] if 'SEMESTRE_ASIGNATURA' in grupo.columns else 'N/A'
        
        resultados.append({
            'ASIGNATURA': str(asignatura)[:40] + '...' if len(str(asignatura)) > 40 else str(asignatura),
            'num_inscritos': num_inscritos,
            'pct_reprobacion': pct_reprobacion,
            'semestre': semestre
        })
    
    if not resultados:
        fig = go.Figure()
        fig.update_layout(title="Matriz de Riesgo vs Volumen - Sin datos suficientes")
        return fig
    
    df_res = pd.DataFrame(resultados)
    
    fig = px.scatter(
        df_res,
        x='num_inscritos',
        y='pct_reprobacion',
        size='num_inscritos',
        color='semestre',
        hover_name='ASIGNATURA',
        title='Matriz de Riesgo vs Volumen de Impacto',
        labels={
            'num_inscritos': 'Número de Inscritos',
            'pct_reprobacion': '% de Reprobación',
            'semestre': 'Semestre'
        }
    )
    
    fig.update_layout(
        xaxis_title='Número de Inscritos (n)',
        yaxis_title='% de Reprobación',
        yaxis_range=[0, 100]
    )
    
    return fig


def graficar_radar_alertas(df):
    """
    Barras divergentes enfocadas solo en el 'PRIMER_PARCIAL' para el periodo en curso.
    """
    if df is None or df.empty:
        fig = go.Figure()
        fig.update_layout(title="Alertas Periodo en Curso - Sin datos disponibles")
        return fig
    
    df_trabajo = df.copy()
    
    # Filtrar periodo en curso
    df_curso = pd.DataFrame()
    if 'CALIDAD_CIERRE' in df_trabajo.columns:
        df_curso = df_trabajo[
            df_trabajo['CALIDAD_CIERRE'].astype(str).str.upper().str.contains('PERIODO_EN_CURSO_NO_FINAL', na=False)
        ].copy()
    
    if df_curso.empty:
        fig = go.Figure()
        fig.update_layout(title="Alertas Periodo en Curso - No hay periodo en curso")
        return fig
    
    if 'TIPO_REGISTRO' in df_curso.columns:
        df_curso = df_curso[df_curso['TIPO_REGISTRO'] == 'CON_BOLETIN'].copy()
    
    if df_curso.empty or 'PRIMER_PARCIAL' not in df_curso.columns or 'ASIGNATURA' not in df_curso.columns:
        fig = go.Figure()
        fig.update_layout(title="Alertas Periodo en Curso - Sin datos de PRIMER_PARCIAL")
        return fig
    
    # Agrupar por asignatura
    resultados = []
    for asignatura, grupo in df_curso.groupby('ASIGNATURA'):
        notas_p1 = grupo['PRIMER_PARCIAL'].dropna()
        notas_p1_validas = notas_p1[notas_p1 >= 0]
        if notas_p1_validas.empty:
            continue
        
        total = len(notas_p1_validas)
        en_riesgo = len(notas_p1_validas[notas_p1_validas < 3.0])
        pct_riesgo = (en_riesgo / total) * 100
        
        if en_riesgo > 0:
            resultados.append({
                'ASIGNATURA': str(asignatura)[:50] + '...' if len(str(asignatura)) > 50 else str(asignatura),
                'en_riesgo': en_riesgo,
                'pct_riesgo': pct_riesgo,
                'total': total
            })
    
    if not resultados:
        fig = go.Figure()
        fig.update_layout(title="Alertas Periodo en Curso - Sin estudiantes en riesgo")
        return fig
    
    df_res = pd.DataFrame(resultados)
    df_res = df_res.sort_values('pct_riesgo')
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Estudiantes en Riesgo (< 3.0)',
        y=df_res['ASIGNATURA'],
        x=df_res['en_riesgo'],
        orientation='h',
        marker_color=COLORES_INSTITUCIONALES['rojo'],
        text=df_res['pct_riesgo'].apply(lambda x: f'{x:.1f}%'),
        textposition='outside'
    ))
    
    fig.update_layout(
        title='Alertas por Asignatura - Periodo en Curso (Basado en PRIMER_PARCIAL)',
        xaxis_title='Número de Estudiantes en Riesgo',
        yaxis_title='Asignatura',
        showlegend=False
    )
    
    return fig


def graficar_trayectoria_individual(df_estudiante, df_cohorte=None):
    """
    Gráfico de líneas que muestre la nota del estudiante sobre una banda sombreada
    que represente el percentil 25 al 75 de su semestre.
    """
    if df_estudiante is None or df_estudiante.empty:
        fig = go.Figure()
        fig.update_layout(title="Trayectoria Individual - Sin datos")
        return fig
    
    df_est = df_estudiante.copy()
    
    # Filtrar solo CON_BOLETIN y periodos históricos
    if 'TIPO_REGISTRO' in df_est.columns:
        df_est = df_est[df_est['TIPO_REGISTRO'] == 'CON_BOLETIN'].copy()
    
    if 'CALIDAD_CIERRE' in df_est.columns:
        df_est = df_est[
            ~df_est['CALIDAD_CIERRE'].astype(str).str.upper().str.contains('PERIODO_EN_CURSO_NO_FINAL', na=False)
        ].copy()
    
    if df_est.empty or 'PERIODO' not in df_est.columns or 'DEFINITIVA_ALMACENADA' not in df_est.columns:
        fig = go.Figure()
        fig.update_layout(title="Trayectoria Individual - Sin datos históricos")
        return fig
    
    # Agrupar por periodo
    trayectoria = df_est.groupby('PERIODO')['DEFINITIVA_ALMACENADA'].mean().reset_index()
    trayectoria = trayectoria.sort_values('PERIODO')
    
    fig = go.Figure()
    
    # Si tenemos cohorte, agregar banda de percentiles
    if df_cohorte is not None and not df_cohorte.empty:
        df_coh = df_cohorte.copy()
        if 'TIPO_REGISTRO' in df_coh.columns:
            df_coh = df_coh[df_coh['TIPO_REGISTRO'] == 'CON_BOLETIN'].copy()
        if 'CALIDAD_CIERRE' in df_coh.columns:
            df_coh = df_coh[
                ~df_coh['CALIDAD_CIERRE'].astype(str).str.upper().str.contains('PERIODO_EN_CURSO_NO_FINAL', na=False)
            ].copy()
        
        if 'PERIODO' in df_coh.columns and 'DEFINITIVA_ALMACENADA' in df_coh.columns:
            percentiles = []
            for periodo in trayectoria['PERIODO']:
                df_p = df_coh[df_coh['PERIODO'] == periodo]
                notas = df_p['DEFINITIVA_ALMACENADA'].dropna()
                if not notas.empty:
                    p25 = notas.quantile(0.25)
                    p75 = notas.quantile(0.75)
                    percentiles.append((p25, p75))
                else:
                    percentiles.append((np.nan, np.nan))
            
            p25_vals = [p[0] for p in percentiles]
            p75_vals = [p[1] for p in percentiles]
            
            # Banda sombreada percentil 25-75
            fig.add_trace(go.Scatter(
                name='Percentil 75',
                x=trayectoria['PERIODO'],
                y=p75_vals,
                mode='lines',
                line=dict(width=0),
                showlegend=False
            ))
            
            fig.add_trace(go.Scatter(
                name='Percentil 25-75',
                x=trayectoria['PERIODO'],
                y=p25_vals,
                mode='lines',
                fill='tonexty',
                fillcolor='rgba(31, 119, 180, 0.2)',
                line=dict(width=0),
                showlegend=True
            ))
    
    # Trayectoria del estudiante
    fig.add_trace(go.Scatter(
        name='Estudiante',
        x=trayectoria['PERIODO'],
        y=trayectoria['DEFINITIVA_ALMACENADA'],
        mode='lines+markers',
        line=dict(color=COLORES_INSTITUCIONALES['rojo'], width=3),
        marker=dict(size=10)
    ))
    
    fig.update_layout(
        title='Trayectoria Individual vs Banda de Cohorte (Percentil 25-75)',
        xaxis_title='Periodo Académico',
        yaxis_title='Promedio',
        yaxis_range=[0, 5],
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig


# Aliases para compatibilidad
def graficar_tendencia_historica(df):
    """
    Alias de graficar_evolucion_historica para compatibilidad con código existente.
    """
    return graficar_evolucion_historica(df)


def graficar_top_mortalidad(df):
    """
    Alias de graficar_ranking_causas para compatibilidad con código existente.
    """
    return graficar_ranking_causas(df)
