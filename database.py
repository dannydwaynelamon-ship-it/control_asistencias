import sqlite3
from datetime import datetime

def conectar():
    conexion = sqlite3.connect("colegio.db")
    conexion.execute("PRAGMA foreign_keys = ON;")
    return conexion

def inicializar_bd():
    conexion = conectar()
    cursor = conexion.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS secciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anio TEXT,
            seccion TEXT,
            coordinacion TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS estudiantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cedula TEXT UNIQUE,
            nombre TEXT,
            id_seccion INTEGER,
            FOREIGN KEY (id_seccion) REFERENCES secciones (id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS docentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cedula TEXT UNIQUE,
            nombre TEXT,
            materia TEXT,
            horas_trabajo INTEGER DEFAULT 0
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS docente_registros_horas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cedula_docente TEXT,
            fecha TEXT,
            horas INTEGER,
            FOREIGN KEY (cedula_docente) REFERENCES docentes (cedula) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS materias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS estudiante_asistencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cedula_estudiante TEXT,
            fecha TEXT,
            estado TEXT,
            horas_estudio TEXT,
            materia TEXT,
            justificada TEXT,
            observacion TEXT,
            FOREIGN KEY (cedula_estudiante) REFERENCES estudiantes (cedula) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios_sistema (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE,
            password TEXT,
            nombre_completo TEXT,
            rol TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historial_auditoria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT,
            fecha_hora TEXT,
            accion TEXT,
            detalle TEXT
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM usuarios_sistema")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO usuarios_sistema (usuario, password, nombre_completo, rol) VALUES (?, ?, ?, ?)",
            ("admin", "admin123", "Administrador Principal", "admin")
        )
        cursor.execute(
            "INSERT INTO usuarios_sistema (usuario, password, nombre_completo, rol) VALUES (?, ?, ?, ?)",
            ("coord1", "coord123", "Coordinación General", "coordinacion")
        )

    conexion.commit()
    conexion.close()

def registrar_auditoria(usuario, accion, detalle):
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO historial_auditoria (usuario, fecha_hora, accion, detalle)
            VALUES (?, ?, ?, ?)
        """, (usuario, ahora, accion, detalle))
        conexion.commit()
        conexion.close()
    except Exception as e:
        print(f"Error al registrar auditoría: {e}")

def obtener_historial_auditoria():
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("SELECT usuario, fecha_hora, accion, detalle FROM historial_auditoria ORDER BY id DESC LIMIT 100")
    registros = cursor.fetchall()
    conexion.close()
    return registros

def validar_login(usuario, password):
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("SELECT usuario, nombre_completo, rol FROM usuarios_sistema WHERE usuario = ? AND password = ?", (usuario, password))
    res = cursor.fetchone()
    conexion.close()
    return res

def obtener_usuarios_sistema():
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("SELECT id, usuario, nombre_completo, rol FROM usuarios_sistema")
    res = cursor.fetchall()
    conexion.close()
    return res

def registrar_usuario_sistema(usuario, password, nombre, rol):
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("""
            INSERT INTO usuarios_sistema (usuario, password, nombre_completo, rol)
            VALUES (?, ?, ?, ?)
        """, (usuario, password, nombre, rol))
        conexion.commit()
        conexion.close()
        return True, "Usuario registrado con éxito."
    except Exception as e:
        return False, f"Error: El nombre de usuario ya existe ({e})"

def eliminar_usuario_sistema(id_usu):
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM usuarios_sistema WHERE id = ?", (id_usu,))
        conexion.commit()
        conexion.close()
        return True
    except Exception as e:
        return False

def registrar_docente(cedula, nombre, materia, horas, usuario_act="Sistema"):
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO docentes (cedula, nombre, materia, horas_trabajo)
            VALUES (?, ?, ?, ?)
        """, (cedula, nombre, materia, horas))
        conexion.commit()
        conexion.close()
        registrar_auditoria(usuario_act, "REGISTRAR/MODIFICAR DOCENTE", f"Docente: {nombre} ({cedula})")
        return True
    except Exception as e:
        return False

