"""Vista de gestion exclusiva del administrador."""

import os
import tempfile
import pandas as pd
import streamlit as st

from src.constants import EXTENSIONES_EXCEL
from src.etl.cleaner import cargar_datos_limpios
from src.services.auth import create_professor, load_users
from src.services.data_management import reemplazar_archivos_excel
from src.services.periods import ordenar_periodos


def render_admin_tab(cargar_datos):
    st.subheader("Gestion de Datos - Administrador")
    st.caption("Carga de archivos Excel y administracion de cuentas.")

    st.markdown("### Crear cuenta de profesor")
    st.caption(
        "La cuenta solo podra consultar estadisticas de las materias "
        "asignadas al docente seleccionado."
    )
    docentes_disponibles = []
    datos_actuales = cargar_datos()
    if "DOCENTE" in datos_actuales.columns:
        docentes_disponibles = sorted(
            nombre
            for nombre in datos_actuales["DOCENTE"].dropna().astype(str).str.strip().unique()
            if nombre
        )
    with st.form("crear_cuenta_profesor"):
        nuevo_usuario = st.text_input("Usuario del profesor")
        nombre_profesor = st.text_input("Nombre visible")
        docente_asociado = st.selectbox(
            "Docente del archivo academico",
            options=docentes_disponibles,
        )
        nueva_contrasena = st.text_input("Contrasena inicial", type="password")
        crear_cuenta = st.form_submit_button("Crear cuenta", width="stretch")
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
    uploaded_file = st.file_uploader(
        "Seleccionar archivo Excel (.xlsx)",
        type=["xlsx", "xls", "xlsm"],
        help="Suba el archivo consolidado con las hojas de registros academicos",
    )
    if uploaded_file is None:
        st.info("Seleccione un archivo Excel para comenzar la carga")
        return

    st.success(f"Archivo cargado: {uploaded_file.name}")
    tmp_path = None
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name
    try:
        with st.spinner("Procesando y validando datos..."):
            df_nuevo = cargar_datos_limpios(ruta_excel=tmp_path)
        st.markdown("### Resumen del archivo cargado")
        col_r1, col_r2, col_r3 = st.columns(3)
        with col_r1:
            st.metric("Total de filas nuevas", f"{len(df_nuevo):,}")
        with col_r2:
            periodos = ordenar_periodos(df_nuevo["PERIODO"].dropna().unique())
            st.metric("Periodos detectados", f"{len(periodos)}")
            st.caption(", ".join(periodos))
        with col_r3:
            st.metric(
                "Cantidad de estudiantes",
                f"{df_nuevo['ID_ESTUDIANTE'].nunique():,}",
            )

        if st.button(
            "Guardar y consolidar",
            width="stretch",
            type="primary",
            key="guardar_consolidar",
        ):
            destino, respaldo = reemplazar_archivos_excel(
                "data",
                tmp_path,
                uploaded_file.name,
                "data/backups",
            )
            st.cache_data.clear()
            mensaje_respaldo = (
                f" Respaldo creado en '{respaldo}'."
                if respaldo
                else " No habia un archivo anterior para respaldar."
            )
            st.success(
                f"Archivo guardado como '{destino.name}'.{mensaje_respaldo}"
            )
            st.info("Recarga la pagina para ver los datos actualizados.")
    except (OSError, ValueError) as error:
        st.error(f"Error al procesar o guardar el archivo: {error}")
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
