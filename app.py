import streamlit as st
from src.etl.cleaner import cargar_datos_limpios
from src.components.student_profile import mostrar_ficha_estudiante
from src.services.ai_copilot import obtener_api_key_configurada
from src.services.auth import authenticate
from src.services.access import filtrar_datos_por_rol
from src.ui.admin import render_admin_tab
from src.ui.global_view import render_global_tab
from src.ui.risk import render_risk_tab
from src.ui.security import render_password_form
from src.ui.subject_analysis import render_subject_analysis_tab


st.set_page_config(
    page_title="Analitica Academica UDP",
    page_icon="YS",
    layout="wide",
    initial_sidebar_state="expanded"
)


@st.cache_data
def cargar_datos():
    """Carga y limpia los datos del archivo Excel con cachA para evitar recargas."""
    return cargar_datos_limpios()


def main():
    # Sistema de autenticacion
    if 'autenticado' not in st.session_state:
        st.session_state.autenticado = False
    
    if not st.session_state.autenticado:
        st.title("Acceso Restringido - Analitica Academica UDP")
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
    
    st.title("Analitica Academica UDP")
    st.markdown("Sistema de analisis del rendimiento academico para la toma de decisiones")
    usuario = st.session_state.get("usuario", {})
    rol = usuario.get("role", "")
    st.sidebar.caption(
        f"Sesion: {usuario.get('display_name', 'Usuario')} ({rol})"
    )
    render_password_form(usuario)
    
    # Boton de cerrar sesion
    if st.sidebar.button("Cerrar Sesion"):
        st.session_state.autenticado = False
        st.session_state.pop("usuario", None)
        st.rerun()
    
    # API Key para IA
    st.sidebar.markdown("---")
    st.sidebar.subheader("Inteligencia Artificial")
    api_key_google = obtener_api_key_configurada()
    if api_key_google:
        st.sidebar.success("API de IA configurada desde secrets.")
    else:
        api_key_google = st.sidebar.text_input(
            "API Key de Google Gemini",
            type="password",
            placeholder="Ingrese su API Key",
            help="Opcional - configure GOOGLE_API_KEY en Streamlit secrets.",
        )
    
    # Cargar datos
    with st.spinner("Cargando y limpiando datos..."):
        df = filtrar_datos_por_rol(cargar_datos(), usuario)
    
    if df.empty:
        st.error("No se encontraron datos para mostrar.")
        return
    
    # Pestañas de navegacion
    nombres_tabs = [
        "Vision Global",
        "Riesgo periodo vigente",
        "Analisis Detallado",
    ]
    if rol in {"admin", "director"}:
        nombres_tabs.append("Analisis por Estudiante")
    if rol == "admin":
        nombres_tabs.append("Gestion de Datos (Administrador)")
    tabs = st.tabs(nombres_tabs)
    tab1 = tabs[0]
    
    with tab1:
        contexto_global = render_global_tab(df, api_key_google)

    with tabs[1]:
        render_risk_tab(df)

    with tabs[2]:
        render_subject_analysis_tab(
            df,
            contexto_global["df_filtrado"],
            contexto_global["asignatura_seleccionada"],
            contexto_global["periodos_seleccionados"],
            contexto_global["periodos_cortes_seleccionados"],
        )

    indice_estudiante = 3
    if rol in {"admin", "director"}:
        with tabs[indice_estudiante]:
            mostrar_ficha_estudiante(df)
        indice_estudiante += 1
    
    if rol == "admin":
        with tabs[indice_estudiante]:
            render_admin_tab(cargar_datos)


if __name__ == "__main__":
    main()
