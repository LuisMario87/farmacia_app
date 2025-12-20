if st.session_state["usuario"]["rol"] != "admin":
    st.stop()

nombre = st.text_input("Nombre")
email = st.text_input("Email")
password = st.text_input("Contraseña", type="password")
rol = st.selectbox("Rol", ["admin", "empleado"])

if st.button("Crear usuario"):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO usuarios (nombre, email, password_hash, rol)
        VALUES (%s, %s, %s, %s)
    """, (nombre, email, hashed, rol))
    conn.commit()
    cursor.close()
    conn.close()

    st.success("Usuario creado")
