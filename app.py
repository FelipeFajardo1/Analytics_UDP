import streamlit as st
import pandas as pd
import os
import tempfile
import shutil
from src.etl.cleaner import cargar_datos_limpios
from src.services.metrics import (
    calcular_kpis_globales,
    calcular_rendimiento_materias,
    detectar_alertas_tempranas
)
from src.components.charts import (
    graficar_tendencia_promedios,
    graficar_tendencia_cantidades,
)
from src.components.student_profile import mostrar_ficha_estudiante
from src.services.ai_copilot import generar_analisis_ia, explicar_grafico_ia
from src.services.auth import authenticate, create_professor, load_users


st.set_page_config(
    page_title="Analitica Academica ITP",
    page_icon="YS",
    layout="wide",
    initial_sidebar_state="expanded"
)


@st.cache_data
def cargar_datos():
    """Carga y limpia los datos del archivo Excel con cachA para evitar recargas."""
    return cargar_datos_limpios()


def _filtrar_datos_por_rol(df, usuario):
    if usuario.get("role") != "profesor":
        return df
    if "DOCENTE" not in df.columns:
        return df.iloc[0:0].copy()
    nombre_docente = usuario.get("teacher_name", "").strip().upper()
    return df[
        df["DOCENTE"].astype(str).str.strip().str.upper() == nombre_docente
    ].copy()


