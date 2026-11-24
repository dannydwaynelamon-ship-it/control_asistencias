import asyncio
import flet as ft
import database as db
import excel_manager as em
from datetime import date


def main(page: ft.Page):
    db.inicializar_bd()

    page.title = "Sistema de Control de Asistencia - Colegio"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.window.width = 1250
    page.window.height = 800

    file_picker = ft.FilePicker()
    page.services.append(file_picker)

    sesion_actual = {"usuario": None, "nombre": None, "rol": None}

    tiempo_inactivo = {"segundos": 0}
    max_inactividad = 600

    def reiniciar_inactividad(e=None):
        tiempo_inactivo["segundos"] = 0

    page.on_keyboard_event = reiniciar_inactividad

    async def vigilar_inactividad():
        try:
            while True:
                await asyncio.sleep(1)
                if sesion_actual["usuario"]:
                    tiempo_inactivo["segundos"] += 1
                    if tiempo_inactivo["segundos"] >= max_inactividad:
                        tiempo_inactivo["segundos"] = 0
                        sesion_actual["usuario"] = None
                        try:
                            mostrar_login()
                        except Exception:
                            pass
        except asyncio.CancelledError:
            pass

    page.run_task(vigilar_inactividad)

    def mostrar_dashboard(rol_efectivo):
        page.clean()

        contenido_principal = ft.Container(
            content=ft.Column([], alignment=ft.MainAxisAlignment.START, scroll=ft.ScrollMode.AUTO),
            padding=25,
            expand=True
        )

        def cambiar_vista(e, titulo):
            reiniciar_inactividad()
            if titulo == "Resumen":
                total_est = db.contar_estudiantes()
                total_doc = db.contar_docentes()
                total_sec = db.contar_secciones()

                tarjeta_est = ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.PEOPLE, size=30, color=ft.Colors.BLUE_700),
                        ft.Text("Estudiantes Registrados", size=14, color=ft.Colors.GREY_700),
                        ft.Text(str(total_est), size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900)
                    ], spacing=5),
                    bgcolor=ft.Colors.BLUE_50, padding=20, border_radius=10, width=230
                )

                tarjeta_doc = ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.SCHOOL, size=30, color=ft.Colors.GREEN_700),
                        ft.Text("Docentes Activos", size=14, color=ft.Colors.GREY_700),
                        ft.Text(str(total_doc), size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_900)
                    ], spacing=5),
                    bgcolor=ft.Colors.GREEN_50, padding=20, border_radius=10, width=230
                )

                tarjeta_sec = ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.BOOK, size=30, color=ft.Colors.ORANGE_700),
                        ft.Text("Secciones Creadas", size=14, color=ft.Colors.GREY_700),
                        ft.Text(str(total_sec), size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE_900)
                    ], spacing=5),
                    bgcolor=ft.Colors.ORANGE_50, padding=20, border_radius=10, width=230
                )

                contenido_principal.content.controls = [
                    ft.Text(f"Panel Principal — Usuario: {sesion_actual['nombre']} ({sesion_actual['rol'].upper()})", size=24, weight=ft.FontWeight.BOLD),
                    ft.Text("Resumen general del estado actual de la institución.", color=ft.Colors.GREY_700),
                    ft.Divider(height=20),
                    ft.Row([tarjeta_est, tarjeta_doc, tarjeta_sec], spacing=15, wrap=True),
                    ft.Divider(height=25),
                    ft.Text("📌 Actividad Reciente del Sistema", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text(
                        "• Base de datos SQLite sincronizada correctamente.\n"
                        "• Módulo de repositorio y control institucional activos.",
                        color=ft.Colors.GREY_800
                    )
                ]

            elif titulo == "Asistencia":
                modo_asist = ft.RadioGroup(
                    content=ft.Row([
                        ft.Radio(value="Individual", label="👤 Registro Individual"),
                        ft.Radio(value="Masiva", label="👥 Registro Masivo por Sección")
                    ], spacing=20),
                    value="Individual"
                )

                contenedor_modo = ft.Column(spacing=15)

                def renderizar_modo_asistencia(e=None):
                    contenedor_modo.controls.clear()

                    if modo_asist.value == "Individual":
                        lbl_msg_asist = ft.Text("", size=13)

                        txt_nueva_materia = ft.TextField(label="Nueva Materia", width=180)
                        lista_materias_view = ft.Column(spacing=4)

                        def actualizar_lista_mat():
                            lista_materias_view.controls.clear()
                            for id_m, nom_m in db.obtener_materias():
                                txt_mod = ft.TextField(value=nom_m, width=140, height=35, text_size=12)
                                def guardar_m(ev, im=id_m, tm=txt_mod):
                                    if tm.value:
                                        db.modificar_materia(im, tm.value, sesion_actual["usuario"])
                                        actualizar_lista_mat()
                                        act_mat_drop()
                                lista_materias_view.controls.append(ft.Row([
                                    txt_mod,
                                    ft.IconButton(icon=ft.Icons.SAVE, icon_size=16, on_click=guardar_m),
                                    ft.IconButton(icon=ft.Icons.DELETE, icon_size=16, icon_color=ft.Colors.RED, on_click=lambda ev, im=id_m: (db.eliminar_materia(im, sesion_actual["usuario"]), actualizar_lista_mat(), act_mat_drop()))
                                ], spacing=2))
                            page.update()

                        def agregar_mat(ev):
                            if txt_nueva_materia.value:
                                db.registrar_materia(txt_nueva_materia.value, sesion_actual["usuario"])
                                txt_nueva_materia.value = ""
                                actualizar_lista_mat()
                                act_mat_drop()

                        panel_mat = ft.ExpansionTile(
                            title=ft.Text("⚙️ Administrar Materias (Exclusivo Administrador)", size=13, weight=ft.FontWeight.BOLD),
                            controls=[ft.Container(content=ft.Column([
                                ft.Row([txt_nueva_materia, ft.Button("Añadir", on_click=agregar_mat)], spacing=10),
                                lista_materias_view
                            ]), padding=8, bgcolor=ft.Colors.BLUE_GREY_50, border_radius=6)],
                            visible=(sesion_actual["rol"] == "admin")
                        )

                        estudiantes_reg = db.obtener_estudiantes()
                        cedula_seleccionada = {"valor": None}
                        txt_buscar_alumno = ft.TextField(label="Buscar Estudiante (Nombre o Cédula)", prefix_icon=ft.Icons.SEARCH, width=320)
                        lbl_elegido = ft.Text("Ningún alumno seleccionado", size=12, italic=True, color=ft.Colors.GREY_600)

                        lista_sugerencias = ft.Column(spacing=2)
                        panel_sug = ft.Container(content=lista_sugerencias, bgcolor=ft.Colors.WHITE, border=ft.Border.all(1, ft.Colors.BLUE_200), border_radius=6, padding=5, width=320, visible=False)

                        def seleccionar_alumno(ced, nom):
                            cedula_seleccionada["valor"] = ced
                            txt_buscar_alumno.value = f"[{ced}] {nom}"
                            lbl_elegido.value = f"✅ Seleccionado: {nom} ({ced})"
                            lbl_elegido.color = ft.Colors.GREEN_700
                            lbl_elegido.italic = False
                            panel_sug.visible = False
                            page.update()

                        def filtrar_alumnos(ev):
                            termino = (txt_buscar_alumno.value or "").strip().lower()
                            cedula_seleccionada["valor"] = None
                            lista_sugerencias.controls.clear()
                            if not termino:
                                panel_sug.visible = False
                                lbl_elegido.value = "Ningún alumno seleccionado"
                                lbl_elegido.color = ft.Colors.GREY_600
                                lbl_elegido.italic = True
                                page.update()
                                return
                            coincidencias = [(c, n) for c, n in estudiantes_reg if termino in c.lower() or termino in n.lower()][:6]
                            if coincidencias:
                                for c, n in coincidencias:
                                    lista_sugerencias.controls.append(ft.TextButton(content=f"[{c}] {n}", on_click=lambda e, cc=c, nn=n: seleccionar_alumno(cc, nn)))
                                panel_sug.visible = True
                            else:
                                panel_sug.visible = False
                            page.update()

                        txt_buscar_alumno.on_change = filtrar_alumnos
                        bloque_buscador = ft.Column([txt_buscar_alumno, panel_sug, lbl_elegido], spacing=2)

                        txt_fecha = ft.TextField(label="Fecha", value=date.today().strftime("%Y-%m-%d"), width=150)
                        drop_estado = ft.Dropdown(label="Estado", options=[ft.dropdown.Option("Presente"), ft.dropdown.Option("Inasistencia")], value="Presente", width=140)
                        drop_horas = ft.Dropdown(label="Horas", options=[ft.dropdown.Option("1h"), ft.dropdown.Option("1:30h"), ft.dropdown.Option("2h"), ft.dropdown.Option("Manual")], value="1h", width=130)
                        txt_hrs_man = ft.TextField(label="Escribir Horas", width=120, visible=False)
                        drop_horas.on_select = lambda e: (setattr(txt_hrs_man, "visible", drop_horas.value == "Manual"), page.update())

                        drop_materia = ft.Dropdown(label="Materia", width=200)
                        def act_mat_drop():
                            mats = db.obtener_materias()
                            drop_materia.options = [ft.dropdown.Option(m[1]) for m in mats]
                            if mats and not drop_materia.value:
                                drop_materia.value = mats[0][1]
                            page.update()

                        drop_just = ft.Dropdown(label="¿Justificada?", options=[ft.dropdown.Option("Sí"), ft.dropdown.Option("No")], value="No", width=130)
                        cont_just = ft.Container(content=drop_just, visible=False)
                        drop_estado.on_select = lambda e: (setattr(cont_just, "visible", drop_estado.value == "Inasistencia"), page.update())

                        txt_obs = ft.TextField(label="Observación", width=300)
                        tabla_hist = ft.Column(spacing=6)

                        def cargar_hist():
                            tabla_hist.controls.clear()
                            for id_r, nom_e, ced_e, f_reg, est, hrs, mat, jst, obs in db.obtener_historial_asistencias():
                                icono = "🟢" if est == "Presente" else "🔴"
                                tabla_hist.controls.append(ft.Container(
                                    content=ft.Text(f"📅 {f_reg} | {nom_e} ({ced_e}) | {icono} {est} ({hrs}) | Mat: {mat} | Obs: {obs or '—'}", size=12),
                                    bgcolor=ft.Colors.GREY_100, padding=6, border_radius=5
                                ))
                            page.update()

                        def guardar_individual(ev):
                            if not cedula_seleccionada["valor"]:
                                lbl_msg_asist.value = "Selecciona un estudiante del buscador."
                                lbl_msg_asist.color = ft.Colors.RED
                                page.update()
                                return
                            hrs_fin = txt_hrs_man.value if drop_horas.value == "Manual" and txt_hrs_man.value else drop_horas.value
                            db.guardar_o_actualizar_asistencia(cedula_seleccionada["valor"], txt_fecha.value, drop_estado.value, hrs_fin, drop_materia.value or "General", drop_just.value if drop_estado.value == "Inasistencia" else "N/A", txt_obs.value, usuario_act=sesion_actual["usuario"])
                            lbl_msg_asist.value = "¡Asistencia registrada con éxito!"
                            lbl_msg_asist.color = ft.Colors.GREEN
                            txt_obs.value = ""
                            cargar_hist()
                            page.update()

                        btn_guardar_ind = ft.Button("Guardar Asistencia", icon=ft.Icons.SAVE, bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE, on_click=guardar_individual)

                        act_mat_drop()
                        cargar_hist()
                        actualizar_lista_mat()

                        contenedor_modo.controls.extend([
                            panel_mat,
                            ft.Divider(height=10),
                            ft.Row([bloque_buscador, txt_fecha, drop_estado], spacing=10, wrap=True),
                            ft.Row([drop_horas, txt_hrs_man, drop_materia, cont_just], spacing=10, vertical_alignment=ft.CrossAxisAlignment.END, wrap=True),
                            ft.Row([txt_obs, btn_guardar_ind], spacing=10, vertical_alignment=ft.CrossAxisAlignment.END, wrap=True),
                            lbl_msg_asist,
                            ft.Divider(height=15),
                            ft.Text("Historial de Asistencias:", weight=ft.FontWeight.BOLD),
                            tabla_hist
                        ])

                    else:
                        secciones = db.obtener_secciones()
                        opciones_s = [ft.dropdown.Option(str(s[0]), f"{s[1]} - Sección '{s[2]}'") for s in secciones]
                        drop_sec_m = ft.Dropdown(label="Seleccionar Sección", options=opciones_s, width=280)
                        txt_fec_m = ft.TextField(label="Fecha", value=date.today().strftime("%Y-%m-%d"), width=150)
                        drop_mat_m = ft.Dropdown(label="Materia", width=200)

                        def act_mat_m():
                            mats = db.obtener_materias()
                            drop_mat_m.options = [ft.dropdown.Option(m[1]) for m in mats]
                            if mats and not drop_mat_m.value:
                                drop_mat_m.value = mats[0][1]
                            page.update()

                        lista_alumnos_masivo = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, height=350)
                        lbl_msg_masiva = ft.Text("", size=13)
                        controles_masivos = {}

                        def cargar_alumnos_masivos(ev):
                            lista_alumnos_masivo.controls.clear()
                            controles_masivos.clear()
                            if not drop_sec_m.value:
                                page.update()
                                return
                            for ced, nom in db.obtener_estudiantes_por_seccion(int(drop_sec_m.value)):
                                chk = ft.Checkbox(label="Presente", value=True)
                                dr_h = ft.Dropdown(options=[ft.dropdown.Option("1h"), ft.dropdown.Option("1:30h"), ft.dropdown.Option("2h")], value="1h", width=95)
                                dr_j = ft.Dropdown(options=[ft.dropdown.Option("N/A"), ft.dropdown.Option("Sí"), ft.dropdown.Option("No")], value="N/A", width=90)
                                tx_o = ft.TextField(label="Obs", width=160, height=35, text_size=12)
                                controles_masivos[ced] = {"chk": chk, "hrs": dr_h, "just": dr_j, "obs": tx_o}
                                lista_alumnos_masivo.controls.append(ft.Container(
                                    content=ft.Row([ft.Text(f"[{ced}] {nom}", width=240, size=13), chk, ft.Text("Horas:"), dr_h, ft.Text("Just:"), dr_j, tx_o], spacing=8, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                    bgcolor=ft.Colors.GREY_100, padding=6, border_radius=5
                                ))
                            page.update()

                        drop_sec_m.on_select = cargar_alumnos_masivos
                        act_mat_m()

                        def guardar_masivo(ev):
                            if not drop_sec_m.value or not drop_mat_m.value:
                                return
                            for ced, comps in controles_masivos.items():
                                est = "Presente" if comps["chk"].value else "Inasistencia"
                                db.guardar_o_actualizar_asistencia(ced, txt_fec_m.value, est, comps["hrs"].value, drop_mat_m.value, comps["just"].value if est == "Inasistencia" else "N/A", comps["obs"].value, usuario_act=sesion_actual["usuario"])
                            lbl_msg_masiva.value = "¡Asistencias guardadas con éxito!"
                            lbl_msg_masiva.color = ft.Colors.GREEN_700
                            page.update()

                        btn_guardar_m = ft.Button("Guardar las Asistencias", icon=ft.Icons.SAVE, bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE, on_click=guardar_masivo)

                        contenedor_modo.controls.extend([
                            ft.Row([drop_sec_m, drop_mat_m, txt_fec_m], spacing=10, wrap=True),
                            ft.Row([btn_guardar_m, lbl_msg_masiva], spacing=15, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                            ft.Divider(height=10),
                            lista_alumnos_masivo
                        ])

                    page.update()

                modo_asist.on_change = renderizar_modo_asistencia
                renderizar_modo_asistencia()

                contenido_principal.content.controls = [
                    ft.Text("Control de Asistencia Estudiantil", size=22, weight=ft.FontWeight.BOLD),
                    ft.Text("Selecciona el modo de registro deseado:", color=ft.Colors.GREY_700),
                    ft.Divider(height=10),
                    modo_asist,
                    ft.Divider(height=10),
                    contenedor_modo
                ]

            elif titulo == "Repositorio y Estadísticas":
                lbl_estado_repo = ft.Text("", size=13)

                tabla_repo_est = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, height=360)
                tabla_repo_doc = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, height=360)

                def cargar_datos_repositorio():
                    tabla_repo_est.controls.clear()
                    tabla_repo_doc.controls.clear()

                    res_est = db.obtener_resumen_estudiantes_seccion()
                    if not res_est:
                        tabla_repo_est.controls.append(ft.Text("No hay registros estadísticos de estudiantes.", italic=True))
                    else:
                        secciones_dict = {}
                        for sec, ced, nom, asis, inas, h_asis, h_inas in res_est:
                            if sec not in secciones_dict:
                                secciones_dict[sec] = []
                            secciones_dict[sec].append((ced, nom, asis, inas, h_asis, h_inas))

                        for sec_nombre, alumnos in secciones_dict.items():
                            filas_alumnos = []
                            for ced, nom, asis, inas, h_asis, h_inas in alumnos:
                                filas_alumnos.append(
                                    ft.Container(
                                        content=ft.Row([
                                            ft.Text(f"[{ced}] {nom}", width=260, weight=ft.FontWeight.W_500, size=13),
                                            ft.Text(f"✅ Asis: {asis or 0}", width=110, size=12),
                                            ft.Text(f"❌ Inas: {inas or 0}", width=110, size=12),
                                            ft.Text(f"⏱️ H.Asis: {h_asis or 0}", width=110, size=12),
                                            ft.Text(f"⏳ H.Inas: {h_inas or 0}", width=110, size=12)
                                        ], spacing=5, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                        bgcolor=ft.Colors.WHITE, padding=6, border_radius=5
                                    )
                                )

                            bloque_sec = ft.ExpansionTile(
                                title=ft.Row([
                                    ft.Icon(ft.Icons.BOOK, color=ft.Colors.BLUE_800, size=20),
                                    ft.Text(f"Sección: {sec_nombre} ({len(alumnos)} alumnos)", weight=ft.FontWeight.BOLD, size=14)
                                ], spacing=8),
                                controls=[ft.Column(filas_alumnos, spacing=4)],
                                expanded=True
                            )
                            tabla_repo_est.controls.append(bloque_sec)

                    res_doc = db.obtener_docentes()
                    if not res_doc:
                        tabla_repo_doc.controls.append(ft.Text("No hay registros de docentes.", italic=True))
                    else:
                        historial_h = db.obtener_historial_horas()
                        totales_doc = {}
                        for _, nom_d, ced_d, _, hrs in historial_h:
                            totales_doc[ced_d] = totales_doc.get(ced_d, 0) + hrs

                        for ced, nom, mat, _ in res_doc:
                            total_h = totales_doc.get(ced, 0)
                            tabla_repo_doc.controls.append(ft.Container(
                                content=ft.Row([
                                    ft.Text(f"[{ced}] {nom}", width=250, weight=ft.FontWeight.BOLD),
                                    ft.Text(f"📚 {mat}", width=200),
                                    ft.Text(f"⏱️ Total Horas Registradas: {total_h}", width=200)
                                ], spacing=10),
                                bgcolor=ft.Colors.GREEN_50, padding=8, border_radius=6
                            ))
                    page.update()

                cargar_datos_repositorio()

                async def guardar_respaldo_repositorio(e):
                    ruta = await file_picker.save_file(
                        file_name=f"Repositorio_Institucional_{date.today().strftime('%Y-%m-%d')}.xlsx",
                        file_type=ft.FilePickerFileType.CUSTOM,
                        allowed_extensions=["xlsx", "csv"]
                    )
                    if ruta:
                        exito, msg = em.exportar_repositorio_completo(ruta)
                        if exito:
                            db.reiniciar_periodo_asistencias_estudiantes(sesion_actual["usuario"])
                            db.reiniciar_periodo_horas_docentes(sesion_actual["usuario"])
                            lbl_estado_repo.value = "¡Cierre de periodo ejecutado y ciclo reiniciado con éxito!"
                            lbl_estado_repo.color = ft.Colors.GREEN_700
                            cargar_datos_repositorio()
                        else:
                            lbl_estado_repo.value = msg
                            lbl_estado_repo.color = ft.Colors.RED
                        page.update()

                btn_cierre = ft.Button(
                    "Realizar Cierre de Periodo y Reiniciar Ciclo",
                    icon=ft.Icons.ARCHIVE,
                    bgcolor=ft.Colors.ORANGE_800,
                    color=ft.Colors.WHITE,
                    on_click=guardar_respaldo_repositorio
                )

                tab_repo = ft.Tabs(
                    length=2,
                    selected_index=0,
                    animation_duration=300,
                    content=ft.Column([
                        ft.TabBar(
                            tabs=[
                                ft.Tab(label="Estadísticas Estudiantes"),
                                ft.Tab(label="Estadísticas Docentes"),
                            ]
                        ),
                        ft.TabBarView(
                            controls=[
                                ft.Column([ft.Divider(height=10), tabla_repo_est], spacing=5),
                                ft.Column([ft.Divider(height=10), tabla_repo_doc], spacing=5),
                            ],
                            height=390
                        )
                    ])
                )

                contenido_principal.content.controls = [
                    ft.Text("Repositorio y Estadísticas Institucionales", size=22, weight=ft.FontWeight.BOLD),
                    ft.Text("Visualiza el acumulado de asistencias, inasistencias y horas agrupadas por salón.", color=ft.Colors.GREY_700),
                    ft.Divider(height=10),
                    ft.Row([btn_cierre, lbl_estado_repo], spacing=15, vertical_alignment=ft.CrossAxisAlignment.CENTER, wrap=True),
                    ft.Divider(height=10),
                    tab_repo
                ]

            elif titulo == "Estudiantes":
                lbl_estado_excel = ft.Text("", size=13)
                tabla_estudiantes_view = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, height=310)
                lbl_contador_est = ft.Text("", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_700)

                cedula_en_edicion = {"valor": None}
                txt_est_cedula = ft.TextField(label="Cédula", width=160)
                txt_est_nombre = ft.TextField(label="Nombre y Apellido", width=230)
                txt_est_anio = ft.TextField(label="Año (Ej: 1er Año)", width=170)
                txt_est_seccion = ft.TextField(label="Sección (Ej: A)", width=115)
                txt_est_coord = ft.TextField(label="Coordinación", value="Media General", width=160)
                lbl_msg_form_est = ft.Text("", size=12)

                btn_guardar_est_ind = ft.Button("Guardar Estudiante", icon=ft.Icons.PERSON_ADD, bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE)
                btn_cancelar_edicion = ft.TextButton("Cancelar", visible=False)

                panel_form_estudiante = ft.ExpansionTile(
                    title=ft.Text("✏️ Registrar o Modificar Estudiante Individual", size=14, weight=ft.FontWeight.BOLD),
                    controls=[
                        ft.Container(
                            content=ft.Column([
                                ft.Row([txt_est_cedula, txt_est_nombre, txt_est_anio, txt_est_seccion, txt_est_coord], spacing=10, wrap=True),
                                ft.Row([btn_guardar_est_ind, btn_cancelar_edicion, lbl_msg_form_est], spacing=10)
                            ], spacing=10),
                            padding=12, bgcolor=ft.Colors.BLUE_GREY_50, border_radius=8
                        )
                    ]
                )

                def limpiar_form(e=None):
                    cedula_en_edicion["valor"] = None
                    txt_est_cedula.value = ""
                    txt_est_nombre.value = ""
                    txt_est_anio.value = ""
                    txt_est_seccion.value = ""
                    btn_guardar_est_ind.content = "Guardar Estudiante"
                    btn_cancelar_edicion.visible = False
                    page.update()

                btn_cancelar_edicion.on_click = limpiar_form

                def iniciar_edicion(ced, nom, anio, sec, coord):
                    cedula_en_edicion["valor"] = ced
                    txt_est_cedula.value = ced
                    txt_est_nombre.value = nom
                    txt_est_anio.value = anio or ""
                    txt_est_seccion.value = sec or ""
                    txt_est_coord.value = coord or "Media General"
                    btn_guardar_est_ind.content = "Actualizar Datos"
                    btn_cancelar_edicion.visible = True
                    panel_form_estudiante.expanded = True
                    page.update()

                def guardar_ind(e):
                    if not txt_est_cedula.value or not txt_est_nombre.value or not txt_est_anio.value or not txt_est_seccion.value:
                        lbl_msg_form_est.value = "Complete los campos obligatorios."
                        lbl_msg_form_est.color = ft.Colors.RED
                        page.update()
                        return

                    exito, msg = db.guardar_o_editar_estudiante(
                        cedula_en_edicion["valor"], txt_est_cedula.value.strip(), txt_est_nombre.value.strip(),
                        txt_est_anio.value.strip(), txt_est_seccion.value.strip(), txt_est_coord.value.strip(),
                        usuario_act=sesion_actual["usuario"]
                    )
                    if exito:
                        limpiar_form()
                        refrescar_directorio()
                    else:
                        lbl_msg_form_est.value = msg
                        lbl_msg_form_est.color = ft.Colors.RED
                        page.update()

                btn_guardar_est_ind.on_click = guardar_ind

                modo_vista_est = ft.Dropdown(
                    label="Modo de Vista",
                    options=[ft.dropdown.Option("LISTA"), ft.dropdown.Option("AGRUPADA")],
                    value="AGRUPADA", width=200
                )
                dropdown_filtro_seccion = ft.Dropdown(label="Filtrar Sección", width=210, value="TODAS", visible=False)
                txt_buscar_est = ft.TextField(label="Buscar Alumno", width=240, prefix_icon=ft.Icons.SEARCH)

                def cargar_opciones_sec():
                    secs = db.obtener_secciones()
                    opciones = [ft.dropdown.Option("TODAS", "Todas")]
                    for id_s, anio, sec, _ in secs:
                        opciones.append(ft.dropdown.Option(str(id_s), f"{anio} - '{sec}'"))
                    dropdown_filtro_seccion.options = opciones

                def construir_fila(ced, nom, anio, sec, coord, mostrar_badge=True):
                    btn_ed = ft.IconButton(icon=ft.Icons.EDIT_OUTLINED, icon_color=ft.Colors.BLUE_700, icon_size=18, on_click=lambda e: iniciar_edicion(ced, nom, anio, sec, coord))
                    btn_el = ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE, icon_color=ft.Colors.RED_400, icon_size=18,
                        visible=(sesion_actual["rol"] == "admin"),
                        on_click=lambda e: (db.eliminar_estudiante(ced, sesion_actual["usuario"]), refrescar_directorio())
                    )

                    izq = [ft.Icon(ft.Icons.PERSON, size=18, color=ft.Colors.BLUE_700), ft.Text(f"[{ced}]", weight=ft.FontWeight.BOLD, size=13, width=105), ft.Text(nom, size=13, width=220)]
                    if mostrar_badge:
                        izq.append(ft.Container(content=ft.Text(f"{anio} '{sec}'", size=11), bgcolor=ft.Colors.BLUE_50, padding=5, border_radius=5))

                    return ft.Container(
                        content=ft.Row([ft.Row(izq, spacing=8, wrap=True), ft.Row([btn_ed, btn_el], spacing=2)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        bgcolor=ft.Colors.GREY_100, padding=6, border_radius=6
                    )

                def refrescar_directorio(e=None):
                    tabla_estudiantes_view.controls.clear()
                    busqueda = txt_buscar_est.value.strip().lower() if txt_buscar_est.value else ""
                    dropdown_filtro_seccion.visible = (modo_vista_est.value == "LISTA")

                    if modo_vista_est.value == "LISTA":
                        estudiantes = db.obtener_estudiantes_detallado(dropdown_filtro_seccion.value, busqueda)
                        lbl_contador_est.value = f"Mostrando {len(estudiantes)} estudiante(s)"
                        for ced, nom, anio, sec, coord in estudiantes:
                            tabla_estudiantes_view.controls.append(construir_fila(ced, nom, anio, sec, coord, True))
                    else:
                        agrupados = db.obtener_estudiantes_agrupados_por_seccion()
                        total = 0
                        for (id_s, anio, sec, coord), lista in agrupados.items():
                            filtrados = [(c, n) for c, n in lista if not busqueda or busqueda in c.lower() or busqueda in n.lower()]
                            if busqueda and not filtrados:
                                continue
                            total += len(filtrados)
                            filas_salon = [construir_fila(c, n, anio, sec, coord, False) for c, n in filtrados]

                            bloque = ft.ExpansionTile(
                                title=ft.Row([ft.Icon(ft.Icons.BOOK, color=ft.Colors.BLUE_800), ft.Text(f"{anio} — '{sec}' ({len(filtrados)} alumnos)", weight=ft.FontWeight.BOLD)]),
                                controls=[ft.Column(filas_salon, spacing=4)]
                            )
                            tabla_estudiantes_view.controls.append(bloque)
                        lbl_contador_est.value = f"Total: {total} estudiantes"
                    page.update()

                modo_vista_est.on_select = refrescar_directorio
                dropdown_filtro_seccion.on_select = refrescar_directorio
                txt_buscar_est.on_change = refrescar_directorio

                async def guardar_plantilla_dialogo(e):
                    ruta = await file_picker.save_file(
                        file_name="plantilla.xlsx",
                        file_type=ft.FilePickerFileType.CUSTOM,
                        allowed_extensions=["xlsx", "csv"]
                    )
                    if ruta:
                        em.generar_plantilla(ruta)
                        lbl_estado_excel.value = "¡Plantilla generada con éxito!"
                        lbl_estado_excel.color = ft.Colors.GREEN
                        page.update()

                async def procesar_importacion(e):
                    archivos = await file_picker.pick_files(
                        file_type=ft.FilePickerFileType.CUSTOM,
                        allowed_extensions=["xlsx", "csv"]
                    )
                    if archivos and archivos[0].path:
                        exito, msg = em.importar_estudiantes(archivos[0].path)
                        lbl_estado_excel.value = msg
                        lbl_estado_excel.color = ft.Colors.GREEN if exito else ft.Colors.RED
                        cargar_opciones_sec()
                        refrescar_directorio()

                btn_plantilla = ft.Button("Descargar Plantilla (Excel/CSV)", icon=ft.Icons.DOWNLOAD, on_click=guardar_plantilla_dialogo, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE)
                btn_import = ft.Button("Importar Archivo", icon=ft.Icons.UPLOAD, on_click=procesar_importacion, bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE)

                contenido_principal.content.controls = [
                    ft.Text("Directorio de Estudiantes", size=22, weight=ft.FontWeight.BOLD),
                    ft.Text("Gestiona, edita o importa la matrícula estudiantil de la institución en Excel o CSV.", color=ft.Colors.GREY_700),
                    ft.Divider(height=10),
                    ft.Row([btn_plantilla, btn_import, lbl_estado_excel], spacing=10, wrap=True),
                    ft.Divider(height=10),
                    panel_form_estudiante,
                    ft.Divider(height=10),
                    ft.Row([modo_vista_est, dropdown_filtro_seccion, txt_buscar_est, lbl_contador_est], spacing=10, wrap=True),
                    ft.Divider(height=5),
                    tabla_estudiantes_view
                ]
                cargar_opciones_sec()
                refrescar_directorio()

            elif titulo == "Reportes":
                lbl_estado_reporte = ft.Text("", size=13)
                secciones = db.obtener_secciones()
                opciones_sec_rep = [ft.dropdown.Option("TODAS", "Todas las Secciones")]
                for id_s, anio, sec, _ in secciones:
                    opciones_sec_rep.append(ft.dropdown.Option(str(id_s), f"{anio} - '{sec}'"))

                dropdown_sec_reporte = ft.Dropdown(label="Sección", options=opciones_sec_rep, value="TODAS", width=250)

                async def guardar_rep_asist(e):
                    ruta = await file_picker.save_file(
                        file_name="asistencias.xlsx",
                        file_type=ft.FilePickerFileType.CUSTOM,
                        allowed_extensions=["xlsx", "csv"]
                    )
                    if ruta:
                        exito, msg = em.exportar_reporte_asistencias(ruta, dropdown_sec_reporte.value)
                        lbl_estado_reporte.value = msg
                        lbl_estado_reporte.color = ft.Colors.GREEN if exito else ft.Colors.RED
                        page.update()

                async def guardar_rep_doc(e):
                    ruta = await file_picker.save_file(
                        file_name="docentes.xlsx",
                        file_type=ft.FilePickerFileType.CUSTOM,
                        allowed_extensions=["xlsx", "csv"]
                    )
                    if ruta:
                        exito, msg = em.exportar_reporte_docentes(ruta)
                        lbl_estado_reporte.value = msg
                        lbl_estado_reporte.color = ft.Colors.GREEN if exito else ft.Colors.RED
                        page.update()

                contenido_principal.content.controls = [
                    ft.Text("Reportes y Exportación", size=22, weight=ft.FontWeight.BOLD),
                    ft.Text("Exporta reportes ejecutivos en formato Excel (.xlsx) o CSV (.csv).", color=ft.Colors.GREY_700),
                    ft.Divider(height=15),
                    ft.Row([
                        ft.Container(
                            content=ft.Column([
                                ft.Text("Reporte de Asistencia Estudiantil", weight=ft.FontWeight.BOLD),
                                dropdown_sec_reporte,
                                ft.Button("Exportar Excel/CSV", icon=ft.Icons.DOWNLOAD, on_click=guardar_rep_asist, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE)
                            ], spacing=10), bgcolor=ft.Colors.BLUE_50, padding=15, border_radius=8
                        ),
                        ft.Container(
                            content=ft.Column([
                                ft.Text("Consolidado Horas Docentes", weight=ft.FontWeight.BOLD),
                                ft.Container(height=35),
                                ft.Button("Exportar Excel/CSV", icon=ft.Icons.DOWNLOAD, on_click=guardar_rep_doc, bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE)
                            ], spacing=10), bgcolor=ft.Colors.GREEN_50, padding=15, border_radius=8
                        )
                    ], spacing=20, wrap=True),
                    lbl_estado_reporte
                ]

            elif titulo == "Gestion Docentes":
                txt_cedula = ft.TextField(label="Cédula", width=200)
                txt_nombre = ft.TextField(label="Nombre y Apellido", width=250)
                txt_materia = ft.TextField(label="Materia / Área", width=200)
                lbl_mensaje = ft.Text("", size=13)
                lista_docentes_view = ft.Column(spacing=10)

                def cargar_docentes():
                    lista_docentes_view.controls.clear()
                    for ced, nom, mat, _ in db.obtener_docentes():
                        btn_del = ft.IconButton(
                            icon=ft.Icons.DELETE, icon_color=ft.Colors.RED_400,
                            visible=(sesion_actual["rol"] == "admin"),
                            on_click=lambda e, c=ced: (db.eliminar_docente(c, sesion_actual["usuario"]), cargar_docentes())
                        )
                        lista_docentes_view.controls.append(ft.Container(
                            content=ft.Row([ft.Text(f"[{ced}] {nom} — {mat}", weight=ft.FontWeight.W_500), btn_del], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            bgcolor=ft.Colors.GREY_100, padding=10, border_radius=8
                        ))
                    page.update()

                def guardar_doc(e):
                    if not txt_cedula.value or not txt_nombre.value:
                        return
                    db.registrar_docente(txt_cedula.value, txt_nombre.value, txt_materia.value, 0, usuario_act=sesion_actual["usuario"])
                    txt_cedula.value = ""
                    txt_nombre.value = ""
                    txt_materia.value = ""
                    cargar_docentes()

                btn_guardar = ft.Button("Guardar Docente", icon=ft.Icons.PERSON_ADD, on_click=guardar_doc, bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE)
                contenido_principal.content.controls = [
                    ft.Text("Directorio de Docentes", size=22, weight=ft.FontWeight.BOLD),
                    ft.Row([txt_cedula, txt_nombre], spacing=10, wrap=True),
                    ft.Row([txt_materia, btn_guardar], spacing=10, vertical_alignment=ft.CrossAxisAlignment.END),
                    lbl_mensaje, ft.Divider(height=20), lista_docentes_view
                ]
                cargar_docentes()

            elif titulo == "Control Horas":
                docentes_reg = db.obtener_docentes()
                dropdown_doc = ft.Dropdown(label="Docente", options=[ft.dropdown.Option(d[0], f"[{d[0]}] {d[1]}") for d in docentes_reg], width=350)
                txt_fecha_h = ft.TextField(label="Fecha", value=date.today().strftime("%Y-%m-%d"), width=180)
                txt_hrs_dia = ft.TextField(label="Horas", width=120, keyboard_type=ft.KeyboardType.NUMBER)
                lbl_msg_h = ft.Text("", size=13)
                tabla_h = ft.Column(spacing=8)

                def cargar_h():
                    tabla_h.controls.clear()
                    for id_h, nom_doc, ced_doc, fecha, hrs in db.obtener_historial_horas():
                        tabla_h.controls.append(ft.Container(
                            content=ft.Row([ft.Text(f"📅 {fecha} | 👨‍🏫 {nom_doc} ({ced_doc}) | ⏱️ {hrs} hrs")], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            bgcolor=ft.Colors.BLUE_GREY_50, padding=8, border_radius=6
                        ))
                    page.update()

                def guardar_h(e):
                    if not dropdown_doc.value or not txt_hrs_dia.value:
                        return
                    db.registrar_horas_diarias(dropdown_doc.value, txt_fecha_h.value, int(txt_hrs_dia.value), usuario_act=sesion_actual["usuario"])
                    txt_hrs_dia.value = ""
                    lbl_msg_h.value = "¡Jornada de horas registrada con éxito!"
                    lbl_msg_h.color = ft.Colors.GREEN_700
                    cargar_h()

                btn_reg_h = ft.Button("Registrar Jornada", icon=ft.Icons.ADD_ALARM, on_click=guardar_h, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE)
                contenido_principal.content.controls = [
                    ft.Text("Registro de Horas Docentes", size=22, weight=ft.FontWeight.BOLD),
                    ft.Text("Las jornadas registradas quedan archivadas permanentemente para los reportes.", color=ft.Colors.GREY_700),
                    ft.Divider(height=10),
                    dropdown_doc,
                    ft.Row([txt_fecha_h, txt_hrs_dia, btn_reg_h], spacing=10, vertical_alignment=ft.CrossAxisAlignment.END),
                    lbl_msg_h,
                    ft.Divider(height=20),
                    ft.Text("Historial de Jornadas:", weight=ft.FontWeight.BOLD),
                    tabla_h
                ]
                cargar_h()

            elif titulo == "Panel Administrador":
                if sesion_actual["rol"] != "admin":
                    contenido_principal.content.controls = [ft.Text("Acceso Denegado", color=ft.Colors.RED, size=20)]
                    page.update()
                    return

                txt_u = ft.TextField(label="Usuario", width=160)
                txt_p = ft.TextField(label="Contraseña", password=True, width=160)
                txt_p_conf = ft.TextField(label="Confirmar Contraseña", password=True, width=160)
                txt_n = ft.TextField(label="Nombre Completo", width=200)
                drop_r = ft.Dropdown(label="Rol", options=[ft.dropdown.Option("coordinacion"), ft.dropdown.Option("admin")], value="coordinacion", width=140)
                lbl_msg_usu = ft.Text("", size=13)
                lista_usu_view = ft.Column(spacing=6)
                tabla_auditoria = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, height=220)

                def cargar_usuarios_y_auditoria():
                    lista_usu_view.controls.clear()
                    for uid, usu, nom, rol in db.obtener_usuarios_sistema():
                        btn_d = ft.IconButton(icon=ft.Icons.DELETE, icon_color=ft.Colors.RED, on_click=lambda e, i=uid: (db.eliminar_usuario_sistema(i), cargar_usuarios_y_auditoria()))
                        lista_usu_view.controls.append(ft.Container(
                            content=ft.Row([ft.Text(f"👤 {nom} ({usu}) — Rol: {rol.upper()}"), btn_d], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            bgcolor=ft.Colors.GREY_100, padding=6, border_radius=6
                        ))

                    tabla_auditoria.controls.clear()
                    for usu, fh, acc, det in db.obtener_historial_auditoria():
                        tabla_auditoria.controls.append(ft.Text(f"[{fh}] {usu} -> {acc}: {det}", size=11, font_family="Consolas"))
                    page.update()

                def crear_usuario(e):
                    if not txt_u.value or not txt_p.value or not txt_p_conf.value or not txt_n.value:
                        lbl_msg_usu.value = "Complete todos los campos."
                        lbl_msg_usu.color = ft.Colors.RED
                        page.update()
                        return
                    if txt_p.value != txt_p_conf.value:
                        lbl_msg_usu.value = "Las contraseñas no coinciden."
                        lbl_msg_usu.color = ft.Colors.RED
                        page.update()
                        return

                    exito, msg = db.registrar_usuario_sistema(txt_u.value.strip(), txt_p.value.strip(), txt_n.value.strip(), drop_r.value)
                    lbl_msg_usu.value = msg
                    lbl_msg_usu.color = ft.Colors.GREEN if exito else ft.Colors.RED
                    txt_u.value = ""
                    txt_p.value = ""
                    txt_p_conf.value = ""
                    txt_n.value = ""
                    cargar_usuarios_y_auditoria()

                btn_crear_u = ft.Button("Crear Usuario", icon=ft.Icons.PERSON_ADD, on_click=crear_usuario, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE)

                contenido_principal.content.controls = [
                    ft.Text("Panel de Administración y Auditoría", size=22, weight=ft.FontWeight.BOLD),
                    ft.Text("Gestión de credenciales con doble confirmación y auditoría del sistema.", color=ft.Colors.GREY_700),
                    ft.Divider(height=10),
                    ft.Text("Registrar Nuevo Usuario:", weight=ft.FontWeight.BOLD),
                    ft.Row([txt_u, txt_p, txt_p_conf, txt_n, drop_r, btn_crear_u], spacing=10, vertical_alignment=ft.CrossAxisAlignment.END, wrap=True),
                    lbl_msg_usu,
                    ft.Divider(height=15),
                    ft.Text("Usuarios Activos:", weight=ft.FontWeight.BOLD),
                    lista_usu_view,
                    ft.Divider(height=15),
                    ft.Text("📜 Historial de Auditoría de Cambios:", weight=ft.FontWeight.BOLD),
                    tabla_auditoria
                ]
                cargar_usuarios_y_auditoria()

            page.update()

        elementos_menu = [
            ft.Row([
                ft.Icon(ft.Icons.SCHOOL, color=ft.Colors.WHITE, size=24),
                ft.Text("GESTIÓN ESCOLAR", color=ft.Colors.WHITE, size=14, weight=ft.FontWeight.BOLD),
            ], spacing=8),
            ft.Divider(color=ft.Colors.WHITE_24),
            ft.TextButton("Resumen", icon=ft.Icons.DASHBOARD, icon_color=ft.Colors.WHITE, on_click=lambda e: cambiar_vista(e, "Resumen"), style=ft.ButtonStyle(color=ft.Colors.WHITE)),
            ft.TextButton("Asistencia", icon=ft.Icons.CHECK_BOX, icon_color=ft.Colors.WHITE, on_click=lambda e: cambiar_vista(e, "Asistencia"), style=ft.ButtonStyle(color=ft.Colors.WHITE)),
            ft.TextButton("Estudiantes / Excel", icon=ft.Icons.PEOPLE, icon_color=ft.Colors.WHITE, on_click=lambda e: cambiar_vista(e, "Estudiantes"), style=ft.ButtonStyle(color=ft.Colors.WHITE)),
            ft.TextButton("Repositorio y Estadísticas", icon=ft.Icons.FOLDER_SPECIAL, icon_color=ft.Colors.WHITE, on_click=lambda e: cambiar_vista(e, "Repositorio y Estadísticas"), style=ft.ButtonStyle(color=ft.Colors.WHITE)),
            ft.TextButton("Reportes y CSV", icon=ft.Icons.BAR_CHART, icon_color=ft.Colors.WHITE, on_click=lambda e: cambiar_vista(e, "Reportes"), style=ft.ButtonStyle(color=ft.Colors.WHITE)),
            ft.TextButton("Gestionar Docentes", icon=ft.Icons.PEOPLE_ALT, icon_color=ft.Colors.WHITE, on_click=lambda e: cambiar_vista(e, "Gestion Docentes"), style=ft.ButtonStyle(color=ft.Colors.WHITE)),
            ft.TextButton("Control de Horas", icon=ft.Icons.TIMER, icon_color=ft.Colors.WHITE, on_click=lambda e: cambiar_vista(e, "Control Horas"), style=ft.ButtonStyle(color=ft.Colors.WHITE)),
        ]

        if sesion_actual["rol"] == "admin":
            elementos_menu.append(ft.TextButton("Panel Administrador", icon=ft.Icons.ADMIN_PANEL_SETTINGS, icon_color=ft.Colors.YELLOW, on_click=lambda e: cambiar_vista(e, "Panel Administrador"), style=ft.ButtonStyle(color=ft.Colors.YELLOW)))

        sidebar = ft.Container(content=ft.Column(elementos_menu, spacing=8), bgcolor="#1E293B", padding=15, width=220)

        header = ft.Container(
            content=ft.Row([
                ft.Text(f"Conectado: {sesion_actual['nombre']} ({sesion_actual['rol'].upper()})", size=15, weight=ft.FontWeight.W_500),
                ft.Button("Cerrar Sesión", icon=ft.Icons.LOGOUT, on_click=lambda e: mostrar_login(), color=ft.Colors.RED)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            bgcolor=ft.Colors.WHITE, padding=15, border=ft.Border.only(bottom=ft.BorderSide(1, ft.Colors.GREY_300))
        )

        layout_dashboard = ft.GestureDetector(
            content=ft.Row([sidebar, ft.Column([header, contenido_principal], expand=True, spacing=0)], expand=True, spacing=0),
            on_hover=reiniciar_inactividad,
            on_tap_down=reiniciar_inactividad,
            hover_interval=1000,
            expand=True
        )

        page.add(layout_dashboard)
        cambiar_vista(None, "Resumen")

    def mostrar_login():
        page.clean()
        sesion_actual["usuario"] = None

        txt_usuario = ft.TextField(label="Usuario", width=300, prefix_icon=ft.Icons.PERSON)
        txt_password = ft.TextField(label="Contraseña", password=True, can_reveal_password=True, width=300, prefix_icon=ft.Icons.LOCK)
        lbl_error = ft.Text("", color=ft.Colors.RED, size=13)

        def intentar_login(e):
            usr = txt_usuario.value.strip()
            pwd = txt_password.value.strip()

            res = db.validar_login(usr, pwd)
            if res:
                sesion_actual["usuario"] = res[0]
                sesion_actual["nombre"] = res[1]
                sesion_actual["rol"] = res[2]
                reiniciar_inactividad()
                db.registrar_auditoria(res[0], "INICIO DE SESIÓN", f"Acceso correcto como {res[2]}")
                mostrar_dashboard(res[2])
            else:
                lbl_error.value = "Usuario o contraseña incorrectos."
                page.update()

        tarjeta_login = ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.LOCK_PERSON, size=60, color="#1E293B"),
                ft.Text("Control de Asistencia Escolar", size=22, weight=ft.FontWeight.BOLD),
                ft.Text("Ingrese sus credenciales institucionales", color=ft.Colors.GREY_700, size=13),
                ft.Divider(height=15),
                txt_usuario,
                txt_password,
                lbl_error,
                ft.Button("Iniciar Sesión", icon=ft.Icons.LOGIN, on_click=intentar_login, bgcolor=ft.Colors.BLUE_800, color=ft.Colors.WHITE, width=300)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
            bgcolor=ft.Colors.WHITE, padding=40, border_radius=15,
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=15, color=ft.Colors.BLACK_12)
        )

        contenedor_centrado = ft.Container(content=tarjeta_login, alignment=ft.Alignment.CENTER, bgcolor="#F1F5F9", expand=True)
        page.add(contenedor_centrado)
        page.update()

    mostrar_login()


if __name__ == "__main__":
    ft.run(main)
