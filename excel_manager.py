import pandas as pd
import database as db
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


def _aplicar_estilo_hoja(ws, color_header="1E293B"):
    fill_header = PatternFill(start_color=color_header, end_color=color_header, fill_type="solid")
    fill_zebra = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_datos = Font(name="Calibri", size=11, color="0F172A")

    borde_fino = Side(border_style="thin", color="CBD5E1")
    border_celda = Border(left=borde_fino, right=borde_fino, top=borde_fino, bottom=borde_fino)

    ws.row_dimensions[1].height = 28
    for cell in ws[1]:
        cell.fill = fill_header
        cell.font = font_header
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border_celda

    for row_idx in range(2, ws.max_row + 1):
        max_lineas = 1
        for cell in ws[row_idx]:
            cell.font = font_datos
            cell.border = border_celda
            if row_idx % 2 == 0:
                cell.fill = fill_zebra
            valor_str = str(cell.value or "")
            if "\n" in valor_str:
                max_lineas = max(max_lineas, valor_str.count("\n") + 1)
            if isinstance(cell.value, (int, float)) or len(valor_str) <= 14:
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        ws.row_dimensions[row_idx].height = max(22, max_lineas * 18)

    for col_idx in range(1, ws.max_column + 1):
        letra_col = get_column_letter(col_idx)
        max_largo = 0
        for row_idx in range(1, ws.max_row + 1):
            val = ws.cell(row=row_idx, column=col_idx).value
            if val is not None:
                lineas = str(val).split("\n")
                max_largo = max(max_largo, max(len(l) for l in lineas))
        ws.column_dimensions[letra_col].width = min(max(max_largo + 6, 14), 48)

    ws.freeze_panes = "A2"