def eliminar_docente(cedula, usuario_act="Sistema"):
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM docentes WHERE cedula = ?", (cedula,))
        conexion.commit()
        conexion.close()
        registrar_auditoria(usuario_act, "ELIMINAR DOCENTE", f"Cédula: {cedula}")
        return True
    except Exception as e:
        return False

def obtener_docentes():
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("SELECT cedula, nombre, materia, horas_trabajo FROM docentes")
    docentes = cursor.fetchall()
    conexion.close()
    return docentes

def registrar_horas_diarias(cedula, fecha, horas, usuario_act="Sistema"):
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("""
            INSERT INTO docente_registros_horas (cedula_docente, fecha, horas)
            VALUES (?, ?, ?)
        """, (cedula, fecha, horas))
        conexion.commit()
        conexion.close()
        registrar_auditoria(usuario_act, "REGISTRO HORAS DOCENTE", f"Docente cédula {cedula}: {horas} hrs el {fecha}")
        return True
    except Exception as e:
        return False

def obtener_historial_horas():
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("""
        SELECT h.id, d.nombre, h.cedula_docente, h.fecha, h.horas 
        FROM docente_registros_horas h
        JOIN docentes d ON h.cedula_docente = d.cedula
        ORDER BY h.fecha DESC
    """)
    registros = cursor.fetchall()
    conexion.close()
    return registros

def eliminar_registro_hora(id_registro, usuario_act="Sistema"):
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM docente_registros_horas WHERE id = ?", (id_registro,))
        conexion.commit()
        conexion.close()
        registrar_auditoria(usuario_act, "ELIMINAR JORNADA HORA DOCENTE", f"ID Registro: {id_registro}")
        return True
    except Exception as e:
        return False

def obtener_secciones():
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("SELECT id, anio, seccion, coordinacion FROM secciones ORDER BY anio, seccion")
    secciones = cursor.fetchall()
    conexion.close()
    return secciones

def obtener_estudiantes():
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("SELECT cedula, nombre FROM estudiantes ORDER BY nombre")
    estudiantes = cursor.fetchall()
    conexion.close()
    return estudiantes

def obtener_estudiantes_por_seccion(id_seccion):
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("SELECT cedula, nombre FROM estudiantes WHERE id_seccion = ? ORDER BY nombre", (id_seccion,))
    estudiantes = cursor.fetchall()
    conexion.close()
    return estudiantes

def obtener_estudiantes_detallado(id_seccion=None, busqueda=""):
    conexion = conectar()
    cursor = conexion.cursor()
    query = """
        SELECT e.cedula, e.nombre, s.anio, s.seccion, s.coordinacion
        FROM estudiantes e
        LEFT JOIN secciones s ON e.id_seccion = s.id
        WHERE 1=1
    """
    params = []
    if id_seccion and id_seccion != "TODAS":
        query += " AND e.id_seccion = ?"
        params.append(id_seccion)
    if busqueda:
        query += " AND (e.nombre LIKE ? OR e.cedula LIKE ?)"
        termino = f"%{busqueda}%"
        params.extend([termino, termino])
    query += " ORDER BY s.anio, s.seccion, e.nombre"
    cursor.execute(query, tuple(params))
    resultados = cursor.fetchall()
    conexion.close()
    return resultados

def obtener_estudiantes_agrupados_por_seccion():
    """Retorna un diccionario agrupado por sección con todos sus estudiantes."""
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("""
        SELECT s.id, s.anio, s.seccion, s.coordinacion, e.cedula, e.nombre
        FROM secciones s
        LEFT JOIN estudiantes e ON s.id = e.id_seccion
        ORDER BY s.anio, s.seccion, e.nombre
    """)
    filas = cursor.fetchall()
    conexion.close()

    agrupado = {}
    for id_s, anio, sec, coord, ced, nom in filas:
        clave = (id_s, anio, sec, coord)
        if clave not in agrupado:
            agrupado[clave] = []
        if ced is not None:
            agrupado[clave].append((ced, nom))
    return agrupado