def main():
    # Sistema de autenticacion
    if 'autenticado' not in st.session_state:
        st.session_state.autenticado = False
    
    if not st.session_state.autenticado:
        st.title("Acceso Restringido - Analitica Academica ITP")
        st.markdown("**Informacion estrictamente confidencial - Solo personal autorizado**")
        
        col_login1, col_login2, col_login3 = st.columns([1, 2, 1])
        with col_login2:
            st.markdown("---")
            username = st.text_input("Usuario", placeholder="Ingrese su usuario")
            password = st.text_input(
                "Contrasena",
                type="password",
                placeholder="Ingrese la contrasena",
            )
            if st.button("Ingresar", width="stretch"):
                usuario = authenticate(username, password)
                if usuario is not None:
                    st.session_state.autenticado = True
                    st.session_state.usuario = usuario
                    st.rerun()
                else:
                    st.error("Contrasena incorrecta. Acceso denegado.")
            st.markdown("---")
        return
    
    st.title("Analitica Academica ITP")
    st.markdown("Sistema de analisis del rendimiento academico para la toma de decisiones")
    usuario = st.session_state.get("usuario", {})
    rol = usuario.get("role", "")
    st.sidebar.caption(
        f"Sesion: {usuario.get('display_name', 'Usuario')} ({rol})"
    )
    
    # Boton de cerrar sesion
    if st.sidebar.button("Cerrar Sesion"):
        st.session_state.autenticado = False
        st.session_state.pop("usuario", None)
        st.rerun()
    
    # API Key para IA
    st.sidebar.markdown("---")
    st.sidebar.subheader("Inteligencia Artificial")
    api_key_google = st.sidebar.text_input(
        "API Key de Google Gemini",
        type="password",
        placeholder="Ingrese su API Key",
        help="Opcional - Solo si desea usar el analisis con IA"
    )
    
    # Cargar datos
    with st.spinner("Cargando y limpiando datos..."):
        df = _filtrar_datos_por_rol(cargar_datos(), usuario)
    
    if df.empty:
        st.error("No se encontraron datos para mostrar.")
        return
    
    # Pestañas de navegacion
    nombres_tabs = ["Vision Global"]
    if rol in {"admin", "director"}:
        nombres_tabs.append("Analisis por Estudiante")
    if rol == "admin":
        nombres_tabs.append("Gestion de Datos (Administrador)")
    tabs = st.tabs(nombres_tabs)
    tab1 = tabs[0]
    
    with tab1:
        # Barra lateral con filtros globales
        st.sidebar.header("Filtros Globales")
    
        # Filtro de Programa
        programas_disponibles = ["Todos"]
        if 'PROGRAMA' in df.columns:
            programas_unicos = sorted(df['PROGRAMA'].dropna().unique().tolist())
            programas_disponibles.extend(programas_unicos)
    
        programa_seleccionado = st.sidebar.selectbox(
            "Programa",
            options=programas_disponibles,
            index=0
        )

        # Los periodos en curso no se mezclan con historicos cerrados.
        periodos_historicos = []
        if 'PERIODO' in df.columns:
            periodos_historicos = sorted(
                df.loc[
                    ~df.get(
                        'CALIDAD_CIERRE',
                        pd.Series('', index=df.index),
                    ).astype(str).str.upper().str.contains(
                        'PERIODO_EN_CURSO_NO_FINAL', na=False
                    ),
                    'PERIODO',
                ].dropna().unique().tolist(),
                key=lambda valor: (
                    int(str(valor).split('-')[0]),
                    int(str(valor).split('-')[1]),
                ),
            )

        if periodos_historicos:
            periodo_inicio, periodo_fin = st.sidebar.select_slider(
                "Rango de periodos academicos",
                options=periodos_historicos,
                value=(periodos_historicos[0], periodos_historicos[-1]),
            )
            indice_inicio = periodos_historicos.index(periodo_inicio)
            indice_fin = periodos_historicos.index(periodo_fin)
            periodos_seleccionados = periodos_historicos[indice_inicio:indice_fin + 1]
        else:
            st.sidebar.warning("No hay periodos historicos cerrados disponibles.")
            periodos_seleccionados = []
        periodo_en_curso_seleccionado = False
    
        # Filtro de Sede
        sedes_disponibles = ["Todas"]
        if 'SEDE' in df.columns:
            sedes_unicas = sorted(df['SEDE'].dropna().unique().tolist())
            sedes_disponibles.extend(sedes_unicas)
    
        sede_seleccionada = st.sidebar.selectbox(
            "Sede",
            options=sedes_disponibles,
            index=0
        )
    
        # Filtro de Asignatura dependiente del programa
        asignaturas_disponibles = ["Todas"]
        if 'ASIGNATURA' in df.columns:
            df_temp_asig = df
            if programa_seleccionado != "Todos" and 'PROGRAMA' in df.columns:
                df_temp_asig = df[df['PROGRAMA'] == programa_seleccionado]
            asignaturas_unicas = sorted(df_temp_asig['ASIGNATURA'].dropna().unique().tolist())
            asignaturas_disponibles.extend(asignaturas_unicas)

        asignatura_seleccionada = st.sidebar.selectbox(
            "Asignatura",
            options=asignaturas_disponibles,
            index=0
        )
    
        # Aplicar filtros al DataFrame
        df_filtrado = df.copy()
    
        # Filtrar por el rango de periodos historicos seleccionado
        if 'PERIODO' in df_filtrado.columns and periodos_seleccionados:
            df_filtrado = df_filtrado[
                df_filtrado['PERIODO'].isin(periodos_seleccionados)
            ].copy()
    
        # Filtrar por programa
        if programa_seleccionado != "Todos" and 'PROGRAMA' in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado['PROGRAMA'] == programa_seleccionado].copy()
    
        # Filtrar por sede
        if sede_seleccionada != "Todas" and 'SEDE' in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado['SEDE'] == sede_seleccionada].copy()
    
        # Filtrar por asignatura
        if asignatura_seleccionada != "Todas" and 'ASIGNATURA' in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado['ASIGNATURA'] == asignatura_seleccionada].copy()

        # Conserva todo el historico para calcular correctamente el acumulado
        # aunque el usuario visualice un rango que empiece despues.
        df_tendencias = df.copy()
        if programa_seleccionado != "Todos" and 'PROGRAMA' in df_tendencias.columns:
            df_tendencias = df_tendencias[
                df_tendencias['PROGRAMA'] == programa_seleccionado
            ].copy()
        if sede_seleccionada != "Todas" and 'SEDE' in df_tendencias.columns:
            df_tendencias = df_tendencias[
                df_tendencias['SEDE'] == sede_seleccionada
            ].copy()
    
        st.sidebar.markdown("---")
        st.sidebar.info(f"Registros filtrados: {len(df_filtrado):,}")
    
        # Fila superior con 4 tarjetas de metricas
        st.subheader("Indicadores Globales")
    
        kpis = calcular_kpis_globales(df_filtrado)
    
        col1, col2, col3, col4 = st.columns(4)
    
        with col1:
            st.metric(
                label="Estudiantes Unicos",
                value=f"{kpis.get('total_estudiantes_unicos', 0):,}"
            )

        with col2:
            st.metric(
                label="Total Matriculas",
                value=f"{kpis.get('total_matriculas', 0):,}"
            )

        with col3:
            nota_prom = kpis.get('nota_promedio_global', 0)
            if pd.isna(nota_prom):
                st.metric(label="Nota Promedio Global", value="N/A")
            else:
                st.metric(label="Nota Promedio Global", value=f"{nota_prom:.2f}")

        with col4:
            tasa_aprob = kpis.get('tasa_aprobacion', 0)
            tasa_rep = kpis.get('tasa_reprobacion', 0)
            st.metric(
                label="Aprobacion / Reprobacion",
                value=f"{tasa_aprob:.1f}% / {tasa_rep:.1f}%"
            )
    
        st.markdown("---")
    
        # Analisis ejecutivo integral con IA
        st.subheader("Analisis ejecutivo integral con IA")
        st.caption("Interpreta las tablas y metricas agregadas del periodo y filtros seleccionados.")
        if st.button("Generar anAlisis ejecutivo integral", width="stretch", key="btn_ia"):
            if not api_key_google or api_key_google.strip() == "":
                st.warning("Por favor, ingrese su API Key de Google Gemini en la barra lateral.")
            else:
                with st.spinner("Generando analisis con IA..."):
                    resultado_ia = generar_analisis_ia(df_filtrado, api_key_google)
                if "Error" in resultado_ia or "Por favor" in resultado_ia:
                    st.error(resultado_ia)
                else:
                    st.success("Analisis generado exitosamente")
                    st.info(resultado_ia)
    
        st.markdown("---")
    
        st.subheader("Tendencias para direccion academica")
        st.caption(
            "Los calculos usan periodos historicos cerrados y excluyen registros SIN_BOLETIN."
        )

        with st.container(border=True, width="stretch"):
            st.markdown("### Promedios por periodo")
            figura_promedios = graficar_tendencia_promedios(
                df_tendencias,
                periodos_visibles=periodos_seleccionados,
            )
            st.plotly_chart(
                figura_promedios,
                width="stretch",
                key="tendencia_promedios",
            )

        with st.container(border=True, width="stretch"):
            st.markdown("### Cantidad de aprobados y reprobados")
            figura_cantidades = graficar_tendencia_cantidades(
                df_filtrado,
                periodos_visibles=periodos_seleccionados,
            )
            st.plotly_chart(
                figura_cantidades,
                width="stretch",
                key="tendencia_cantidades",
            )

            periodos_drilldown = (
                sorted(
                    df_filtrado['PERIODO'].dropna().unique().tolist(),
                    key=lambda valor: (
                        int(str(valor).split('-')[0]),
                        int(str(valor).split('-')[1]),
                    ),
                )
                if 'PERIODO' in df_filtrado.columns
                else []
            )
            if periodos_drilldown:
                periodo_drilldown = st.selectbox(
                    "Consultar estudiantes reprobados de un periodo",
                    options=periodos_drilldown,
                    key="periodo_drilldown",
                )
                reprobados = df_filtrado[
                    (df_filtrado['PERIODO'] == periodo_drilldown)
                    & (
                        df_filtrado['ESTADO_MATERIA']
                        .astype(str)
                        .str.strip()
                        .str.upper()
                        == 'PERDIO'
                    )
                ].copy()
                columnas_drilldown = [
                    'NOMBRE_COMPLETO',
                    'NUMERO_DOCUMENTO',
                    'CORREO_INSTITUCIONAL',
                ]
                columnas_disponibles = [
                    columna for columna in columnas_drilldown
                    if columna in reprobados.columns
                ]
                st.dataframe(
                    reprobados[columnas_disponibles],
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.info("No hay periodos disponibles para consultar.")
    
        st.markdown("---")

        # Panel principal con rendimiento por materias
        st.subheader("Rendimiento por Asignatura")

        rendimiento_materias = calcular_rendimiento_materias(df_filtrado)

        if not rendimiento_materias.empty:
            # Ordenar por tasa de reprobacion
            rendimiento_materias = rendimiento_materias.sort_values('porcentaje_reprobacion', ascending=False)
    
            # Mostrar dataframe
            st.dataframe(
                rendimiento_materias,
                width="stretch",
                hide_index=True,
                column_config={
                    "ASIGNATURA": st.column_config.TextColumn("Asignatura", width="large"),
                    "num_inscritos": st.column_config.NumberColumn("Inscritos", format="%d"),
                    "nota_promedio": st.column_config.NumberColumn("Nota Promedio", format="%.2f"),
                    "porcentaje_reprobacion": st.column_config.NumberColumn("% Reprobacion", format="%.2f%%")
                }
            )
        else:
            st.info("No hay datos de rendimiento por materia para mostrar con los filtros seleccionados.")

            # Seccion condicional para periodo en curso
            if periodo_en_curso_seleccionado:
                st.markdown("---")
                st.subheader("Estudiantes en Riesgo - Periodo en Curso (2026-2)")
                st.caption("Basado unicamente en PRIMER_PARCIAL con calificacion menor a 3.0 en 2 o mas asignaturas")
        
                alertas = detectar_alertas_tempranas(df_filtrado)
        
                if not alertas.empty:
                    st.dataframe(
                        alertas,
                        width="stretch",
                        hide_index=True,
                        column_config={
                            "ID_ESTUDIANTE": st.column_config.TextColumn("ID Estudiante"),
                            "NOMBRE_COMPLETO": st.column_config.TextColumn("Nombre Completo", width="large"),
                            "num_asignaturas_bajo_rendimiento": st.column_config.NumberColumn("Asignaturas en Riesgo", format="%d"),
                            "asignaturas_afectadas": st.column_config.TextColumn("Asignaturas Afectadas", width="large")
                        }
                    )
                    st.warning(f"Se detectaron {len(alertas)} estudiante(s) en alerta temprana.")
                else:
                    st.success("No se detectaron estudiantes en alerta temprana con los criterios actuales.")

    if rol in {"admin", "director"}:
        with tabs[1]:
            mostrar_ficha_estudiante(df)
    
    if rol == "admin":
        with tabs[2]:
            st.subheader("Gestion de Datos - Administrador")
        st.caption("Carga de archivos Excel semestrales para actualizar el historico")

        st.markdown("### Crear cuenta de profesor")
        st.caption(
            "La cuenta solo podra consultar estadisticas de las materias "
            "asignadas al docente seleccionado."
        )
        docentes_disponibles = []
        if "DOCENTE" in cargar_datos().columns:
            docentes_disponibles = sorted(
                nombre
                for nombre in cargar_datos()["DOCENTE"].dropna().astype(str).str.strip().unique()
                if nombre
            )
        with st.form("crear_cuenta_profesor"):
            nuevo_usuario = st.text_input("Usuario del profesor")
            nombre_profesor = st.text_input("Nombre visible")
            docente_asociado = st.selectbox(
                "Docente del archivo academico",
                options=docentes_disponibles,
            )
            nueva_contrasena = st.text_input(
                "Contrasena inicial",
                type="password",
            )
            crear_cuenta = st.form_submit_button(
                "Crear cuenta",
                width="stretch",
            )
        if crear_cuenta:
            try:
                create_professor(
                    nuevo_usuario,
                    nombre_profesor,
                    docente_asociado,
                    nueva_contrasena,
                )
                st.success(
                    f"Cuenta '{nuevo_usuario.strip().lower()}' creada correctamente."
                )
            except ValueError as error:
                st.error(str(error))

        st.markdown("### Cuentas registradas")
        cuentas = pd.DataFrame(
            [
                {
                    "Usuario": user.get("username", ""),
                    "Nombre": user.get("display_name", ""),
                    "Rol": user.get("role", ""),
                    "Docente asociado": user.get("teacher_name", ""),
                }
                for user in load_users()
            ]
        )
        st.dataframe(cuentas, width="stretch", hide_index=True)

        st.markdown("---")
        
        # File uploader
        uploaded_file = st.file_uploader(
            "Seleccionar archivo Excel (.xlsx)",
            type=['xlsx'],
            help="Suba el archivo consolidado con las hojas de registros acadAmicos"
        )
        
        if uploaded_file is not None:
            st.success(f"Archivo cargado: {uploaded_file.name}")
            
            # Guardar archivo temporal
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name
            
            try:
                with st.spinner("Procesando y validando datos..."):
                    # Ejecutar cargar_datos_limpios sobre archivo temporal
                    df_nuevo = cargar_datos_limpios(ruta_excel=tmp_path)
                
                st.markdown("### Resumen del Archivo Cargado")
                
                col_r1, col_r2, col_r3 = st.columns(3)
                
                with col_r1:
                    st.metric("Total de Filas Nuevas", f"{len(df_nuevo):,}")
                
                with col_r2:
                    if 'PERIODO' in df_nuevo.columns:
                        periodos_detectados = df_nuevo['PERIODO'].dropna().unique()
                        st.metric("Periodos Detectados", f"{len(periodos_detectados)}")
                        st.caption(", ".join(sorted([str(p) for p in periodos_detectados])))
                    else:
                        st.metric("Periodos Detectados", "N/A")
                
                with col_r3:
                    if 'ID_ESTUDIANTE' in df_nuevo.columns:
                        num_estudiantes = df_nuevo['ID_ESTUDIANTE'].nunique()
                        st.metric("Cantidad de Estudiantes", f"{num_estudiantes:,}")
                    else:
                        st.metric("Cantidad de Estudiantes", "N/A")
                
                st.markdown("---")
                
                # Boton para guardar y consolidar
                if st.button("Guardar y Consolidar", width="stretch", type="primary", key="guardar_consolidar"):
                    try:
                        carpeta_data = "data"
                        os.makedirs(carpeta_data, exist_ok=True)

                        nombre_seguro = os.path.basename(uploaded_file.name)
                        if not nombre_seguro:
                            raise ValueError("El archivo cargado no tiene un nombre vAlido.")

                        ruta_destino = os.path.join(carpeta_data, nombre_seguro)
                        ruta_temporal_data = f"{ruta_destino}.uploading"
                        shutil.copy2(tmp_path, ruta_temporal_data)

                        for nombre_archivo in os.listdir(carpeta_data):
                            ruta_archivo = os.path.join(carpeta_data, nombre_archivo)
                            if (
                                os.path.isfile(ruta_archivo)
                                and os.path.splitext(nombre_archivo)[1].lower()
                                in {".xlsx", ".xls", ".xlsm"}
                            ):
                                os.remove(ruta_archivo)

                        os.replace(ruta_temporal_data, ruta_destino)
                        
                        # Limpiar cache
                        st.cache_data.clear()
                        
                        st.success(
                            f"Archivo guardado exitosamente como '{nombre_seguro}'. "
                            "El archivo Excel anterior fue reemplazado."
                        )
                        st.info("Recarga la pagina para ver los datos actualizados.")
                        
                    except Exception as e:
                        st.error(f"Error al guardar el archivo: {e}")
                
            except Exception as e:
                st.error(f"Error al procesar el archivo: {e}")
                st.caption("Verifique que el archivo tenga el formato correcto con las hojas de registros acadAmicos.")
            
            finally:
                # Limpiar archivo temporal
                try:
                    os.unlink(tmp_path)
                except:
                    pass
        else:
            st.info("Seleccione un archivo .xlsx para comenzar la carga")


if __name__ == "__main__":
    main()