def generar_plantilla(ruta_destino):
    data = {
        "Anio": ["1er Año", "1er Año", "2do Año"],
        "Seccion": ["A", "B", "A"],
        "Coordinacion": ["Media General", "Media General", "Media General"],
        "Cedula_Estudiante": ["V-30111222", "V-30111333", "V-30111444"],
        "Nombre_Estudiante": ["Ejemplo Juan Pérez", "Ejemplo María Gómez", "Ejemplo Carlos Ruiz"]
    }
    df = pd.DataFrame(data)
    if ruta_destino.endswith(".csv"):
        df.to_csv(ruta_destino, index=False, encoding="utf-8-sig")
    else:
        with pd.ExcelWriter(ruta_destino, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Plantilla Estudiantes", index=False)
            _aplicar_estilo_hoja(writer.sheets["Plantilla Estudiantes"], color_header="1E3A8A")
    return ruta_destino


def importar_estudiantes(ruta_archivo):
    try:
        if ruta_archivo.endswith(".csv"):
            df = pd.read_csv(ruta_archivo, encoding="utf-8-sig")
        else:
            df = pd.read_excel(ruta_archivo)

        columnas_necesarias = ["Anio", "Seccion", "Coordinacion", "Cedula_Estudiante", "Nombre_Estudiante"]
        for col in columnas_necesarias:
            if col not in df.columns:
                return False, f"Falta la columna obligatoria: {col}"

        conexion = db.conectar()
        cursor = conexion.cursor()
        importados = 0

        for _, row in df.iterrows():
            anio = str(row["Anio"]).strip()
            seccion = str(row["Seccion"]).strip()
            coordinacion = str(row["Coordinacion"]).strip()
            cedula = str(row["Cedula_Estudiante"]).strip()
            nombre = str(row["Nombre_Estudiante"]).strip()

            if not cedula or cedula == "nan":
                continue

            cursor.execute("SELECT id FROM secciones WHERE anio = ? AND seccion = ?", (anio, seccion))
            res_sec = cursor.fetchone()
            if res_sec:
                id_seccion = res_sec[0]
            else:
                cursor.execute("INSERT INTO secciones (anio, seccion, coordinacion) VALUES (?, ?, ?)", (anio, seccion, coordinacion))
                id_seccion = cursor.lastrowid

            cursor.execute("INSERT OR REPLACE INTO estudiantes (cedula, nombre, id_seccion) VALUES (?, ?, ?)", (cedula, nombre, id_seccion))
            importados += 1

        conexion.commit()
        conexion.close()
        return True, f"¡Se importaron {importados} estudiantes con éxito!"
    except Exception as e:
        return False, f"Error al procesar archivo: {e}"


def exportar_reporte_docentes(ruta_destino):
    try:
        conexion = db.conectar()
        query_resumen = """
            SELECT d.cedula AS "Cédula", d.nombre AS "Docente", d.materia AS "Materia / Área",
                   COUNT(h.id) AS "Días Registrados", COALESCE(SUM(h.horas), 0) AS "Total Horas Trabajadas"
            FROM docentes d LEFT JOIN docente_registros_horas h ON d.cedula = h.cedula_docente
            GROUP BY d.cedula, d.nombre, d.materia ORDER BY d.nombre
        """
        df_resumen = pd.read_sql_query(query_resumen, conexion)
        query_detalle = """
            SELECT h.fecha AS "Fecha", d.cedula AS "Cédula", d.nombre AS "Docente", d.materia AS "Materia / Área", h.horas AS "Horas de Jornada"
            FROM docente_registros_horas h JOIN docentes d ON h.cedula_docente = d.cedula ORDER BY h.fecha DESC, d.nombre
        """
        df_detalle = pd.read_sql_query(query_detalle, conexion)
        conexion.close()

        if ruta_destino.endswith(".csv"):
            df_resumen.to_csv(ruta_destino, index=False, encoding="utf-8-sig")
        else:
            with pd.ExcelWriter(ruta_destino, engine="openpyxl") as writer:
                df_resumen.to_excel(writer, sheet_name="Resumen Consolidado", index=False)
                df_detalle.to_excel(writer, sheet_name="Detalle Diario", index=False)
                _aplicar_estilo_hoja(writer.sheets["Resumen Consolidado"], color_header="14532D")
                _aplicar_estilo_hoja(writer.sheets["Detalle Diario"], color_header="1E293B")
        return True, f"Reporte exportado en:\n{ruta_destino}"
    except Exception as e:
        return False, f"Error: {e}"


def exportar_reporte_asistencias(ruta_destino, id_seccion=None):
    try:
        conexion = db.conectar()
        filtro_sql = ""
        params = ()
        if id_seccion and id_seccion != "TODAS":
            filtro_sql = "WHERE e.id_seccion = ?"
            params = (id_seccion,)

        query_resumen = f"""
            SELECT e.cedula AS "Cédula", e.nombre AS "Estudiante", COALESCE(s.anio || ' ' || s.seccion, 'Sin Sección') AS "Sección",
                   SUM(CASE WHEN a.estado = 'Presente' THEN 1 ELSE 0 END) AS "Total Asistencias",
                   SUM(CASE WHEN a.estado = 'Inasistencia' THEN 1 ELSE 0 END) AS "Total Inasistencias",
                   SUM(CASE WHEN a.estado = 'Inasistencia' AND a.justificada = 'Sí' THEN 1 ELSE 0 END) AS "Justificadas",
                   SUM(CASE WHEN a.estado = 'Inasistencia' AND a.justificada = 'No' THEN 1 ELSE 0 END) AS "Injustificadas",
                   COALESCE(GROUP_CONCAT(CASE WHEN a.observacion IS NOT NULL AND TRIM(a.observacion) != '' THEN '[' || a.fecha || '] ' || TRIM(a.observacion) END, CHAR(10)), 'Sin observaciones') AS "Observaciones Registradas"
            FROM estudiantes e LEFT JOIN secciones s ON e.id_seccion = s.id LEFT JOIN estudiante_asistencias a ON e.cedula = a.cedula_estudiante
            {filtro_sql} GROUP BY e.cedula, e.nombre, s.anio, s.seccion ORDER BY s.anio, s.seccion, e.nombre
        """
        df_resumen = pd.read_sql_query(query_resumen, conexion, params=params)
        
        query_detalle = f"""
            SELECT a.fecha AS "Fecha", COALESCE(s.anio || ' ' || s.seccion, 'Sin Sección') AS "Sección", e.cedula AS "Cédula", e.nombre AS "Estudiante", a.materia AS "Materia", a.estado AS "Estado", a.horas_estudio AS "Horas de Estudio", a.justificada AS "Justificada", COALESCE(NULLIF(TRIM(a.observacion), ''), '—') AS "Observación"
            FROM estudiante_asistencias a JOIN estudiantes e ON a.cedula_estudiante = e.cedula LEFT JOIN secciones s ON e.id_seccion = s.id
            {filtro_sql} ORDER BY a.fecha DESC, s.anio, s.seccion, e.nombre
        """
        df_detalle = pd.read_sql_query(query_detalle, conexion, params=params)
        conexion.close()

        if ruta_destino.endswith(".csv"):
            df_resumen.to_csv(ruta_destino, index=False, encoding="utf-8-sig")
        else:
            with pd.ExcelWriter(ruta_destino, engine="openpyxl") as writer:
                df_resumen.to_excel(writer, sheet_name="Resumen por Estudiante", index=False)
                df_detalle.to_excel(writer, sheet_name="Historial Detallado", index=False)
                _aplicar_estilo_hoja(writer.sheets["Resumen por Estudiante"], color_header="1E3A8A")
                _aplicar_estilo_hoja(writer.sheets["Historial Detallado"], color_header="1E293B")
        return True, f"Reporte exportado en:\n{ruta_destino}"
    except Exception as e:
        return False, f"Error: {e}"


def exportar_repositorio_completo(ruta_destino):
    """Exporta el repositorio completo dividido en hojas independientes por cada sección y año en Excel."""
    try:
        conexion = db.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT id, anio, seccion FROM secciones ORDER BY anio, seccion")
        secciones = cursor.fetchall()

        if ruta_destino.endswith(".csv"):
            query = """
                SELECT 
                    COALESCE(s.anio, 'Sin Año') AS "Año",
                    COALESCE(s.seccion, 'Sin Sección') AS "Sección",
                    e.cedula AS "Cédula",
                    e.nombre AS "Estudiante",
                    SUM(CASE WHEN a.estado = 'Presente' THEN 1 ELSE 0 END) AS "Total Asistencias",
                    SUM(CASE WHEN a.estado = 'Inasistencia' THEN 1 ELSE 0 END) AS "Total Inasistencias",
                    SUM(CASE WHEN a.estado = 'Inasistencia' AND a.justificada = 'Sí' THEN 1 ELSE 0 END) AS "Justificadas",
                    SUM(CASE WHEN a.estado = 'Inasistencia' AND a.justificada = 'No' THEN 1 ELSE 0 END) AS "Injustificadas"
                FROM estudiantes e
                LEFT JOIN secciones s ON e.id_seccion = s.id
                LEFT JOIN estudiante_asistencias a ON e.cedula = a.cedula_estudiante
                GROUP BY e.cedula, e.nombre, s.anio, s.seccion
                ORDER BY s.anio, s.seccion, e.nombre
            """
            df = pd.read_sql_query(query, conexion)
            conexion.close()
            df.to_csv(ruta_destino, index=False, encoding="utf-8-sig")
            return True, f"Repositorio exportado en CSV:\n{ruta_destino}"
        else:
            with pd.ExcelWriter(ruta_destino, engine="openpyxl") as writer:
                for id_s, anio, sec in secciones:
                    nombre_hoja = f"{anio}_{sec}".replace(" ", "_")
                    query_sec = """
                        SELECT 
                            e.cedula AS "Cédula",
                            e.nombre AS "Estudiante",
                            SUM(CASE WHEN a.estado = 'Presente' THEN 1 ELSE 0 END) AS "Total Asistencias",
                            SUM(CASE WHEN a.estado = 'Inasistencia' THEN 1 ELSE 0 END) AS "Total Inasistencias",
                            SUM(CASE WHEN a.estado = 'Inasistencia' AND a.justificada = 'Sí' THEN 1 ELSE 0 END) AS "Justificadas",
                            SUM(CASE WHEN a.estado = 'Inasistencia' AND a.justificada = 'No' THEN 1 ELSE 0 END) AS "Injustificadas",
                            COALESCE(
                                GROUP_CONCAT(
                                    CASE 
                                        WHEN a.observacion IS NOT NULL AND TRIM(a.observacion) != '' 
                                        THEN '[' || a.fecha || '] ' || TRIM(a.observacion) 
                                    END, 
                                    CHAR(10)
                                ), 
                                'Sin observaciones'
                            ) AS "Observaciones Registradas"
                        FROM estudiantes e
                        LEFT JOIN estudiante_asistencias a ON e.cedula = a.cedula_estudiante
                        WHERE e.id_seccion = ?
                        GROUP BY e.cedula, e.nombre
                        ORDER BY e.nombre
                    """
                    df_sec = pd.read_sql_query(query_sec, conexion, params=(id_s,))
                    df_sec.to_excel(writer, sheet_name=nombre_hoja, index=False)
                    _aplicar_estilo_hoja(writer.sheets[nombre_hoja], color_header="1E3A8A")

                query_doc = """
                    SELECT 
                        d.cedula AS "Cédula",
                        d.nombre AS "Docente",
                        d.materia AS "Materia / Área",
                        COALESCE(SUM(h.horas), 0) AS "Total Horas Trabajadas"
                    FROM docentes d
                    LEFT JOIN docente_registros_horas h ON d.cedula = h.cedula_docente
                    GROUP BY d.cedula, d.nombre, d.materia
                    ORDER BY d.nombre
                """
                df_doc = pd.read_sql_query(query_doc, conexion)
                df_doc.to_excel(writer, sheet_name="Docentes", index=False)
                _aplicar_estilo_hoja(writer.sheets["Docentes"], color_header="14532D")

            conexion.close()
            return True, f"Repositorio exportado con éxito en Excel (dividido por secciones):\n{ruta_destino}"
    except Exception as e:
        return False, f"Error al exportar repositorio: {e}"