def eliminar_estudiante(cedula, usuario_act="Sistema"):
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM estudiantes WHERE cedula = ?", (cedula,))
        conexion.commit()
        conexion.close()
        registrar_auditoria(usuario_act, "ELIMINAR ESTUDIANTE", f"Cédula: {cedula}")
        return True
    except Exception as e:
        return False

def guardar_o_editar_estudiante(cedula_original, nueva_cedula, nombre, anio, seccion, coordinacion="Media General", usuario_act="Sistema"):
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT id FROM secciones WHERE anio = ? AND seccion = ?", (anio.strip(), seccion.strip()))
        res = cursor.fetchone()
        if res:
            id_seccion = res[0]
        else:
            cursor.execute("INSERT INTO secciones (anio, seccion, coordinacion) VALUES (?, ?, ?)", (anio.strip(), seccion.strip(), coordinacion.strip()))
            id_seccion = cursor.lastrowid

        if cedula_original:
            if cedula_original != nueva_cedula:
                cursor.execute("UPDATE estudiante_asistencias SET cedula_estudiante = ? WHERE cedula_estudiante = ?", (nueva_cedula, cedula_original))
            cursor.execute("UPDATE estudiantes SET cedula = ?, nombre = ?, id_seccion = ? WHERE cedula = ?", (nueva_cedula, nombre, id_seccion, cedula_original))
            accion = "MODIFICAR ESTUDIANTE"
        else:
            cursor.execute("INSERT OR REPLACE INTO estudiantes (cedula, nombre, id_seccion) VALUES (?, ?, ?)", (nueva_cedula, nombre, id_seccion))
            accion = "REGISTRAR ESTUDIANTE"

        conexion.commit()
        conexion.close()
        registrar_auditoria(usuario_act, accion, f"Estudiante: {nombre} ({nueva_cedula})")
        return True, "Estudiante guardado con éxito."
    except Exception as e:
        return False, f"Error: {e}"

def registrar_materia(nombre, usuario_act="Sistema"):
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("INSERT OR IGNORE INTO materias (nombre) VALUES (?)", (nombre,))
        conexion.commit()
        conexion.close()
        registrar_auditoria(usuario_act, "REGISTRAR MATERIA", f"Materia: {nombre}")
        return True
    except Exception as e:
        return False

def obtener_materias():
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("SELECT id, nombre FROM materias ORDER BY nombre")
    materias = cursor.fetchall()
    conexion.close()
    return materias

def modificar_materia(id_materia, nuevo_nombre, usuario_act="Sistema"):
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("UPDATE materias SET nombre = ? WHERE id = ?", (nuevo_nombre, id_materia))
        conexion.commit()
        conexion.close()
        registrar_auditoria(usuario_act, "MODIFICAR MATERIA", f"ID {id_materia} a '{nuevo_nombre}'")
        return True
    except Exception as e:
        return False

def eliminar_materia(id_materia, usuario_act="Sistema"):
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM materias WHERE id = ?", (id_materia,))
        conexion.commit()
        conexion.close()
        registrar_auditoria(usuario_act, "ELIMINAR MATERIA", f"ID Materia: {id_materia}")
        return True
    except Exception as e:
        return False

