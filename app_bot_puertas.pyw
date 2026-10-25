# -*- coding: utf-8 -*-
# Bot Puertas Galacticas - WordGalaxy  |  Aplicacion (doble clic, sin consola)
import sys, os, re, time, json, threading, subprocess, importlib, importlib.util, shutil, webbrowser, queue
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

AQUI = os.path.dirname(os.path.abspath(__file__))
os.chdir(AQUI)
if AQUI not in sys.path:
    sys.path.insert(0, AQUI)

# ------------------------------------------------------------------ paleta
BG, PANEL, PANEL2, BORDE = "#0a0f1c", "#111827", "#162033", "#25324d"
TXT, MUTED = "#e6edf7", "#8190ab"
ACC, CIAN, VERDE, ROJO, AMAR = "#f5a524", "#38bdf8", "#34d399", "#f87171", "#fbbf24"
FUENTE = "Segoe UI"
SIN_VENTANA = getattr(subprocess, "CREATE_NO_WINDOW", 0)

PAQUETES = {"numpy": "numpy", "cv2": "opencv-python", "mss": "mss", "pyautogui": "pyautogui",
            "keyboard": "keyboard", "pytesseract": "pytesseract", "websocket": "websocket-client"}


def aclarar(hexcolor, f=1.15):
    h = hexcolor.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02x%02x%02x" % tuple(min(255, int(c * f)) for c in (r, g, b))


# ------------------------------------------------------------------ dependencias
def asegurar_dependencias(root):
    falta = [pip for mod, pip in PAQUETES.items() if importlib.util.find_spec(mod) is None]
    if not falta:
        return True
    if not messagebox.askyesno(
            "Falta instalar componentes",
            "Para funcionar el bot necesita instalar:\n\n  " + "\n  ".join(falta) +
            "\n\nSe instalan automaticamente (hace falta internet).\n\n¿Instalar ahora?"):
        return False
    win = tk.Toplevel(root)
    win.title("Instalando...")
    win.configure(bg=BG)
    win.geometry("380x120")
    win.resizable(False, False)
    tk.Label(win, text="Instalando componentes, espera un momento...", bg=BG, fg=TXT,
             font=(FUENTE, 10)).pack(pady=(22, 10))
    barra = ttk.Progressbar(win, mode="indeterminate", length=300)
    barra.pack()
    barra.start(12)
    res = {}

    def tarea():
        exe = sys.executable
        if exe.lower().endswith("pythonw.exe") and os.path.exists(exe[:-5] + ".exe"):
            exe = exe[:-5] + ".exe"
        try:
            r = subprocess.run([exe, "-m", "pip", "install", *falta], capture_output=True, text=True,
                               creationflags=SIN_VENTANA)
            res["ok"], res["txt"] = r.returncode == 0, (r.stdout + r.stderr)[-1500:]
        except Exception as e:
            res["ok"], res["txt"] = False, str(e)

    th = threading.Thread(target=tarea, daemon=True)
    th.start()
    while th.is_alive():
        win.update()
        time.sleep(0.05)
    win.destroy()
    importlib.invalidate_caches()
    if not res.get("ok"):
        messagebox.showerror("No se pudo instalar", res.get("txt", ""))
        return False
    return True


# ------------------------------------------------------------------ widgets
class Boton(tk.Label):
    def __init__(self, master, texto, comando, bg, fg="#0a0f1c", font=None, padx=18, pady=10):
        super().__init__(master, text=texto, bg=bg, fg=fg, font=font or (FUENTE, 11, "bold"),
                         padx=padx, pady=pady, cursor="hand2")
        self.cmd, self.base, self.fg0, self.activo = comando, bg, fg, True
        self.bind("<Enter>", lambda e: self.activo and self.config(bg=aclarar(self.base)))
        self.bind("<Leave>", lambda e: self.activo and self.config(bg=self.base))
        self.bind("<Button-1>", lambda e: self.activo and self.cmd())

    def set(self, activo=None, texto=None, bg=None):
        if texto is not None:
            self.config(text=texto)
        if bg is not None:
            self.base = bg
        if activo is not None:
            self.activo = activo
        if self.activo:
            self.config(bg=self.base, fg=self.fg0, cursor="hand2")
        else:
            self.config(bg="#1a2336", fg="#566682", cursor="arrow")


class CartaPuerta(tk.Frame):
    def __init__(self, master, nombre, sub, cb):
        super().__init__(master, bg=PANEL2, highlightthickness=2, highlightbackground=BORDE, cursor="hand2")
        self.nombre, self.cb = nombre, cb
        self.l1 = tk.Label(self, text=nombre, bg=PANEL2, fg=TXT, font=(FUENTE, 11, "bold"), cursor="hand2")
        self.l2 = tk.Label(self, text=sub, bg=PANEL2, fg=MUTED, font=(FUENTE, 8), cursor="hand2")
        self.l1.pack(padx=8, pady=(9, 0))
        self.l2.pack(padx=8, pady=(0, 9))
        for w in (self, self.l1, self.l2):
            w.bind("<Button-1>", lambda e: self.cb(self.nombre))

    def seleccionar(self, v):
        bg = "#21304f" if v else PANEL2
        self.config(bg=bg, highlightbackground=ACC if v else BORDE)
        self.l1.config(bg=bg, fg=ACC if v else TXT)
        self.l2.config(bg=bg)


