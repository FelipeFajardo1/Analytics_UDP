"""Controles de seguridad visibles para usuarios autenticados."""

import streamlit as st

from src.services.auth import change_password


def render_password_form(usuario):
    with st.sidebar.expander("Cambiar contraseña"):
        with st.form("cambiar_contrasena"):
            actual = st.text_input("Contraseña actual", type="password")
            nueva = st.text_input("Nueva contraseña", type="password")
            confirmar = st.text_input("Confirmar contraseña", type="password")
            enviar = st.form_submit_button("Actualizar contraseña")
        if enviar:
            if nueva != confirmar:
                st.error("Las contraseñas nuevas no coinciden.")
            else:
                try:
                    change_password(usuario.get("username", ""), actual, nueva)
                    st.success("Contraseña actualizada correctamente.")
                except ValueError as error:
                    st.error(str(error))