def guardar_o_actualizar_asistencia(cedula, fecha, estado, horas, materia, justificada, observacion, usuario_act="Sistema"):
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT id FROM estudiante_asistencias 
            WHERE cedula_estudiante = ? AND fecha = ? AND materia = ?
        """, (cedula, fecha, materia))
        existe = cursor.fetchone()

        if existe:
            id_reg = existe[0]
            cursor.execute("""
                UPDATE estudiante_asistencias 
                SET estado = ?, horas_estudio = ?, justificada = ?, observacion = ?
                WHERE id = ?
            """, (estado, horas, justificada, observacion, id_reg))
            accion = "MODIFICAR ASISTENCIA"
        else:
            cursor.execute("""
                INSERT INTO estudiante_asistencias (cedula_estudiante, fecha, estado, horas_estudio, materia, justificada, observacion)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (cedula, fecha, estado, horas, materia, justificada, observacion))
            accion = "REGISTRAR ASISTENCIA"

        conexion.commit()
        conexion.close()
        registrar_auditoria(usuario_act, accion, f"Alumno {cedula} el {fecha} ({estado})")
        return True
    except Exception as e:
        print(f"Error al guardar asistencia: {e}")
        return False

def obtener_historial_asistencias():
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("""
        SELECT a.id, e.nombre, a.cedula_estudiante, a.fecha, a.estado, a.horas_estudio, a.materia, a.justificada, a.observacion
        FROM estudiante_asistencias a
        JOIN estudiantes e ON a.cedula_estudiante = e.cedula
        ORDER BY a.fecha DESC
    """)
    registros = cursor.fetchall()
    conexion.close()
    return registros

def contar_estudiantes():
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("SELECT COUNT(*) FROM estudiantes")
    t = cursor.fetchone()[0]
    conexion.close()
    return t

def contar_docentes():
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("SELECT COUNT(*) FROM docentes")
    t = cursor.fetchone()[0]
    conexion.close()
    return t

def contar_secciones():
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("SELECT COUNT(*) FROM secciones")
    t = cursor.fetchone()[0]
    conexion.close()
    return t

def obtener_resumen_estudiantes_seccion(id_seccion=None):
    conexion = conectar()
    cursor = conexion.cursor()
    filtro = ""
    params = ()
    if id_seccion and id_seccion != "TODAS":
        filtro = "WHERE e.id_seccion = ?"
        params = (id_seccion,)
    
    query = f"""
        SELECT 
            COALESCE(s.anio || ' ' || s.seccion, 'Sin Sección') AS seccion,
            e.cedula,
            e.nombre,
            SUM(CASE WHEN a.estado = 'Presente' THEN 1 ELSE 0 END) AS total_asistencias,
            SUM(CASE WHEN a.estado = 'Inasistencia' THEN 1 ELSE 0 END) AS total_inasistencias,
            SUM(CASE WHEN a.estado = 'Presente' THEN 1 ELSE 0 END) AS horas_asistidas,
            SUM(CASE WHEN a.estado = 'Inasistencia' THEN 1 ELSE 0 END) AS horas_inasistidas
        FROM estudiantes e
        LEFT JOIN secciones s ON e.id_seccion = s.id
        LEFT JOIN estudiante_asistencias a ON e.cedula = a.cedula_estudiante
        {filtro}
        GROUP BY e.cedula, e.nombre, s.anio, s.seccion
        ORDER BY s.anio, s.seccion, e.nombre
    """
    cursor.execute(query, params)
    res = cursor.fetchall()
    conexion.close()
    return res

def reiniciar_periodo_asistencias_estudiantes(usuario_act="Sistema"):
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM estudiante_asistencias")
        conexion.commit()
        conexion.close()
        registrar_auditoria(usuario_act, "CIERRE Y RESETEO PERIODO", "Se reinició el ciclo de asistencias estudiantiles para nuevo repositorio.")
        return True
    except Exception as e:
        return False

def reiniciar_periodo_horas_docentes(usuario_act="Sistema"):
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM docente_registros_horas")
        conexion.commit()
        conexion.close()
        registrar_auditoria(usuario_act, "CIERRE Y RESETEO PERIODO", "Se reinició el ciclo de horas docentes para nuevo repositorio.")
        return True
    except Exception as e:
        return False