class Dato(tk.Frame):
    def __init__(self, master, titulo, valor="—", color=TXT, grande=False):
        super().__init__(master, bg=PANEL2)
        tk.Label(self, text=titulo, bg=PANEL2, fg=MUTED, font=(FUENTE, 8, "bold")).pack(anchor="w", padx=10, pady=(8, 0))
        self.v = tk.Label(self, text=valor, bg=PANEL2, fg=color, font=(FUENTE, 17 if grande else 11, "bold"))
        self.v.pack(anchor="w", padx=10, pady=(0, 8))

    def set(self, valor, color=None):
        self.v.config(text=valor)
        if color:
            self.v.config(fg=color)


def seccion(master, texto):
    return tk.Label(master, text=texto, bg=PANEL, fg=MUTED, font=(FUENTE, 8, "bold"))



# ------------------------------------------------------------------ ajustes
# (clave, etiqueta, tipo, minimo, maximo, valor recomendado, ayuda)
AJUSTES = [
    ("Armado de la puerta", [
        ("intervalo_tirada", "Pausa entre tiradas (s)", float, 0.0, 10, 0.3, "Espera después de cada clic en PROCESAR TIRADA."),
        ("espera_carga_nave", "Máximo esperando a que cargue la nave (s)", int, 10, 900, 240, "Al iniciar, tiempo máximo para que aparezca la nave."),
    ]),
    ("Ir al portal y saltar (J)", [
        ("quieto_seg", "Nave detenida para dar por llegada (s)", float, 0.1, 10, 0.6, "Cuánto tiempo debe quedar quieta la nave antes de pulsar J."),
        ("timeout_llegada", "Máximo viajando al portal (s)", int, 10, 300, 90, "Si no llega en este tiempo, vuelve a intentar."),
        ("espera_salto", "Espera después de pulsar J (s)", int, 1, 60, 10, "Tiempo para que cambie el mapa tras el salto."),
        ("umbral_quieta_mini", "Sensibilidad de movimiento (px)", int, 1, 200, 25, "Más alto = tolera más cambios en el minimapa antes de decir que la nave se mueve."),
        ("max_intentos_salto", "Intentos máximos de salto", int, 1, 200, 60, "Veces que reintenta ir al portal y saltar."),
    ]),
    ("Combate (kamikaze)", [
        ("espera_inicio_ronda", "Esperar NPC al empezar la ronda (s)", float, 0, 60, 5, "Si no aparece ningún NPC en este tiempo, da la ronda por terminada."),
        ("estable_seg", "NPC juntos antes de lanzar (s)", float, 0, 10, 0.7, "Tiempo que deben seguir juntos para lanzar el kamikaze."),
        ("spread_max_mini", "Dispersión máxima de NPC (px del minimapa)", int, 2, 60, 12, "Qué tan pegados deben estar para considerarlos juntos."),
        ("espera_juntos_max", "Máximo esperando que se junten (s)", int, 3, 300, 40, "Pasado este tiempo lanza con los que haya cerca."),
        ("radio_juntos", "Radio de NPC cercanos (px de pantalla)", int, 100, 900, 300, "Distancia a la nave para contar un NPC como cercano."),
        ("cooldown_kamikaze", "Mínimo huyendo tras lanzar (s)", float, 0, 60, 22, "El enfriamiento real del kamikaze es de 25 s."),
    ]),
    ("Huida", [
        ("radio_llegada", "Distancia para dar un punto por llegado (px)", int, 2, 60, 10, "En el minimapa: qué tan cerca debe quedar la nave del punto."),
        ("quieto_llegada", "Nave quieta antes del punto = llegó (s)", float, 0.1, 10, 0.5, "Si se detiene antes de llegar (borde, obstáculo), pasa al siguiente punto."),
        ("quieto_huida", "Nave quieta (sin cruz del minimapa) (s)", float, 0.1, 10, 0.3, "Solo si no se ve la cruz de la nave en el minimapa."),
        ("timeout_tramo", "Máximo por punto antes de pasar al siguiente (s)", int, 5, 300, 45, "Evita quedarse atorado en un punto."),
        ("huida_margen", "Margen con el borde del minimapa (px)", int, 0, 60, 14, "Separación de los puntos con el borde del minimapa."),
    ]),
    ("PET", [
        ("comb_min", "Comprar combustible desde (%)", int, 0, 100, 4, "Compra cuando el combustible esté entre estos dos valores."),
        ("comb_max", "Comprar combustible hasta (%)", int, 0, 100, 10, ""),
    ]),
]
PUNTOS_DEF = [[0, 0], [0, 1], [1, 1], [1, 0]]


class VentanaAjustes(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app.root)
        self.app, self.bot = app, app.bot
        self.title("Ajustes del bot")
        self.configure(bg=BG)
        self.geometry("1020x740")
        self.minsize(940, 620)
        self.transient(app.root)
        self.vars, self.filas, self.campos = {}, [], []

        tk.Label(self, text="Ajustes", bg=BG, fg=TXT, font=(FUENTE, 16, "bold")).pack(anchor="w", padx=22, pady=(16, 0))
        tk.Label(self, text="Los cambios se aplican al pulsar Guardar (la mayoría en el momento, incluso con el bot trabajando).",
                 bg=BG, fg=MUTED, font=(FUENTE, 9)).pack(anchor="w", padx=22, pady=(0, 8))

        cuerpo = tk.Frame(self, bg=BG)
        cuerpo.pack(fill="both", expand=True, padx=22)
        cuerpo.columnconfigure(0, weight=1)
        cuerpo.columnconfigure(1, weight=0)
        cuerpo.rowconfigure(0, weight=1)

        # ---- lista de tiempos (con scroll)
        izq = tk.Frame(cuerpo, bg=BG)
        izq.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        cv = tk.Canvas(izq, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(izq, command=cv.yview)
        cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        cv.pack(side="left", fill="both", expand=True)
        interior = tk.Frame(cv, bg=BG)
        win = cv.create_window((0, 0), window=interior, anchor="nw")
        interior.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.bind("<Configure>", lambda e: cv.itemconfig(win, width=e.width))
        self.bind("<MouseWheel>", lambda e: cv.yview_scroll(int(-e.delta / 120), "units"))

        for titulo, campos in AJUSTES:
            caja = tk.Frame(interior, bg=PANEL)
            caja.pack(fill="x", pady=(0, 10))
            tk.Label(caja, text=titulo.upper(), bg=PANEL, fg=ACC, font=(FUENTE, 9, "bold")).pack(anchor="w", padx=14, pady=(10, 4))
            for c in campos:
                clave, etiqueta, tipo, mn, mx, dflt, ayuda = c
                self.campos.append(c)
                fila = tk.Frame(caja, bg=PANEL)
                fila.pack(fill="x", padx=14, pady=(2, 6))
                fila.columnconfigure(0, weight=1)
                tk.Label(fila, text=etiqueta, bg=PANEL, fg=TXT, font=(FUENTE, 10), anchor="w").grid(row=0, column=0, sticky="w")
                v = tk.StringVar(value=self.fmt(self.bot.CFG.get(clave, dflt)))
                self.vars[clave] = v
                tk.Entry(fila, textvariable=v, width=9, justify="center", bg=PANEL2, fg=TXT, insertbackground=TXT,
                         relief="flat", font=(FUENTE, 10, "bold"), highlightthickness=1, highlightbackground=BORDE,
                         highlightcolor=ACC).grid(row=0, column=1, sticky="e", ipady=3)
                if ayuda:
                    tk.Label(fila, text=ayuda, bg=PANEL, fg=MUTED, font=(FUENTE, 8), anchor="w", justify="left",
                             wraplength=430).grid(row=1, column=0, columnspan=2, sticky="w")

        # ---- puntos de huida
        der = tk.Frame(cuerpo, bg=PANEL, width=380)
        der.grid(row=0, column=1, sticky="ns")
        der.grid_propagate(False)
        tk.Label(der, text="PUNTOS DE HUIDA", bg=PANEL, fg=ACC, font=(FUENTE, 9, "bold")).pack(anchor="w", padx=14, pady=(12, 2))
        tk.Label(der, text="El bot huye de punto en punto, en este orden, mientras el kamikaze se enfría. "
                           "X e Y van de 0 a 100 (0 = izquierda / arriba, 100 = derecha / abajo del minimapa).",
                 bg=PANEL, fg=MUTED, font=(FUENTE, 8), justify="left", wraplength=350).pack(anchor="w", padx=14)
        self.prev = tk.Canvas(der, width=300, height=190, bg="#0d1424", highlightthickness=1, highlightbackground=BORDE)
        self.prev.pack(pady=10)
        self.caja_filas = tk.Frame(der, bg=PANEL)
        self.caja_filas.pack(fill="x", padx=14)
        Boton(der, "＋  Agregar punto", self.agregar_punto, PANEL2, fg=TXT, font=(FUENTE, 9, "bold"), pady=6).pack(padx=14, pady=8, fill="x")

        pts = self.bot.CFG.get("puntos_huida") or PUNTOS_DEF
        for fx, fy in pts:
            self.nueva_fila(int(round(fx * 100)), int(round(fy * 100)))
        self.vars["huida_margen"].trace_add("write", lambda *a: self.dibujar())
        self.dibujar()

        # ---- botones
        pie = tk.Frame(self, bg=BG)
        pie.pack(fill="x", padx=22, pady=14)
        self.estado = tk.Label(pie, text="", bg=BG, fg=VERDE, font=(FUENTE, 10, "bold"))
        self.estado.pack(side="left")
        Boton(pie, "Guardar", self.guardar, VERDE, pady=9).pack(side="right")
        Boton(pie, "Restaurar recomendados", self.restaurar, PANEL2, fg=TXT, font=(FUENTE, 10, "bold"), pady=9).pack(side="right", padx=10)

    @staticmethod
    def fmt(v):
        return str(int(v)) if float(v) == int(v) else str(v)

    # ---- puntos
    def nueva_fila(self, x=50, y=50):
        vx, vy = tk.StringVar(value=str(x)), tk.StringVar(value=str(y))
        fila = tk.Frame(self.caja_filas, bg=PANEL)
        fila.pack(fill="x", pady=2)
        n = tk.Label(fila, text="", bg=PANEL, fg=ACC, font=(FUENTE, 10, "bold"), width=3)
        n.pack(side="left")
        for txt, var in (("X", vx), ("Y", vy)):
            tk.Label(fila, text=txt, bg=PANEL, fg=MUTED, font=(FUENTE, 9, "bold")).pack(side="left", padx=(4, 2))
            sp = tk.Spinbox(fila, from_=0, to=100, increment=5, width=5, textvariable=var, justify="center", bg=PANEL2, fg=TXT,
                            insertbackground=TXT, relief="flat", buttonbackground=BORDE, highlightthickness=0,
                            command=self.dibujar, font=(FUENTE, 10))
            sp.pack(side="left")
        d = {"frame": fila, "n": n, "x": vx, "y": vy}
        Boton(fila, "✕", lambda d=d: self.quitar(d), PANEL2, fg=ROJO, font=(FUENTE, 9, "bold"), padx=8, pady=2).pack(side="right")
        vx.trace_add("write", lambda *a: self.dibujar())
        vy.trace_add("write", lambda *a: self.dibujar())
        self.filas.append(d)
        self.dibujar()

    def agregar_punto(self):
        if len(self.filas) < 12:
            self.nueva_fila()

    def quitar(self, d):
        if len(self.filas) <= 1:
            return
        d["frame"].destroy()
        self.filas.remove(d)
        self.dibujar()

    def puntos(self):
        out = []
        for d in self.filas:
            try:
                fx = max(0, min(100, float(d["x"].get()))) / 100
                fy = max(0, min(100, float(d["y"].get()))) / 100
            except ValueError:
                fx = fy = 0.5
            out.append([fx, fy])
        return out

    def dibujar(self):
        c = self.prev
        c.delete("all")
        W, H, sc = 300, 190, 300 / 228
        c.create_rectangle(2, 2, W - 2, H - 2, outline=BORDE)
        try:
            m = max(0, min(60, float(self.vars["huida_margen"].get()))) * sc
        except Exception:
            m = 14 * sc
        c.create_rectangle(m, m, W - m, H - m, outline="#1e2b44", dash=(3, 3))
        pts = [(m + fx * (W - 2 * m), m + fy * (H - 2 * m)) for fx, fy in self.puntos()]
        for i, p in enumerate(pts):
            q = pts[(i + 1) % len(pts)]
            if len(pts) > 1:
                c.create_line(*p, *q, fill="#3a4d73", arrow="last", dash=(4, 3) if i == len(pts) - 1 else ())
        for i, (x, y) in enumerate(pts):
            c.create_oval(x - 10, y - 10, x + 10, y + 10, fill=ACC, outline="")
            c.create_text(x, y, text=str(i + 1), fill="#0a0f1c", font=(FUENTE, 9, "bold"))
        for i, d in enumerate(self.filas):
            d["n"].config(text=f"{i + 1}")

    # ---- guardar / restaurar
    def guardar(self):
        nuevos = {}
        for clave, etiqueta, tipo, mn, mx, dflt, ayuda in self.campos:
            txt = self.vars[clave].get().strip().replace(",", ".")
            try:
                v = tipo(float(txt))
            except ValueError:
                messagebox.showerror("Valor no válido", f"«{etiqueta}» debe ser un número.", parent=self)
                return
            nuevos[clave] = max(mn, min(mx, v))
        nuevos["puntos_huida"] = self.puntos()
        self.bot.CFG.update(nuevos)
        try:
            try:
                datos = json.load(open(self.bot.CFG_FILE, encoding="utf-8"))
            except Exception:
                datos = dict(self.bot.CFG)
            datos.update(nuevos)
            json.dump(datos, open(self.bot.CFG_FILE, "w", encoding="utf-8"), indent=2)
        except Exception as e:
            messagebox.showerror("No se pudo guardar", str(e), parent=self)
            return
        for clave, *_ in self.campos:                   # mostrar el valor ya ajustado a su rango
            self.vars[clave].set(self.fmt(nuevos[clave]))
        self.app.log("Ajustes guardados", "ok")
        self.estado.config(text="✓ Guardado")
        self.after(2500, lambda: self.estado.config(text=""))

    def restaurar(self):
        if not messagebox.askyesno("Restaurar", "¿Volver a los valores recomendados?", parent=self):
            return
        for clave, etiqueta, tipo, mn, mx, dflt, ayuda in self.campos:
            self.vars[clave].set(self.fmt(dflt))
        for d in list(self.filas):
            d["frame"].destroy()
        self.filas.clear()
        for fx, fy in PUNTOS_DEF:
            self.nueva_fila(int(fx * 100), int(fy * 100))
        self.estado.config(text="Pulsa Guardar para aplicar")


# ------------------------------------------------------------------ aplicacion
class App:
    def __init__(self, root, bot):
        self.root, self.bot = root, bot
        self.S = bot.S
        self.th = None
        self.gate = "KRONOS"
        self.activo_seg = 0.0
        self.t_ult = time.time()
        self.ultimo_key = None
        self.cola = queue.Queue()
        self.conexion = None
        self.f6 = False
        self.abriendo = False

        root.title("Bot Puertas Galácticas · WordGalaxy")
        root.configure(bg=BG)
        root.geometry("1120x800")
        root.minsize(1060, 740)
        root.protocol("WM_DELETE_WINDOW", self.cerrar)
        self.construir()
        self.elegir_gate("KRONOS")
        self.set_modo(bool(bot.CFG.get("modo_fondo", True)), guardar=False)
        try:
            bot.keyboard.add_hotkey("f6", lambda: setattr(self, "f6", True))
        except Exception:
            pass
        threading.Thread(target=self.vigilar_conexion, daemon=True).start()
        self.refrescar()

    # ---------- interfaz
    def construir(self):
        r = self.root
        # cabecera
        cab = tk.Frame(r, bg=BG)
        cab.pack(fill="x", padx=22, pady=(16, 6))
        logo = tk.Frame(cab, bg=BG)
        logo.pack(side="left")
        tk.Label(logo, text="WORD", bg=BG, fg=TXT, font=(FUENTE, 20, "bold")).pack(side="left")
        tk.Label(logo, text="GALAXY", bg=BG, fg=ACC, font=(FUENTE, 20, "bold")).pack(side="left")
        tk.Label(logo, text="   Bot de Puertas Galácticas", bg=BG, fg=MUTED, font=(FUENTE, 11)).pack(side="left", pady=(6, 0))
        self.chip = tk.Label(cab, text="", bg=PANEL, fg=MUTED, font=(FUENTE, 9, "bold"), padx=12, pady=6)
        self.chip.pack(side="right")
        Boton(cab, "⚙  Ajustes", self.abrir_ajustes, PANEL, fg=TXT, font=(FUENTE, 9, "bold"), padx=14, pady=6).pack(side="right", padx=(0, 10))

        self.aviso = tk.Frame(r, bg="#3a2a0e")
        self.aviso_txt = tk.Label(self.aviso, text="", bg="#3a2a0e", fg=AMAR, font=(FUENTE, 9), anchor="w")
        self.aviso_txt.pack(side="left", padx=12, pady=6)
        Boton(self.aviso, "Descargar Tesseract", lambda: webbrowser.open("https://github.com/UB-Mannheim/tesseract/wiki"),
              "#5c430f", fg=AMAR, font=(FUENTE, 8, "bold"), padx=10, pady=3).pack(side="right", padx=10)
        if not self.hay_tesseract():
            self.aviso_txt.config(text="Falta Tesseract-OCR: no se podrá leer el uridium ni deducir la ronda por los nombres de los NPC.")
            self.aviso.pack(fill="x", padx=22, pady=(0, 6))

        cuerpo = tk.Frame(r, bg=BG)
        cuerpo.pack(fill="both", expand=True, padx=22, pady=(4, 8))
        cuerpo.columnconfigure(1, weight=1)
        cuerpo.rowconfigure(0, weight=1)

        # ---- izquierda
        izq = tk.Frame(cuerpo, bg=PANEL, width=400)
        izq.grid(row=0, column=0, sticky="ns", padx=(0, 14))
        izq.grid_propagate(False)
        izq.pack_propagate(False)
        seccion(izq, "1 · ELIGE LA PUERTA").pack(anchor="w", padx=18, pady=(18, 8))
        grid = tk.Frame(izq, bg=PANEL)
        grid.pack(padx=18, fill="x")
        self.cartas = {}
        nombres = self.bot.GATES
        for i, n in enumerate(nombres):
            tot = self.bot.RONDAS.get(n)
            sub = f"{tot} rondas" if tot else "sin configurar"
            c = CartaPuerta(grid, n, sub, self.elegir_gate)
            c.grid(row=i // 3, column=i % 3, padx=4, pady=4, sticky="nsew")
            grid.columnconfigure(i % 3, weight=1)
            self.cartas[n] = c

        seccion(izq, "2 · MODO DE TRABAJO").pack(anchor="w", padx=18, pady=(18, 8))
        seg = tk.Frame(izq, bg=BORDE)
        seg.pack(padx=18, fill="x")
        self.m_fondo = tk.Label(seg, text="Segundo plano", font=(FUENTE, 10, "bold"), pady=8, cursor="hand2")
        self.m_normal = tk.Label(seg, text="Normal", font=(FUENTE, 10, "bold"), pady=8, cursor="hand2")
        self.m_fondo.pack(side="left", fill="x", expand=True, padx=(2, 1), pady=2)
        self.m_normal.pack(side="left", fill="x", expand=True, padx=(1, 2), pady=2)
        self.m_fondo.bind("<Button-1>", lambda e: self.set_modo(True))
        self.m_normal.bind("<Button-1>", lambda e: self.set_modo(False))
        self.ayuda_modo = tk.Label(izq, text="", bg=PANEL, fg=MUTED, font=(FUENTE, 9), justify="left", wraplength=350, anchor="w")
        self.ayuda_modo.pack(anchor="w", padx=18, pady=(8, 8))
        self.b_juego = Boton(izq, "Abrir el juego en segundo plano", self.abrir_juego, PANEL2, fg=TXT,
                             font=(FUENTE, 10, "bold"), pady=8)
        self.b_juego.pack(padx=18, fill="x")

        seccion(izq, "3 · CONTROL").pack(anchor="w", padx=18, pady=(20, 8))
        self.b_inicio = Boton(izq, "▶  INICIAR", self.iniciar, VERDE, font=(FUENTE, 14, "bold"), pady=14)
        self.b_inicio.pack(padx=18, fill="x")
        fila = tk.Frame(izq, bg=PANEL)
        fila.pack(padx=18, pady=(8, 0), fill="x")
        self.b_pausa = Boton(fila, "‖  Pausar", self.pausar, AMAR, pady=9)
        self.b_pausa.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.b_stop = Boton(fila, "■  Detener", self.detener, ROJO, pady=9)
        self.b_stop.pack(side="left", fill="x", expand=True, padx=(4, 0))
        tk.Label(izq, text="Atajo: F6 pausa / reanuda", bg=PANEL, fg=MUTED, font=(FUENTE, 8)).pack(pady=(10, 0))

        # ---- derecha
        der = tk.Frame(cuerpo, bg=BG)
        der.grid(row=0, column=1, sticky="nsew")
        der.columnconfigure(0, weight=1)
        der.rowconfigure(3, weight=1)

        est = tk.Frame(der, bg=PANEL)
        est.grid(row=0, column=0, sticky="ew")
        top = tk.Frame(est, bg=PANEL)
        top.pack(fill="x", padx=20, pady=(16, 0))
        self.punto = tk.Label(top, text="●", bg=PANEL, fg=MUTED, font=(FUENTE, 14))
        self.punto.pack(side="left")
        self.estado = tk.Label(top, text="DETENIDO", bg=PANEL, fg=MUTED, font=(FUENTE, 13, "bold"))
        self.estado.pack(side="left", padx=(6, 0))
        self.lbl_gate = tk.Label(top, text="", bg=PANEL, fg=ACC, font=(FUENTE, 11, "bold"))
        self.lbl_gate.pack(side="right")
        self.msg = tk.Label(est, text="Elige una puerta y pulsa INICIAR.", bg=PANEL, fg=TXT, font=(FUENTE, 12),
                            justify="left", anchor="w", wraplength=560)
        self.msg.pack(fill="x", padx=20, pady=(6, 16))

        fila2 = tk.Frame(der, bg=BG)
        fila2.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        self.d_ronda = Dato(fila2, "RONDA", grande=True, color=ACC)
        self.d_tiradas = Dato(fila2, "TIRADAS", grande=True)
        self.d_kami = Dato(fila2, "KAMIKAZES", grande=True)
        self.d_tiempo = Dato(fila2, "TIEMPO ACTIVO", grande=True)
        for i, d in enumerate((self.d_ronda, self.d_tiradas, self.d_kami, self.d_tiempo)):
            d.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0))
            fila2.columnconfigure(i, weight=1, uniform="a")

        uri = tk.Frame(der, bg=BG)
        uri.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        self.u_ini = Dato(uri, "INICIAL")
        self.u_act = Dato(uri, "ACTUAL")
        self.u_gan = Dato(uri, "GANADO", color=VERDE)
        self.u_gas = Dato(uri, "GASTADO", color=ROJO)
        self.u_neto = Dato(uri, "NETO", color=CIAN)
        for i, d in enumerate((self.u_ini, self.u_act, self.u_gan, self.u_gas, self.u_neto)):
            d.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0))
            uri.columnconfigure(i, weight=1, uniform="b")

        reg = tk.Frame(der, bg=PANEL)
        reg.grid(row=3, column=0, sticky="nsew", pady=(12, 0))
        tk.Label(reg, text="REGISTRO", bg=PANEL, fg=MUTED, font=(FUENTE, 8, "bold")).pack(anchor="w", padx=16, pady=(12, 4))
        marco = tk.Frame(reg, bg=PANEL)
        marco.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        self.texto = tk.Text(marco, bg="#0d1424", fg=TXT, font=("Consolas", 9), relief="flat", wrap="word",
                             height=8, padx=10, pady=8, state="disabled", highlightthickness=0)
        sb = tk.Scrollbar(marco, command=self.texto.yview)
        self.texto.config(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.texto.pack(side="left", fill="both", expand=True)
        self.texto.tag_config("hora", foreground=MUTED)
        self.texto.tag_config("ok", foreground=VERDE)
        self.texto.tag_config("mal", foreground=ROJO)

        pie = tk.Frame(r, bg=BG)
        pie.pack(fill="x", padx=22, pady=(0, 10))
        self.top_var = tk.BooleanVar(value=False)
        tk.Checkbutton(pie, text="Mantener esta ventana al frente", variable=self.top_var, bg=BG, fg=MUTED,
                       selectcolor=PANEL, activebackground=BG, activeforeground=TXT, font=(FUENTE, 9), highlightthickness=0, bd=0,
                       command=lambda: r.attributes("-topmost", self.top_var.get())).pack(side="left")
        tk.Label(pie, text="Si arrastras el mouse a una esquina de la pantalla en modo Normal, el bot se detiene.",
                 bg=BG, fg="#56627a", font=(FUENTE, 8)).pack(side="right")

    # ---------- acciones
    def hay_tesseract(self):
        return bool(getattr(self.bot, "OCR", False))

    def corriendo(self):
        return self.th is not None and self.th.is_alive()

    def elegir_gate(self, nombre):
        if self.corriendo():
            return
        self.gate = nombre
        for n, c in self.cartas.items():
            c.seleccionar(n == nombre)
        self.lbl_gate.config(text=f"PUERTA {nombre}")

    def set_modo(self, fondo, guardar=True):
        if self.corriendo():
            return
        self.bot.CFG["modo_fondo"] = fondo
        if guardar:
            try:
                try:
                    datos = json.load(open(self.bot.CFG_FILE, encoding="utf-8"))
                except Exception:
                    datos = dict(self.bot.CFG)
                datos["modo_fondo"] = fondo
                json.dump(datos, open(self.bot.CFG_FILE, "w", encoding="utf-8"), indent=2)
            except Exception:
                pass
        on, off = ("#21304f", ACC), (BORDE, MUTED)
        self.m_fondo.config(bg=on[0] if fondo else off[0], fg=on[1] if fondo else off[1])
        self.m_normal.config(bg=off[0] if fondo else on[0], fg=off[1] if fondo else on[1])
        if fondo:
            self.ayuda_modo.config(text="El bot trabaja con las ventanas del juego aunque estén tapadas y sin usar tu mouse ni tu teclado. "
                                        "Primero pulsa «Abrir el juego en segundo plano».")
            self.b_juego.pack(padx=18, fill="x", after=self.ayuda_modo)
        else:
            self.ayuda_modo.config(text="El bot usa tu mouse y teclado y necesita las dos ventanas del juego a la vista. "
                                        "No uses el PC mientras trabaja.")
            self.b_juego.pack_forget()
        self.actualizar_chip()

    def log(self, texto, tag=None):
        self.cola.put((time.strftime("%H:%M:%S"), texto, tag))

    def abrir_ajustes(self):
        if getattr(self, "_ajustes", None) is not None and self._ajustes.winfo_exists():
            self._ajustes.lift()
            return
        self._ajustes = VentanaAjustes(self)

    def iniciar(self):
        if self.corriendo():
            return
        S = self.S
        S.update({"ini": None, "act": None, "ganado": 0, "gastado": 0, "tiradas": 0, "kami": 0,
                  "fin": False, "fin_ok": False, "ronda": None, "rondas_total": None, "msg": "Iniciando..."})
        self.activo_seg = 0.0
        S["stop"].clear()
        S["run"].set()
        self.th = threading.Thread(target=self.bot.worker, args=(self.gate,), daemon=True)
        self.th.start()
        self.log(f"Iniciado: puerta {self.gate} · modo {'segundo plano' if self.bot.CFG.get('modo_fondo') else 'normal'}", "ok")

    def pausar(self):
        if not self.corriendo():
            return
        if self.S["run"].is_set():
            self.S["run"].clear()
            self.log("Pausado")
        else:
            self.S["run"].set()
            self.log("Reanudado", "ok")

    def detener(self):
        if not self.corriendo():
            return
        self.S["stop"].set()
        self.S["run"].set()
        self.log("Deteniendo...", "mal")

    def cerrar(self):
        self.S["stop"].set()
        self.S["run"].set()
        self.root.after(200, self.root.destroy)

    # ---------- juego en segundo plano
    def abrir_juego(self):
        if self.abriendo or self.corriendo():
            return
        self.abriendo = True
        self.b_juego.set(activo=False, texto="Abriendo el juego...")
        threading.Thread(target=self._abrir_juego, daemon=True).start()

    def _powershell(self, cmd):
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True,
                               timeout=60, creationflags=SIN_VENTANA)
            return r.stdout.strip()
        except Exception:
            return ""

    def _abrir_juego(self):
        try:
            ruta = ""
            f = os.path.join(AQUI, "ruta_juego.txt")
            if os.path.exists(f):
                ruta = open(f, encoding="utf-8").read().strip()
            vivo = self._powershell("(Get-Process -Name 'WordGalaxy-Client' -ErrorAction SilentlyContinue | "
                                    "Select-Object -First 1).Path")
            if vivo and os.path.exists(vivo):
                ruta = vivo
            if not (ruta and os.path.exists(ruta)):
                self.log("Buscando WordGalaxy-Client.exe ...")
                ruta = self._powershell(
                    "Get-ChildItem -Path $env:LOCALAPPDATA,$env:ProgramFiles,'C:\\Program Files (x86)',"
                    "$env:USERPROFILE\\Desktop,$env:USERPROFILE\\Downloads,$env:APPDATA -Filter WordGalaxy-Client.exe "
                    "-Recurse -Depth 5 -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName")
            if not (ruta and os.path.exists(ruta)):
                ev, res = threading.Event(), {}

                def pedir():
                    res["r"] = filedialog.askopenfilename(
                        title="Selecciona WordGalaxy-Client.exe", filetypes=[("Programa", "*.exe")])
                    ev.set()
                self.root.after(0, pedir)
                ev.wait()
                ruta = res.get("r", "")
            if not (ruta and os.path.exists(ruta)):
                self.log("No se encontró el juego.", "mal")
                return
            open(f, "w", encoding="utf-8").write(ruta)
            self.log("Cerrando el juego si estaba abierto...")
            subprocess.run(["taskkill", "/f", "/im", "WordGalaxy-Client.exe"], capture_output=True,
                           creationflags=SIN_VENTANA)
            time.sleep(4)
            puerto = self.bot.CFG.get("puerto_debug", 9222)
            self.log(f"Abriendo el juego con el puerto {puerto}...")
            subprocess.Popen([ruta, f"--remote-debugging-port={puerto}", "--remote-allow-origins=*",
                              "--disable-renderer-backgrounding", "--disable-background-timer-throttling",
                              "--disable-backgrounding-occluded-windows"],
                             cwd=os.path.dirname(ruta), creationflags=0x00000008 | 0x00000200)
            for _ in range(30):
                if self.bot.puerto_responde() is not None:
                    self.log("Juego listo en segundo plano. Inicia sesión si te lo pide y pulsa INICIAR.", "ok")
                    return
                time.sleep(1)
            self.log("El juego no abrió el puerto de control. Ábrelo de nuevo con este botón.", "mal")
        except Exception as e:
            self.log(f"Error al abrir el juego: {e}", "mal")
        finally:
            self.abriendo = False

    def vigilar_conexion(self):
        while True:
            try:
                self.conexion = self.bot.puerto_responde()
            except Exception:
                self.conexion = None
            time.sleep(3)

    # ---------- refresco
    def actualizar_chip(self):
        if not self.bot.CFG.get("modo_fondo", True):
            self.chip.config(text="  MODO NORMAL  ", fg=MUTED)
        elif self.conexion:
            n = len(self.conexion)
            self.chip.config(text=f"  ● JUEGO CONECTADO ({n} ventana{'s' if n != 1 else ''})  ", fg=VERDE)
        else:
            self.chip.config(text="  ● JUEGO SIN CONEXIÓN  ", fg=AMAR)

    def refrescar(self):
        S = self.S
        ahora = time.time()
        dt, self.t_ult = ahora - self.t_ult, ahora
        if self.f6:
            self.f6 = False
            self.pausar()
        vivo = self.corriendo()
        pausado = vivo and not S["run"].is_set()
        if vivo and not pausado:
            self.activo_seg += dt

        msg = S.get("msg", "")
        if vivo and not pausado:
            texto, color = "TRABAJANDO", VERDE
        elif pausado:
            texto, color = "EN PAUSA", AMAR
        else:
            falla = msg.startswith(("Error", "Sin conexion", "No encuentro", "No se", "No pude", "La nave", "Sin uridium"))
            texto, color = ("DETENIDO · REVISAR", ROJO) if falla else ("DETENIDO", MUTED)
        self.punto.config(fg=color)
        self.estado.config(text=texto, fg=color)
        self.msg.config(text=msg if (vivo or msg != "Listo") else "Elige una puerta y pulsa INICIAR.")

        # botones
        self.b_inicio.set(activo=not vivo)
        self.b_pausa.set(activo=vivo, texto="▶  Reanudar" if pausado else "‖  Pausar")
        self.b_stop.set(activo=vivo)
        if not self.abriendo:
            self.b_juego.set(activo=not vivo, texto="Abrir el juego en segundo plano")

        # datos
        r, tot = S.get("ronda"), S.get("rondas_total")
        self.d_ronda.set(f"{r}/{tot}" if (r and tot) else (f"{r}" if r else "—"))
        self.d_tiradas.set(str(S.get("tiradas", 0)))
        self.d_kami.set(str(S.get("kami", 0)))
        h, rem = divmod(int(self.activo_seg), 3600)
        m, s = divmod(rem, 60)
        self.d_tiempo.set(f"{h:02d}:{m:02d}:{s:02d}")
        ini, act = S.get("ini"), S.get("act")
        self.u_ini.set(f"{ini:,}" if ini is not None else "N/D")
        self.u_act.set(f"{act:,}" if act is not None else "N/D")
        self.u_gan.set(f"+{S.get('ganado', 0):,}")
        self.u_gas.set(f"-{S.get('gastado', 0):,}")
        self.u_neto.set(f"{act - ini:+,}" if (ini is not None and act is not None) else "N/D")

        # registro (solo cuando cambia el mensaje de fondo)
        clave = re.sub(r"[\d.,]+", "#", msg)
        if clave != self.ultimo_key and msg and msg != "Listo" and msg != "Iniciando...":
            self.ultimo_key = clave
            mal = msg.startswith(("Error", "Sin conexion", "No encuentro", "No se", "No pude", "Conexion perdida"))
            self.log(msg, "mal" if mal else None)
        self.vaciar_cola()
        self.actualizar_chip()
        self.root.after(250, self.refrescar)

    def vaciar_cola(self):
        hubo = False
        while True:
            try:
                hora, txt, tag = self.cola.get_nowait()
            except queue.Empty:
                break
            self.texto.config(state="normal")
            self.texto.insert("end", hora + "  ", "hora")
            self.texto.insert("end", txt + "\n", tag or ())
            n = int(self.texto.index("end-1c").split(".")[0])
            if n > 400:
                self.texto.delete("1.0", f"{n - 400}.0")
            self.texto.config(state="disabled")
            hubo = True
        if hubo:
            self.texto.see("end")


def main():
    root = tk.Tk()
    root.withdraw()
    if not asegurar_dependencias(root):
        root.destroy()
        return
    try:
        import bot_puertas as bot
    except Exception as e:
        messagebox.showerror("No se pudo cargar el bot", f"{e}\n\nAsegúrate de que bot_puertas.py esté en la misma carpeta.")
        root.destroy()
        return
    root.deiconify()
    App(root, bot)
    root.mainloop()


if __name__ == "__main__":
    main()
