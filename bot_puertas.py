# -*- coding: utf-8 -*-
# Bot Puertas Galacticas - WordGalaxy (1920x1080)
# Uso: python bot_puertas.py ALPHA   |   python bot_puertas.py --coords
import sys, os, time, json, threading, base64
import numpy as np, cv2, mss, pyautogui, keyboard
import tkinter as tk

try:
    import pytesseract, shutil
    _cands = [r"C:\Program Files\Tesseract-OCR\tesseract.exe",
              r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
              os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Tesseract-OCR", "tesseract.exe"),
              os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local", "Tesseract-OCR", "tesseract.exe")]
    _exe = next((p for p in _cands if os.path.exists(p)), None) or shutil.which("tesseract")
    if _exe:
        pytesseract.pytesseract.tesseract_cmd = _exe
    OCR = bool(_exe)
except Exception:
    OCR = False

pyautogui.FAILSAFE = True   # mouse a la esquina sup. izq. = parada de emergencia
pyautogui.PAUSE = 0.05

GATES = ["ALPHA", "BETA", "GAMMA", "DELTA", "KAPPA", "LAMBDA", "KRONOS", "ZETA", "HADES"]
# NPC de cada ronda (nombre -> cantidad). Las demas GATES: agregar aqui con el mismo formato.
NPC_RONDAS = {
    "KRONOS": [
        {"Phoenix": 10, "Yamato": 30},
        {"Liberator": 30, "Defcom": 20},
        {"Piranha": 30, "Nostromo": 20},
        {"Bigboy": 30},
        {"Goliath": 8, "Vengeance": 20},
        {"Leonov": 30},
        {"Solace": 5, "Venom": 5, "Sentinel": 5, "Diminisher": 5, "Spectrum": 5},
        {"Spearhead": 15, "Revenge": 10},
        {"Lightning": 18, "Avenger": 12},
        {"Spearhead": 6, "Bastion": 12},
        {"Goliath": 10, "Spearhead": 10, "Aegis": 8, "Citadel": 6},
        {"Jade": 8, "Sapphire": 8, "Crimson": 8},
        {"Leonov": 6, "Bigboy": 5, "Cyborg": 3},
    ],
}
RONDAS = {g: len(v) for g, v in NPC_RONDAS.items()}      # total de rondas de cada GATE
CFG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config_puertas.json")

CFG = {
    "tab_puertas": [938, 72],
    "gate_x": 643,
    "gate_y": [277, 350, 423, 496, 569, 642, 715, 788, 861],   # con scroll arriba
    "scroll_punto": [1500, 600],
    "x100": [1047, 451],             # con scroll abajo
    "procesar": [930, 770],          # con scroll abajo
    "preparar_portal": [930, 960],   # con scroll abajo (boton naranja)
    "boton_start": [1168, 73],
    "teclas_cambio": ["ctrl+tab", "ctrl+shift+tab"],
    "espera_start": 12,
    "uridium_region": [1590, 64, 80, 18],    # barra superior del launcher (solo el numero, sin el icono)
    "uridium_juego": [144, 116, 76, 18],     # panel "Usuario" del juego (fila de uridium)
    "mapa_region": [1660, 882, 230, 143],    # area interior del minimapa
    "titulo_region": [1660, 863, 140, 16],   # texto "2-1 184/24"
    "aros": {   # posicion en pantalla del aro de cada GATE en el minimapa 2-1
        "ALPHA":  [1848, 897],
        "KRONOS": [1829, 904],
        "BETA":   [1856, 918],
        "GAMMA":  [1874, 931],
        "LAMBDA": [1846, 932],
        "ZETA":   [1869, 943],
        "KAPPA":  [1869, 950],
        "DELTA":  [1893, 944],
    },
    "mini_mapa": [1672, 887, 230, 143],       # area interior del minimapa (en el juego)
    "slot_kamikaze": [1137, 923],
    "tecla_kamikaze": "0",
    "pet_boton": [1637, 358, 52, 33],         # x, y, w, h del boton del PET (play / llave)
    "centro_nave": [960, 540],
    "radio_juntos": 300,
    "min_npc_juntos": 6,
    "espera_juntos_max": 40,
    "cooldown_kamikaze": 22,              # seg minimos huyendo tras lanzar (el enfriamiento real es 25)
    "pet_comprar_comb": [1718, 372],      # boton gota con "+"
    "pet_barra_comb": [1821, 66],         # x inicial y largo (px) de la barra de combustible
    "comb_min": 4,                        # % minimo para comprar
    "comb_max": 10,                       # % maximo para comprar
    "spread_max_mini": 12,      # px max (en el minimapa) entre los NPC para considerarlos todos juntos
    "estable_seg": 0.7,         # segundos que deben seguir juntos antes de lanzar
    "tiempo_tramo": 6,
    "puntos_huida": [[0, 0], [0, 1], [1, 1], [1, 0]],   # (x, y) de 0 a 1 dentro del minimapa; en este orden
    "huida_margen": 14,                                  # px de separacion con el borde del minimapa
    "quieto_llegada": 0.5,
    "intervalo_tirada": 0.5,
    "costo_tirada": 10000,
    "max_intentos_salto": 60,
}
if os.path.exists(CFG_FILE):
    try:
        CFG.update(json.load(open(CFG_FILE, encoding="utf-8")))
    except Exception:
        pass
else:
    json.dump(CFG, open(CFG_FILE, "w", encoding="utf-8"), indent=2)

_RAPIDO = {"intervalo_tirada": 0.3, "estable_seg": 0.7, "espera_inicio_ronda": 5, "quieto_seg": 0.6, "quieto_huida": 0.3}
if CFG.get("version_tiempos") != 3:
    CFG.update(_RAPIDO)
    CFG["version_tiempos"] = 3
    try:
        json.dump(CFG, open(CFG_FILE, "w", encoding="utf-8"), indent=2)
    except Exception:
        pass

sct = mss.mss()

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_puertas.log")

def log(m):
    try:
        open(LOG_FILE, "a", encoding="utf-8").write(time.strftime("%H:%M:%S ") + str(m) + "\n")
    except Exception:
        pass

# =====================================================================
#  MODO FONDO (sin usar tu mouse/teclado ni tener que ver el juego)
#  El juego se abre con --remote-debugging-port (iniciar_juego_fondo.bat)
#  y el bot lee la imagen y manda clics/teclas directo a cada ventana
#  por el protocolo DevTools de Chromium (el cliente es Electron).
# =====================================================================
try:
    import websocket          # pip install websocket-client
    WS_OK = True
except Exception:
    WS_OK = False
import urllib.request

CFG.setdefault("modo_fondo", True)
CFG.setdefault("puerto_debug", 9222)

_VK = {"j": 0x4A, "0": 0x30, "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34, "5": 0x35,
       "6": 0x36, "7": 0x37, "8": 0x38, "9": 0x39}

class Pestana:
    """Una ventana del cliente (launcher o juego) controlada por DevTools."""
    def __init__(self, t):
        self.id = t["id"]
        self.url = t.get("url", "")
        self.ws = websocket.create_connection(t["webSocketDebuggerUrl"], timeout=15,
                                              suppress_origin=True)
        self.n = 0
        self.lock = threading.Lock()
        self.off = (0, 0)
        self.t_off = 0.0
        self.frame = None
        self.t_frame = 0.0
        for m, p in (("Emulation.clearDeviceMetricsOverride", {}),      # por si el visor quedo atascado
                     ("Emulation.setFocusEmulationEnabled", {"enabled": True}),
                     ("Page.setWebLifecycleState", {"state": "active"})):
            try:
                self.call(m, **p)
            except Exception:
                pass

    def call(self, metodo, **params):
        with self.lock:
            self.n += 1
            n = self.n
            self.ws.send(json.dumps({"id": n, "method": metodo, "params": params}))
            while True:
                r = json.loads(self.ws.recv())
                if r.get("id") == n:
                    if "error" in r:
                        raise RuntimeError(f"{metodo}: {r['error']}")
                    return r.get("result", {})

    def js(self, expr):
        return self.call("Runtime.evaluate", expression=expr, returnByValue=True)["result"].get("value")

    def offset(self):
        """Posicion en pantalla del area del juego (para usar las mismas coordenadas de siempre)."""
        if time.time() - self.t_off < 10:
            return self.off
        try:
            sx, sy, ow, oh, iw, ih, titulo = self.js(
                "[screenX,screenY,outerWidth,outerHeight,innerWidth,innerHeight,document.title]")
            off = _offset_hwnd(titulo, iw, ih)
            if off is None:
                bx = (ow - iw) / 2.0
                off = (int(round(sx + bx)), int(round(sy + (oh - ih) - bx)))
            if "offset_fondo" in CFG:                 # ajuste manual opcional [dx, dy]
                off = (off[0] + CFG["offset_fondo"][0], off[1] + CFG["offset_fondo"][1])
            self.off, self.t_off = off, time.time()
            self.vw, self.vh = int(iw), int(ih)
        except Exception:
            pass
        return self.off

    def captura(self):
        if self.frame is not None and time.time() - self.t_frame < 0.15:
            return self.frame
        ox, oy = self.offset()
        try:
            r = self.call("Page.captureScreenshot", format="png", optimizeForSpeed=True)
        except Exception:
            r = self.call("Page.captureScreenshot", format="png")
        img = cv2.imdecode(np.frombuffer(base64.b64decode(r["data"]), np.uint8), cv2.IMREAD_COLOR)
        lienzo = np.zeros((1080, 1920, 3), np.uint8)
        h, w = img.shape[:2]
        x0, y0 = max(ox, 0), max(oy, 0)
        x1, y1 = min(ox + w, 1920), min(oy + h, 1080)
        if x1 > x0 and y1 > y0:
            lienzo[y0:y1, x0:x1] = img[y0 - oy:y1 - oy, x0 - ox:x1 - ox]
        self.frame, self.t_frame = lienzo, time.time()
        return lienzo

    def region(self, x, y, w, h):
        """Recorte (x, y, w, h) del cuadro completo de la ventana (coordenadas de pantalla)."""
        f = self.captura()
        return f[int(y):int(y) + int(h), int(x):int(x) + int(w)].copy()

    def _raton(self, tipo, x, y, **extra):
        ox, oy = self.offset()
        self.call("Input.dispatchMouseEvent", type=tipo, x=float(x - ox), y=float(y - oy), **extra)

    def click(self, x, y):
        self._raton("mouseMoved", x, y)
        time.sleep(0.05)
        self._raton("mousePressed", x, y, button="left", clickCount=1)
        time.sleep(0.05)
        self._raton("mouseReleased", x, y, button="left", clickCount=1)
        self.frame = None

    def rueda(self, x, y, dy):
        self._raton("mouseMoved", x, y)
        self._raton("mouseWheel", x, y, deltaX=0, deltaY=float(dy))
        self.frame = None

    def tecla(self, k):
        vk = _VK.get(k, ord(k.upper()) if len(k) == 1 else 0)
        code = ("Digit" + k) if k.isdigit() else ("Key" + k.upper() if len(k) == 1 else k)
        base = dict(windowsVirtualKeyCode=vk, nativeVirtualKeyCode=vk, key=k, code=code)
        self.call("Input.dispatchKeyEvent", type="rawKeyDown", **base)
        self.call("Input.dispatchKeyEvent", type="char", text=k, unmodifiedText=k, **base)
        time.sleep(0.1)
        self.call("Input.dispatchKeyEvent", type="keyUp", **base)
        self.frame = None

FONDO = {"on": False, "tabs": {}, "actual": None}

def _hwnds_cliente():
    """Ventanas de nivel superior del proceso WordGalaxy-Client."""
    import ctypes
    from ctypes import wintypes
    u, k = ctypes.windll.user32, ctypes.windll.kernel32
    out = []
    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(h, l):
        if u.IsWindowVisible(h):
            pid = wintypes.DWORD(); u.GetWindowThreadProcessId(h, ctypes.byref(pid))
            hp = k.OpenProcess(0x1000, False, pid.value)
            buf = ctypes.create_unicode_buffer(520); n = wintypes.DWORD(520)
            ok = k.QueryFullProcessImageNameW(hp, 0, buf, ctypes.byref(n)) if hp else 0
            if hp: k.CloseHandle(hp)
            if ok and buf.value.lower().endswith("wordgalaxy-client.exe"):
                out.append(h)
        return True
    u.EnumWindows(cb, 0)
    return out

def _offset_hwnd(titulo, iw, ih):
    """Ventana cuyo area cliente mide iw x ih (prefiere mismo titulo): esquina del area en pantalla."""
    try:
        import ctypes
        from ctypes import wintypes
        u = ctypes.windll.user32
        cands = []
        for h in _hwnds_cliente():
            r = wintypes.RECT(); u.GetClientRect(h, ctypes.byref(r))
            if abs(r.right - iw) <= 2 and abs(r.bottom - ih) <= 2:
                n = u.GetWindowTextLengthW(h); b = ctypes.create_unicode_buffer(n + 1)
                u.GetWindowTextW(h, b, n + 1)
                p = wintypes.POINT(0, 0); u.ClientToScreen(h, ctypes.byref(p))
                cands.append((b.value != titulo, (p.x, p.y)))
        if cands:
            cands.sort(key=lambda c: c[0])
            return cands[0][1]
    except Exception:
        pass
    return None

def fondo_ventanas_visibles():
    """Minimizada no dibuja: la restaura SIN activarla y la manda al fondo (detras de tus programas)."""
    try:
        import ctypes
        u = ctypes.windll.user32
        for h in _hwnds_cliente():
            if u.IsIconic(h):
                u.ShowWindow(h, 4)                                          # SW_SHOWNOACTIVATE
                u.SetWindowPos(h, 1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)  # HWND_BOTTOM, sin activar
    except Exception:
        pass

def fondo_conectar():
    """Conecta (o reconecta) con todas las ventanas del cliente. True si hay al menos una."""
    if not (CFG.get("modo_fondo") and WS_OK):
        return False
    try:
        lst = json.load(urllib.request.urlopen(f"http://127.0.0.1:{CFG['puerto_debug']}/json", timeout=3))
    except Exception:
        FONDO["on"] = False
        return False
    vivos = {t["id"]: t for t in lst if t.get("type") == "page" and t.get("webSocketDebuggerUrl")}
    for tid in list(FONDO["tabs"]):
        if tid not in vivos:
            FONDO["tabs"].pop(tid, None)
    for tid, t in vivos.items():
        if tid not in FONDO["tabs"]:
            try:
                FONDO["tabs"][tid] = Pestana(t)
            except Exception:
                pass
    if FONDO["actual"] not in FONDO["tabs"].values():
        FONDO["actual"] = next(iter(FONDO["tabs"].values()), None)
    FONDO["on"] = bool(FONDO["tabs"])
    return FONDO["on"]

def _tab():
    if FONDO["actual"] is None:
        fondo_conectar()
    if FONDO["actual"] is None:
        raise RuntimeError("Sin conexion con el juego (abrelo con iniciar_juego_fondo.bat)")
    return FONDO["actual"]

def _fondo_op(fn):
    """Ejecuta una operacion en la ventana actual; si falla, reconecta y reintenta una vez."""
    try:
        return fn(_tab())
    except Exception:
        actual_url = FONDO["actual"].url if FONDO["actual"] else None
        fondo_ventanas_visibles()
        for t in list(FONDO["tabs"].values()):
            try: t.ws.close()
            except Exception: pass
        FONDO["tabs"].clear(); FONDO["actual"] = None
        time.sleep(0.3)
        fondo_conectar()
        for t in FONDO["tabs"].values():       # volver a la misma ventana si sigue abierta
            if t.url == actual_url:
                FONDO["actual"] = t
        return fn(_tab())

def grab(x, y, w, h):
    if FONDO["on"]:
        return _fondo_op(lambda t: t.region(x, y, w, h))
    img = np.array(sct.grab({"left": int(x), "top": int(y), "width": int(w), "height": int(h)}))
    return img[:, :, :3]

def click(x, y):
    if FONDO["on"]:
        _fondo_op(lambda t: t.click(x, y)); return
    pyautogui.moveTo(x, y, duration=0.15)
    pyautogui.click()

def tecla(k):
    if FONDO["on"]:
        _fondo_op(lambda t: t.tecla(k)); return
    keyboard.press(k); time.sleep(0.12); keyboard.release(k)

def _ocr_numero(reg):
    """Lee un numero con puntos/comas (p. ej. 12.590.980) probando varios preprocesados y votando."""
    import re, collections
    votos = collections.Counter()
    gris = cv2.cvtColor(reg, cv2.COLOR_BGR2GRAY)
    for esc, interp, thr in ((4, cv2.INTER_LANCZOS4, 140), (6, cv2.INTER_CUBIC, "otsu"),
                             (8, cv2.INTER_CUBIC, 140), (4, cv2.INTER_LANCZOS4, "otsu")):
        g = cv2.resize(gris, None, fx=esc, fy=esc, interpolation=interp)
        if thr == "otsu":
            _, b = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        else:
            _, b = cv2.threshold(g, thr, 255, cv2.THRESH_BINARY)
        if b.mean() < 127:
            b = 255 - b
        b = cv2.copyMakeBorder(b, 14, 14, 14, 14, cv2.BORDER_CONSTANT, value=255)
        t = pytesseract.image_to_string(b, config="--psm 7 -c tessedit_char_whitelist=0123456789.,").strip()
        if re.fullmatch(r"\d{1,3}([.,]\d{3}){1,3}", t):
            votos[t] += 1
    if not votos:
        return None
    return int(re.sub(r"\D", "", votos.most_common(1)[0][0]))

def leer_uridium():
    """Uridium actual: del launcher (barra superior) o del juego (panel Usuario), segun la ventana activa."""
    if not OCR:
        return None
    try:
        reg = CFG["uridium_region"] if en_launcher() else CFG["uridium_juego"]
        return _ocr_numero(grab(*reg))
    except Exception as e:
        log(f"leer uridium fallo: {e}")
        return None

# ---------- minimapa: se ubica por su marco (el panel puede cambiar de lugar) ----------
# posicion de cada aro relativa a (borde derecho, borde superior) del marco del minimapa
ARO_REL = {
    "KRONOS": (-70.9, 21.1),
    "LAMBDA": (-54.6, 49.4),
    "ALPHA":  (-51.6, 14.4),
    "BETA":   (-44.6, 36.4),
    "ZETA":   (-31.9, 60.1),
    "KAPPA":  (-31.6, 66.4),
    "GAMMA":  (-26.6, 49.4),
    "DELTA":  (-7.6, 60.4),
}
_MARCO = {"v": None, "t": 0.0}

def detectar_marco(img=None, x0=1480, y0=760, w=440, h=320):
    if img is None:
        img = grab(x0, y0, w, h)
    r = img.astype(int)
    B, G, R = r[:, :, 0], r[:, :, 1], r[:, :, 2]
    m = (abs(R - G) < 12) & (abs(G - B) < 14) & (R > 105) & (R < 175)
    ys = [y0 + i for i, v in enumerate(m.sum(axis=1)) if v > 150]
    xs = [x0 + i for i, v in enumerate(m.sum(axis=0)) if v > 90]
    top = None
    for a in ys:
        if any(143 <= b - a <= 145 for b in ys):
            top = a + 1
            break
    if top is None or not xs:
        return None
    return max(xs), top

def marco():
    ahora = time.time()
    if _MARCO["v"] is None or ahora - _MARCO["t"] > 3:
        v = detectar_marco()
        if v:
            _MARCO["v"], _MARCO["t"] = v, ahora
        elif _MARCO["v"] is None:
            _MARCO["v"], _MARCO["t"] = (1902, 885), ahora
    return _MARCO["v"]

def mapa_region():
    r, t = marco(); return (r - 231, t, 231, 143)

def mini_mapa():
    r, t = marco(); return (r - 230, t + 2, 228, 140)

def titulo_region():
    r, t = marco(); return (r - 231, t - 22, 240, 16)

def ubicacion():
    """'gg' (dentro de la GATE), '2-1' (mapa base) o '?' segun el ancho del titulo del minimapa."""
    reg = grab(*titulo_region())
    cols = np.nonzero((reg.min(axis=2) > 200).any(axis=0))[0]
    ext = int(cols.max() - cols.min() + 1) if len(cols) else 0
    if ext >= 90:
        return "gg"
    if ext >= 40:
        return "2-1"
    return "?"

def _firma_titulo():
    """Mascara del texto blanco del titulo del minimapa ('2-1 191/27'): cambia mientras la nave se mueve."""
    return grab(*titulo_region()).min(axis=2) > 200

def esperar_llegada(timeout=None, quieto_seg=None):
    """Espera a que la nave deje de moverse (coordenadas del minimapa fijas). True si llego."""
    timeout = CFG.get("timeout_llegada", 90) if timeout is None else timeout
    quieto_seg = CFG.get("quieto_seg", 0.6) if quieto_seg is None else quieto_seg
    esperar(0.3)                      # dar tiempo a que la nave arranque tras el clic
    t0 = time.time()
    prev = _firma_titulo()
    t_quieto = time.time()
    while time.time() - t0 < timeout:
        esperar(0.15)
        act = _firma_titulo()
        if act.shape != prev.shape or int((act != prev).sum()) > 3:
            t_quieto = time.time()    # las coordenadas cambiaron: sigue moviendose
        prev = act
        if time.time() - t_quieto >= quieto_seg:
            return True
    return False

def presionar_j():
    tecla("j")

def leer_titulo_mapa():
    if not OCR:
        return ""
    try:
        g = cv2.cvtColor(grab(*titulo_region()), cv2.COLOR_BGR2GRAY)
        g = cv2.resize(g, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
        _, g = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if g.mean() < 127:
            g = 255 - g
        return pytesseract.image_to_string(g, config="--psm 7").upper()
    except Exception:
        return ""

def es_naranja(centro, ancho=80, alto=14):
    cx, cy = centro
    img = grab(cx - ancho // 2, cy - alto // 2, ancho, alto)
    b, g, r = img[:, :, 0].astype(int), img[:, :, 1].astype(int), img[:, :, 2].astype(int)
    m = (r > 200) & (g > 120) & (g < 215) & (b < 100)
    return m.mean() > 0.5

def _comps(img=None):
    x0, y0, w, h = 780, 110, 300, 940
    if img is None:
        img = grab(x0, y0, w, h)
    c = img.astype(int)
    B, G, R = c[:, :, 0], c[:, :, 1], c[:, :, 2]
    mx, mn = c.max(axis=2), c.min(axis=2)
    masks = {
        "bright": (mx - mn > 150) & (mx > 200),
        "brown": (R > B + 60) & (R > G + 30) & (mx > 90) & (mx < 190) & (mx - mn > 70),
        "teal": (R < 90) & (G > 85) & (G < 150) & (B > 120) & (B < 190),
    }
    out = {"bright": [], "brown": [], "teal": []}
    for k, m in masks.items():
        n, _, st, ce = cv2.connectedComponentsWithStats(m.astype(np.uint8) * 255)
        for i in range(1, n):
            x, y, ww, hh, area = st[i]
            if ww > 200 and 28 <= hh <= 70 and area > 0.5 * ww * hh:
                sub = m[y:y + hh, x:x + ww]
                gm = float(G[y:y + hh, x:x + ww][sub].mean())
                bm = float(B[y:y + hh, x:x + ww][sub].mean())
                out[k].append((int(x0 + ce[i][0]), int(y0 + ce[i][1]), int(y0 + y), int(hh), gm, bm))
    return out

def find_portal(img=None, c=None):
    """Boton naranja-amarillo alto PREPARAR PORTAL (aparece cuando la GATE esta COMPLETED)."""
    c = c or _comps(img)
    ty = c["teal"][0][1] if c["teal"] else None
    for (cx, cy, top, hh, gm, bm) in c["bright"]:
        if hh >= 44 and 140 <= gm <= 210 and bm < 90 and (ty is None or cy > ty):
            return cx, cy
    return None

def find_procesar(img=None, c=None):
    """(x, y, tipo, top): 'activo' = PROCESAR TIRADA, 'espera' = CONSULTAR TIRADA PENDIENTE."""
    c = c or _comps(img)
    ty = c["teal"][0][1] if c["teal"] else 10 ** 6
    for (cx, cy, top, hh, gm, bm) in c["bright"]:
        if cy < ty:
            return cx, cy, "activo", top
    for (cx, cy, top, hh, gm, bm) in c["brown"]:
        if cy < ty:
            return cx, cy, "espera", top
    return None

def x100_seleccionado(bx, by):
    img = grab(bx - 14, by - 6, 28, 12).astype(int)
    sat = img.max(axis=2) - img.min(axis=2)
    return (sat > 120).mean() > 0.35

def aro_de_gate(gate, i=0):
    """Aro de la GATE segun su posicion fija respecto al marco del minimapa."""
    if gate not in ARO_REL:
        return None
    r, t = marco()
    dx, dy = ARO_REL[gate]
    ex, ey = int(round(r + dx)), int(round(t + dy))
    ox, oy = [(0, 0), (1, 0), (0, 1), (-1, 0), (0, -1)][i % 5]
    return ex + ox, ey + oy

def buscar_aro_gate():
    """Aro blanco cercano a la base (arriba-derecha). Ignora izq-inferior y centro."""
    x0, y0, w, h = CFG["mapa_region"]
    img = grab(x0, y0, w, h)
    mask = cv2.inRange(img, (190, 190, 190), (255, 255, 255))
    mask = cv2.GaussianBlur(mask, (5, 5), 0)
    c = cv2.HoughCircles(mask, cv2.HOUGH_GRADIENT, dp=1.2, minDist=12,
                         param1=100, param2=12, minRadius=4, maxRadius=12)
    if c is None:
        return None
    mejores = []
    for (cx, cy, r) in c[0]:
        if cx > 0.6 * w and cy < 0.5 * h:          # zona de la base
            mejores.append((np.hypot(w - cx, cy), cx, cy))
    if not mejores:
        return None
    mejores.sort()
    _, cx, cy = mejores[0]
    return int(x0 + cx), int(y0 + cy)

# ---------------- estado compartido ----------------
S = {"run": threading.Event(), "stop": threading.Event(), "msg": "Listo",
     "ini": None, "act": None, "ganado": 0, "gastado": 0, "tiradas": 0, "fin": False, "kami": 0, "ronda": None, "rondas_total": None}

def esperar(seg):
    t = time.time()
    while time.time() - t < seg:
        if S["stop"].is_set():
            raise SystemExit
        while not S["run"].is_set():
            if S["stop"].is_set():
                raise SystemExit
            time.sleep(0.1)
        time.sleep(0.05)

_DESC = {"t": 0.0}

def buscar_dialogo_desconexion(img):
    """Centro del icono rojo (globo con X) del recuadro 'Conexion perdida', o None."""
    x0, y0, x1, y1 = 700, 330, 1220, 700
    c = img[y0:y1, x0:x1].astype(int)
    B, G, R = c[:, :, 0], c[:, :, 1], c[:, :, 2]
    m = ((R > 150) & (R - G > 80) & (R - B > 80)).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    n, _, st, ce = cv2.connectedComponentsWithStats(m)
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if 30 <= w <= 48 and 30 <= h <= 48 and abs(w - h) <= 6 and a > 0.55 * w * h:
            return int(x0 + ce[i][0]), int(y0 + ce[i][1])
    return None

def revisar_desconexion():
    """Si aparece 'Conexion perdida', da clic en 'Nueva conexion' (en la ventana donde aparezca)."""
    ahora = time.time()
    if ahora < _DESC["t"]:
        return
    _DESC["t"] = ahora + 3
    try:
        if FONDO["on"]:
            for t in list(FONDO["tabs"].values()):
                lienzo = np.zeros((1080, 1920, 3), np.uint8)
                lienzo[330:700, 700:1220] = t.region(700, 330, 520, 370)
                pos = buscar_dialogo_desconexion(lienzo)
                if pos:
                    t.click(pos[0] - 22, pos[1] + 45)          # boton "Nueva conexion"
                    log("conexion perdida: clic en Nueva conexion")
                    S["msg"] = "Conexion perdida - clic en Nueva conexion"
                    _DESC["t"] = time.time() + 4
                    return
        else:
            pos = buscar_dialogo_desconexion(grab(0, 0, 1920, 1080))
            if pos:
                click(pos[0] - 22, pos[1] + 45)
                log("conexion perdida: clic en Nueva conexion")
                S["msg"] = "Conexion perdida - clic en Nueva conexion"
                _DESC["t"] = time.time() + 4
    except Exception as e:
        log(f"revisar desconexion fallo: {e}")

def chk():
    esperar(0)
    revisar_desconexion()

def actualizar_uridium():
    """Actual = lectura validada. Gastado = tiradas x costo. Ganado = (actual - inicial) + gastado."""
    v = leer_uridium()
    if v is None:
        return
    ant = S["act"]
    if S["ini"] is None:
        S["ini"], S["act"] = v, v
        return
    if ant and abs(v - ant) > max(200000, ant * 0.02) and S.get("_cand") != v:
        S["_cand"] = v                 # salto muy grande: se acepta solo si la siguiente lectura coincide
        return
    S["_cand"] = None
    S["act"] = v
    S["gastado"] = S["tiradas"] * CFG["costo_tirada"]
    S["ganado"] = max(0, (S["act"] - S["ini"]) + S["gastado"])

def scroll(arriba):
    if FONDO["on"]:
        x, y = CFG["scroll_punto"]
        _fondo_op(lambda t: t.rueda(x, y, -5000 if arriba else 5000))
        esperar(0.5); return
    pyautogui.moveTo(*CFG["scroll_punto"])
    pyautogui.scroll(5000 if arriba else -5000)
    esperar(0.5)

def foco():
    pass

def en_launcher():
    """True si se ve el boton amarillo START de la barra superior (pestana de puertas)."""
    cx, cy = CFG["boton_start"]
    img = grab(cx - 40, cy - 10, 80, 20)
    B, G, R = img[:, :, 0].astype(int), img[:, :, 1].astype(int), img[:, :, 2].astype(int)
    return ((R > 220) & (G > 150) & (G < 225) & (B < 90)).mean() > 0.25

def _ventanas_wg():
    import ctypes
    from ctypes import wintypes
    u = ctypes.windll.user32
    out = []
    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(h, l):
        if u.IsWindowVisible(h):
            n = u.GetWindowTextLengthW(h)
            buf = ctypes.create_unicode_buffer(n + 1)
            u.GetWindowTextW(h, buf, n + 1)
            if buf.value.strip() == "WordGalaxy":
                out.append(h)
        return True
    u.EnumWindows(cb, 0)
    return out

def _traer(h):
    import ctypes
    u = ctypes.windll.user32
    k = ctypes.windll.kernel32
    try:
        u.ShowWindow(h, 9 if u.IsIconic(h) else 5)
        fg = u.GetForegroundWindow()
        t1 = u.GetWindowThreadProcessId(fg, None)
        t2 = k.GetCurrentThreadId()
        u.AttachThreadInput(t2, t1, True)
        u.SetForegroundWindow(h)
        u.BringWindowToTop(h)
        u.AttachThreadInput(t2, t1, False)
    except Exception:
        pass
    time.sleep(0.5)

def _ir_a(launcher):
    if FONDO["on"] or fondo_conectar():
        # modo fondo: solo se cambia la ventana "actual" del bot, no se toca el foco de Windows
        for _ in range(3):
            fondo_ventanas_visibles()
            fondo_conectar()
            for t in list(FONDO["tabs"].values()):
                FONDO["actual"] = t
                t.frame = None
                try:
                    if en_launcher() == launcher:
                        return True
                except Exception:
                    pass
            time.sleep(0.3)
        return False
    for _ in range(3):
        for h in _ventanas_wg():
            _traer(h)
            if en_launcher() == launcher:
                return True
    return False

def ir_launcher():
    return _ir_a(True)

def ir_juego():
    return _ir_a(False)

def portal_visible(gate, intentos=2):
    """True si en el minimapa del 2-1 se ve el aro (portal) de la GATE que estamos corriendo."""
    if gate not in ARO_REL:
        return False
    yy, xx = np.mgrid[-9:10, -9:10]
    d = np.hypot(xx, yy)
    anillo = (d >= 3.5) & (d <= 6.5)
    vistos = 0
    for _ in range(intentos):
        ex, ey = aro_de_gate(gate, 0)
        g = cv2.cvtColor(grab(ex - 11, ey - 11, 23, 23), cv2.COLOR_BGR2GRAY).astype(int)
        mejor = 0.0
        for ox in range(-2, 3):
            for oy in range(-2, 3):
                p = g[11 + oy - 9:11 + oy + 10, 11 + ox - 9:11 + ox + 10]
                if p.shape == d.shape:
                    mejor = max(mejor, float((p[anillo] > 140).mean()))
        if mejor >= CFG.get("umbral_aro", 0.12):
            vistos += 1
        esperar(0.08)
    return vistos >= intentos

def armar_puerta(gate):
    """Pestana de Puertas: tiradas hasta completar la GATE y PREPARAR PORTAL.
    Devuelve True (portal preparado), False (reintentar) o None (sin uridium: detener)."""
    idx = GATES.index(gate)
    S["msg"] = "Yendo a la pestana de Puertas"
    if not ir_launcher():
        S["msg"] = "No pude abrir la pestana de puertas (deja abiertas las 2 ventanas WordGalaxy)"
        return False
    scroll(True)
    click(*CFG["tab_puertas"]); esperar(0.8)
    scroll(True)
    S["msg"] = f"Seleccionando GATE {gate}"
    click(CFG["gate_x"], CFG["gate_y"][idx]); esperar(0.4)
    scroll(False)
    actualizar_uridium()

    S["msg"] = f"Verificando si GATE {gate} ya esta armada"
    fallos = 0
    pp = None
    scroll(False)
    x100_ok = False
    while True:
        chk()
        comps = _comps()                       # un solo analisis de pantalla por vuelta
        pp = find_portal(c=comps)
        if pp:
            break
        pr = find_procesar(c=comps)
        if not pr:
            fallos += 1
            S["msg"] = f"No encuentro boton ({fallos}/15)"
            if fallos % 3 == 0:
                scroll(False)
            if fallos >= 15:
                cv2.imwrite("bot_debug.png", grab(0, 0, 1920, 1080))
                S["msg"] = "No encuentro botones (ver bot_debug.png) - reintentando"
                return False
            esperar(0.5); continue
        fallos = 0
        px, py, tipo, top = pr
        if tipo == "espera":
            S["msg"] = "Esperando tirada pendiente..."
            esperar(0.2); continue
        if S["act"] is not None and S["act"] < CFG["costo_tirada"]:
            S["msg"] = "Sin uridium suficiente - bot detenido"
            return None
        bx, by = CFG["x100"][0], top - 300
        if not x100_ok:
            if not x100_seleccionado(bx, by):
                S["msg"] = "Seleccionando x100"
                click(bx, by); esperar(0.2); continue
            x100_ok = True
        click(px, py)
        S["tiradas"] += 1
        S["msg"] = f"Armando puerta - tirada #{S['tiradas']}"
        esperar(CFG["intervalo_tirada"])
        if S["tiradas"] % 8 == 0:
            actualizar_uridium()

    S["msg"] = "Preparando portal (mapa 2-1)"
    click(*pp); esperar(0.8)
    S["msg"] = "Volviendo a la pestana de la nave"
    if not ir_juego():
        S["msg"] = "No pude volver a la nave (deja abiertas las 2 ventanas WordGalaxy)"
        return False
    esperar(0.8)
    return True

def entrar_portal(gate):
    """Va al aro de la GATE en el 2-1, espera a llegar y salta con J. True si quedo dentro de la GG."""
    for i in range(CFG["max_intentos_salto"]):
        chk()
        loc = ubicacion()
        if loc == "gg":
            return True
        if loc != "2-1":
            # transicion del salto (titulo cambiando): esperar sin dar clics
            S["msg"] = "Saltando / cargando mapa, esperando..."
            esperar(0.7)
            continue
        aro = aro_de_gate(gate, i)
        if aro:
            S["msg"] = f"Yendo al portal de {gate} (intento {i + 1})"
            click(*aro)
        S["msg"] = f"Viajando al portal de {gate}... (esperando a que la nave llegue)"
        esperar_llegada()
        if ubicacion() != "2-1":
            continue              # ya salto: NO volver a dar clic
        S["msg"] = f"En el portal de {gate} - saltando (J)"
        presionar_j()
        # esperar a que el mapa cambie a la GG antes de cualquier otro clic
        t0 = time.time()
        while time.time() - t0 < CFG.get("espera_salto", 10):
            esperar(0.2)
            if ubicacion() != "2-1":
                break
    return ubicacion() == "gg"

def flujo(gate):
    """Ciclo completo y automatico hasta que el usuario detenga el bot:
    2-1 -> (portal en minimapa? si: entrar | no: armar puerta) -> GG -> combate -> 2-1 -> ..."""
    foco()
    S["msg"] = "Revisando pantalla de la nave"
    if not ir_juego():
        S["msg"] = "No encuentro la ventana de la nave (deja abiertas las 2 ventanas WordGalaxy)"
    vuelta = 0
    while True:
        chk()
        loc = ubicacion()
        if loc == "gg":
            vuelta += 1
            S["msg"] = f"Dentro de la GG {gate} (vuelta {vuelta}) - quieto, esperando NPC"
            S["fin"] = True
            esperar(1)
            combate(gate)
            S["msg"] = "GATE terminada - volviendo al 2-1"
            esperar(2)                     # dar tiempo a que cargue el 2-1
            continue
        if loc != "2-1":
            S["msg"] = "Cargando mapa / no reconozco el mapa, esperando..."
            if not ir_juego():
                esperar(1)
            esperar(0.8)
            continue

        # ---- en el 2-1: primero corroborar si el portal de la GATE ya esta en el minimapa ----
        S["msg"] = f"Corroborando en el minimapa si esta el portal de {gate}"
        if portal_visible(gate):
            S["msg"] = f"Portal de {gate} visible - yendo a entrar"
            if entrar_portal(gate):
                continue                   # el ciclo detecta 'gg' y entra al combate
            S["msg"] = "No se pudo entrar al portal - revisando de nuevo"
            esperar(1)
            continue

        # ---- no esta el portal: armar la puerta para que aparezca ----
        S["msg"] = f"No esta el portal de {gate} - armando la puerta"
        r = armar_puerta(gate)
        if r is None:
            return                         # sin uridium: detener
        if not r:
            esperar(2)                     # algo fallo: reintentar el ciclo
            ir_juego()
            continue
        # portal preparado: entrar directamente
        S["msg"] = "Corroborando ubicacion en el mapa"
        esperar(0.4)
        if not entrar_portal(gate):
            S["msg"] = "No se pudo entrar al portal - revisando de nuevo"
            esperar(1)

# ---------------- COMBATE (kamikaze) ----------------
TPL_PLAY = cv2.imdecode(np.frombuffer(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAABYAAAAWCAAAAADh3zPnAAABN0lEQVQYGW3BXytDYRwH8O9vO2fnOW5EuVDkZknj7JIUSZLQUsTSJkTMC/A2vAM3XLpUiruVkhRr1nFspvyZKNGitp1znvNYY+2fz4eW8B8Kw/SgAYWg3aa6UIcWEbD0G7MFNSiIhc6PdFJvRTWaR7Db7WT0RLIdFTSHUI9HRjZlXD53oIxmEfYxj4tbb4YRE034RTNY7mWKJLhdeNITejNKKICVPpVJEJxbX/d6PN2GIprGqqYyiSA4L+TfjdeHRzdAk1jTVCaREJyb+YJtR89yAE1g3a8yCY5jWxZ3MvFjFNE4NvxMkRzHshzxGTtACY1h068oLm5ykb/exR8aRUSTZdiC352fooxGEPFJbhe9XByigoax5ZXZ99U+qtEQtr22sZdFDRrETi56gjo0gKkjNKB+/OcHd0p3c2TA0SQAAAAASUVORK5CYII="), np.uint8), cv2.IMREAD_GRAYSCALE)
TPL_LLAVE = cv2.imdecode(np.frombuffer(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAB4AAAAcCAAAAABTk1B1AAAB8UlEQVQoFX3BT0hTARzA8e9vW1sqFfgHS1qBROA/HGZKVGjIqIgw0rBIE/FcHiQjIgjqUHQJgy556OCloxVKwjI0QbRlqTH/LKZl/9BRqDPfe3tvbdPnn8s+H2kgEaknEanDlJY8+Vd2s4XUYtrjlqFfX/842UQus678qDET8PvS2SCX2FBdoC/MjA6msk5q2KQ2X1se/zhhxyQXAIfCmiuFS6EP3RZMUgWUvRXW3N6uT7yexyTnIaN68F0ScUZzOrNd05ikEg5cDIz17iIqdKo00/jxIoBJzsLeRmNqpC8NVLfLade+tc9jkjPANeeCf+DTzkhlTpYjovqeWDDJaeBcuRaa+rJQnJ3hEGOp3cs6OUlUy/4VI2yz2602MX73dCRjEjdRzqYdimGJsgqqb8iTwhqpICa/MU3TDYvdJoqmjXvfJLFKTrDqRmqKbTE4WpGpqGH/e4+DOCljq7vZimr4h7u3ESPHidKtoFtBt8Kdg6oa8Xs9QpQcA/b9m8OWO5BM3qQGt/LCK7p/uCcCyBFw1gU6F6+q/SMl7rFODW4W6MvKdKA3CFIKpVWzba7CnNZgbkPXKwVocYUXCT7/DFIC3P/+mPqie3O0vewgpvmw+Dx9gBQDj34+4HpWa4Cn/c+Ia7I/JEYOkYgUkYi4SOQ/2Gm2AntuW80AAAAASUVORK5CYII="), np.uint8), cv2.IMREAD_GRAYSCALE)

def pantalla():
    return grab(0, 0, 1920, 1080)

def _quitar_ui(m):
    m[0:75, :] = 0; m[60:350, 0:240] = 0; m[860:1050, 0:330] = 0
    m[250:455, 1625:1910] = 0; m[830:1050, 1640:1910] = 0; m[1040:, :] = 0
    return m

def npcs_cerca(img):
    """(estimado de NPC cerca del centro, etiquetas individuales [(cx,cy,w,h,dist)])"""
    B, G, R = img[:, :, 0].astype(int), img[:, :, 1].astype(int), img[:, :, 2].astype(int)
    m = _quitar_ui(((R > 190) & (G < 60) & (B < 60)).astype(np.uint8) * 255)
    d = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_RECT, (30, 9)))
    n, _, st, ce = cv2.connectedComponentsWithStats(d)
    cx0, cy0 = CFG["centro_nave"]
    total, etiquetas = 0.0, []
    for i in range(1, n):
        x, y, w, h, a = st[i]
        raw = int((m[y:y + h, x:x + w] > 0).sum())
        if raw < 25:
            continue
        cx, cy = ce[i]
        dist = float(np.hypot(cx - cx0, cy - cy0))
        if dist <= CFG["radio_juntos"]:
            total += raw / 230.0
        if w < 200 and h < 40 and raw > 120:
            etiquetas.append((int(cx), int(cy), int(w), int(h), dist))
    etiquetas.sort(key=lambda e: e[4])
    return total, etiquetas

def hay_objetivo(img):
    B, G, R = img[:, :, 0].astype(int), img[:, :, 1].astype(int), img[:, :, 2].astype(int)
    m = _quitar_ui(((R > 110) & (R < 200) & (G < 45) & (B < 45)).astype(np.uint8) * 255)
    m = cv2.dilate(m, np.ones((3, 3), np.uint8))
    n, _, st, ce = cv2.connectedComponentsWithStats(m)
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if 40 <= w <= 110 and 35 <= h <= 90 and a < 0.5 * w * h:
            return True
    return False

def kamikaze_listo(img):
    """Enfriando = contador blanco '0:25' sobre el slot (o fondo casi negro). Listo = icono dorado/gris sobre fondo gris-azulado."""
    cx, cy = CFG["slot_kamikaze"]
    slot = img[cy - 16:cy + 16, cx - 16:cx + 16]
    if int((slot.min(axis=2) > 185).sum()) >= 15:      # digitos del contador
        return False
    v = [img[cy + dy - 3:cy + dy + 3, cx + dx - 3:cx + dx + 3].mean()
         for dx, dy in ((-13, -13), (13, -13), (-13, 13), (13, 13))]
    return float(np.mean(v)) > 30

def pet_estado(img):
    x, y, w, h = CFG["pet_boton"]
    g = cv2.cvtColor(img[y:y + h, x:x + w], cv2.COLOR_BGR2GRAY)
    sp = cv2.matchTemplate(g, TPL_PLAY, cv2.TM_CCOEFF_NORMED).max()
    sl = cv2.matchTemplate(g, TPL_LLAVE, cv2.TM_CCOEFF_NORMED).max()
    if sl > 0.8 and sl >= sp:
        return "llave"
    if sp > 0.8:
        return "play"
    return "otro"

def pet_centro():
    x, y, w, h = CFG["pet_boton"]
    return x + w // 2, y + h // 2

def npcs_minimapa(img):
    """(pixeles rojos, centro [x,y] en pantalla, dispersion max en px del minimapa)"""
    x0, y0, w, h = mini_mapa()
    r = img[y0:y0 + h, x0:x0 + w].astype(int)
    B, G, R = r[:, :, 0], r[:, :, 1], r[:, :, 2]
    m = (R > 130) & (R < 200) & (G < 35) & (B < 35)
    ys, xs = np.nonzero(m)
    if len(xs) < 4:
        return 0, None, 0.0
    mx, my = float(np.median(xs)), float(np.median(ys))
    spread = float(np.hypot(xs - mx, ys - my).max())
    return len(xs), (int(x0 + xs.mean()), int(y0 + ys.mean())), spread

def aros_minimapa(img):
    """Aros blancos (portales) visibles en el minimapa: [(x, y)] en pantalla."""
    x0, y0, w, h = mini_mapa()
    g = cv2.cvtColor(img[y0:y0 + h, x0:x0 + w], cv2.COLOR_BGR2GRAY)
    big = cv2.GaussianBlur(cv2.resize(g, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC), (5, 5), 0)
    c = cv2.HoughCircles(big, cv2.HOUGH_GRADIENT, dp=1, minDist=22, param1=120, param2=22,
                         minRadius=18, maxRadius=30)
    res = []
    if c is not None:
        for (cx, cy, r) in c[0]:
            px, py = int(cx / 4), int(cy / 4)
            zona = g[max(py - 7, 0):py + 8, max(px - 7, 0):px + 8]
            if (zona > 150).sum() >= 15:
                res.append((int(round(x0 + cx / 4)), int(round(y0 + cy / 4))))
    return sorted(res)

def nave_minimapa(img):
    """Posicion de la nave en pantalla segun la cruz (linea horizontal + vertical) del minimapa."""
    x0, y0, w, h = mini_mapa()
    g = cv2.cvtColor(img[y0:y0 + h, x0:x0 + w], cv2.COLOR_BGR2GRAY).astype(np.int16)
    if g.shape[0] < 10 or g.shape[1] < 10:
        return None
    sr = np.median(g[2:-2, :] - (g[:-4, :] + g[4:, :]) / 2, axis=1)
    sc = np.median(g[:, 2:-2] - (g[:, :-4] + g[:, 4:]) / 2, axis=0)
    if sr.max() < 10 or sc.max() < 10:
        return None
    ys = [i for i in np.nonzero(sr >= sr.max() * 0.6)[0] if abs(i - int(np.argmax(sr))) <= 2]
    xs = [i for i in np.nonzero(sc >= sc.max() * 0.6)[0] if abs(i - int(np.argmax(sc))) <= 2]
    return x0 + 2 + float(np.mean(xs)), y0 + 2 + float(np.mean(ys))

def esquinas():
    """Puntos de huida (pantalla) segun CFG['puntos_huida'] (fracciones 0..1 del minimapa)."""
    x0, y0, w, h = mini_mapa()
    k = int(CFG.get("huida_margen", 14))
    pts = CFG.get("puntos_huida") or [[0, 0], [0, 1], [1, 1], [1, 0]]
    return [(int(x0 + k + fx * (w - 2 * k)), int(y0 + k + fy * (h - 2 * k))) for fx, fy in pts]

def seleccionar_npc(img):
    _, etiquetas = npcs_cerca(img)
    for (cx, cy, w, h, d) in etiquetas[:4]:
        click(cx, cy - 60)          # la nave del NPC esta ~60 px arriba de su nombre
        esperar(0.15)
        if hay_objetivo(pantalla()):
            return True
    return False

def disparar_kamikaze():
    img = pantalla()
    if not hay_objetivo(img):
        S["msg"] = "Seleccionando NPC"
        seleccionar_npc(img)
    if pet_estado(pantalla()) == "play":
        click(*pet_centro()); esperar(0.4)
    for _ in range(3):
        tecla(CFG["tecla_kamikaze"])
        esperar(0.5)
        if not kamikaze_listo(pantalla()):
            S["kami"] += 1
            return True
    return False

def combustible_pct(img):
    """% de la barra de combustible del PET (la que esta junto a la gota)."""
    x0, largo = CFG["pet_barra_comb"]
    mejor = 0
    for y in range(315, 321):
        fila = img[y, x0:x0 + largo + 4]
        claro = fila.min(axis=1) > 170
        run = 0
        for v in claro:
            if not v:
                break
            run += 1
        mejor = max(mejor, run)
    return min(100.0, mejor * 100.0 / largo)

def _mejor_nombre(texto, nombres):
    """Nombre de NPC mas parecido dentro del texto leido (tolera letras basura al inicio/fin)."""
    import difflib, re
    t = re.sub("[^A-Za-z]", "", texto).lower()
    if len(t) < 3:
        return None, 0.0
    mejor = (None, 0.0)
    for n in nombres:
        nl = n.lower()
        for L in (len(nl) - 1, len(nl), len(nl) + 1):
            for i in range(0, max(1, len(t) - L + 1)):
                r = difflib.SequenceMatcher(None, t[i:i + L], nl).ratio()
                if r > mejor[1]:
                    mejor = (n, r)
    return mejor

def leer_nombres(img, nombres, max_etiquetas=4):
    """Lee (OCR) el nombre de los NPC cercanos (etiquetas rojas). Devuelve lista de nombres reconocidos."""
    if not OCR:
        return []
    B, G, R = img[:, :, 0].astype(int), img[:, :, 1].astype(int), img[:, :, 2].astype(int)
    m = _quitar_ui(((R > 190) & (G < 60) & (B < 60)).astype(np.uint8) * 255)
    _, etiquetas = npcs_cerca(img)
    cfg = "--psm 7 -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    res = []
    for (cx, cy, w, h, d) in etiquetas[:max_etiquetas]:
        if not (165 <= w <= 185):          # etiqueta individual (las encimadas no se leen)
            continue
        x, y = int(cx - w // 2), int(cy - h // 2)
        y0, y1, x0, x1 = max(y - 3, 0), y + h + 3, max(x, 0), x + w
        xa, xb = x0 + int((x1 - x0) * 0.40), x1 - int((x1 - x0) * 0.13)
        votos = {}
        crops = []
        for esc in (4, 6):
            c = cv2.resize(m[y0:y1, xa:xb], None, fx=esc, fy=esc, interpolation=cv2.INTER_CUBIC)
            crops.append(255 - c)
            r = cv2.resize(img[y0:y1, xa:xb, 2], None, fx=esc, fy=esc, interpolation=cv2.INTER_CUBIC)
            _, r = cv2.threshold(r, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            crops.append(255 - r if r.mean() < 127 else r)
        for c in crops:
            c = cv2.copyMakeBorder(c, 12, 12, 12, 12, cv2.BORDER_CONSTANT, value=255)
            try:
                t = pytesseract.image_to_string(c, config=cfg)
            except Exception:
                continue
            n, sc = _mejor_nombre(t, nombres)
            if n and sc >= 0.7:
                votos[n] = votos.get(n, 0) + 1
        if votos:
            n = max(votos, key=votos.get)
            if votos[n] >= 2:
                res.append(n)
    return res

def deducir_ronda(gate, obs):
    """Ronda (1..N) mas probable segun los nombres vistos (obs: nombre -> veces). None si aun no es claro."""
    import math
    rondas = NPC_RONDAS.get(gate)
    total = sum(obs.values())
    if not rondas or total < 3:
        return None
    pts = []
    for i, r in enumerate(rondas):
        suma = float(sum(r.values()))
        ll = 0.0
        for n, k in obs.items():
            p = r.get(n, 0) / suma
            ll += k * math.log(p if p > 0 else 0.02)
        pts.append((ll, i + 1))
    pts.sort(reverse=True)
    if len(pts) > 1 and pts[0][0] - pts[1][0] < 3:
        return None
    return pts[0][1]

def combate(gate):
    S["msg"] = "Combate: esperando NPC"
    cors = esquinas()
    idx = 0
    t_tramo = 0.0
    t_reparo = 0.0
    t_j = 0.0
    t_portal = 0.0
    t_loc = 0.0
    t_comb = 0.0
    t_disparo = 0.0
    t_uri = 0.0
    t_sin = None
    comprado = False
    fuera = 0
    primera = True          # inicio de ronda: NO huir ni acercarse, solo esperar a que lleguen todos
    fase = None
    estable = None
    detenido = False
    huida_dest = None       # punto de huida al que se dirige la nave
    t_mov = 0.0             # ultima vez que se detecto movimiento de la nave
    sig_prev = None
    vio_npc = False         # ya aparecieron NPC en esta ronda
    ronda = CFG.get("ronda_inicial")     # None = desconocida: se deduce leyendo los nombres de los NPC
    obs = {}                              # nombre de NPC -> veces visto (en la ronda actual)
    t_ocr = 0.0
    total_rondas = RONDAS.get(gate)
    fin_puerta = False      # termino la ultima ronda: quedarse quieto hasta volver al 2-1
    t_ronda = time.time()   # inicio de la ronda actual
    while True:
        chk()
        img = pantalla()
        ahora = time.time()

        S["ronda"] = ronda
        S["rondas_total"] = total_rondas
        if ahora - t_uri > 15:
            t_uri = ahora
            actualizar_uridium()

        # corroborar que seguimos dentro de la GG
        if ahora - t_loc > 0.5:
            t_loc = ahora
            fuera = fuera + 1 if ubicacion() == "2-1" else 0
            if fuera >= 2:
                S["msg"] = "Puerta terminada (de vuelta en 2-1) - quieto"
                return

        if fin_puerta:
            S["msg"] = f"Ronda {ronda}/{total_rondas} terminada - quieto, esperando volver al 2-1"
            esperar(0.2); continue

        # ronda desconocida: deducirla leyendo los nombres de los NPC que se ven en pantalla
        if ronda is None and total_rondas and OCR and ahora - t_ocr > 1.5:
            t_ocr = ahora
            for n in leer_nombres(img, list(set(k for r in NPC_RONDAS[gate] for k in r))):
                obs[n] = obs.get(n, 0) + 1
            r = deducir_ronda(gate, obs)
            if r:
                ronda = r
                S["msg"] = f"Ronda detectada por los NPC: {ronda}/{total_rondas}"

        # reparar PET (un solo clic)
        if pet_estado(img) == "llave" and ahora - t_reparo > 4:
            click(*pet_centro()); t_reparo = ahora
            esperar(0.4); continue

        # combustible del PET: un solo clic en la gota cuando esta entre comb_min y comb_max
        pct = combustible_pct(img)
        if pct > 15:
            comprado = False
        if (not comprado and CFG["comb_min"] <= pct <= CFG["comb_max"] and ahora - t_comb > 5):
            S["msg"] = f"Comprando combustible al PET ({pct:.0f}%)"
            click(*CFG["pet_comprar_comb"])
            comprado = True; t_comb = ahora
            esperar(0.4); continue

        listo = kamikaze_listo(img) and (ahora - t_disparo >= CFG["cooldown_kamikaze"])
        n_pix, centro, spread = npcs_minimapa(img)

        # movimiento de la nave: las coordenadas del minimapa cambian mientras se mueve
        sig = _firma_titulo()
        if sig_prev is None or sig.shape != sig_prev.shape or int((sig != sig_prev).sum()) > 3:
            t_mov = ahora
        sig_prev = sig

        if n_pix > 0:
            vio_npc = True

        # ---- ronda terminada: sin NPC en el minimapa ----
        if n_pix == 0:
            if t_sin is None:
                t_sin = ahora
            espera_ini = CFG.get("espera_inicio_ronda", 5)
            if not vio_npc and ahora - t_ronda < espera_ini:
                # recien llegamos (o recien saltamos): quedarse QUIETO unos segundos por si aparecen NPC
                S["msg"] = f"Inicio de ronda - quieto, esperando NPC ({espera_ini - (ahora - t_ronda):.0f}s)"
                esperar(0.15); continue
            if ahora - t_sin >= 1.0:
                if total_rondas and ronda is not None and ronda >= total_rondas and vio_npc:
                    fin_puerta = True       # ultimo NPC de la ultima ronda: no cliquear nada
                    continue
                primera = True; fase = None; estable = None; detenido = False; huida_dest = None
                portales = aros_minimapa(img)
                if portales:
                    # 1) ir al portal de la derecha y esperar a estar en sus coordenadas
                    der = max(portales, key=lambda p: p[0])      # portal de la derecha
                    S["msg"] = f"Ronda terminada - yendo al portal derecho ({len(portales)} portales)"
                    click(*der); t_portal = ahora
                    esperar_llegada()
                    # 2) ya en el portal: esperar a que el kamikaze este enfriado
                    while not (kamikaze_listo(pantalla()) and time.time() - t_disparo >= CFG["cooldown_kamikaze"]):
                        S["msg"] = "En el portal - esperando que el kamikaze se enfrie"
                        if pet_estado(pantalla()) == "llave" and time.time() - t_reparo > 4:
                            click(*pet_centro()); t_reparo = time.time()
                        esperar(0.2)
                    # 3) kamikaze listo: saltar a la siguiente ronda
                    S["msg"] = "Kamikaze listo - saltando a la siguiente ronda (J)"
                    presionar_j(); t_j = time.time()
                    if ronda is not None:
                        ronda += 1
                    obs.clear()
                    # nueva ronda: no dar ningun clic hasta que aparezcan los NPC
                    vio_npc = False; t_ronda = time.time(); t_sin = None; sig_prev = None
                    esperar(1.5); continue
                else:
                    S["msg"] = "Ronda terminada - buscando portales"
                esperar(0.3); continue
            esperar(0.15); continue
        t_sin = None

        if not listo:
            # kamikaze enfriando: huir IZQ-SUP -> IZQ-INF -> DER-INF -> DER-SUP
            # solo pasa al siguiente punto cuando la nave LLEGO (dejo de moverse).
            # Si se interrumpe antes de llegar, la proxima huida vuelve a ese mismo punto.
            fase = None; estable = None; detenido = False; primera = False
            cors = esquinas(); idx %= len(cors)
            radio = CFG.get("radio_llegada", 10)        # px del minimapa para considerar "llego"
            nave = nave_minimapa(img)

            def cerca(p):
                return nave is not None and np.hypot(nave[0] - p[0], nave[1] - p[1]) <= radio

            if huida_dest is None:
                # si ya esta parado cerca del punto pendiente, saltarlo y seguir con el siguiente
                if cerca(cors[idx]):
                    idx = (idx + 1) % len(cors)
                huida_dest = cors[idx]          # retomar el punto pendiente (idx no avanzo)
                click(*huida_dest); t_tramo = time.time(); t_mov = t_tramo
            else:
                if nave is not None:
                    llego = cerca(huida_dest)           # la cruz del minimapa ya esta en el punto
                    if not llego and t_mov > t_tramo and ahora - t_mov >= CFG.get("quieto_llegada", 0.5):
                        llego = True                    # se detuvo antes (borde del mapa / obstaculo)
                elif t_mov > t_tramo:
                    llego = ahora - t_mov >= CFG.get("quieto_huida", 0.3)
                else:
                    llego = ahora - t_tramo >= 2.0
                atorado = ahora - t_tramo > CFG.get("timeout_tramo", 45)
                if llego or atorado:
                    idx = (idx + 1) % len(cors)         # llego: ahora si, siguiente punto
                    huida_dest = cors[idx]
                    click(*huida_dest); t_tramo = time.time(); t_mov = t_tramo
            S["msg"] = f"Huyendo (kamikaze enfriando) - punto {idx + 1}/4"
            esperar(0.05); continue
        huida_dest = None                       # interrumpida: idx se queda en el punto no alcanzado

        if fase is None:
            fase = ahora
        n_cerca, etiquetas = npcs_cerca(img)
        en_pantalla = n_cerca >= 1 or len(etiquetas) > 0     # NPC visibles en la pantalla de la nave
        juntos = spread <= CFG["spread_max_mini"] and n_cerca >= 1

        if juntos:
            if estable is None:
                estable = ahora
            S["msg"] = f"NPC juntos en minimapa - confirmando ({ahora - estable:.1f}s)"
            listo_disparo = ahora - estable >= CFG["estable_seg"]
        else:
            estable = None
            listo_disparo = False
            if primera:
                S["msg"] = f"Esperando que lleguen todos los NPC (dispersion {spread:.0f}px)"
            else:
                S["msg"] = f"Acercando NPC (dispersion {spread:.0f}px)"

        if not listo_disparo and ahora - fase > CFG["espera_juntos_max"] and n_cerca >= 1:
            listo_disparo = True    # tiempo agotado: lanzar a los que haya cerca

        if listo_disparo:
            if not detenido:
                click(*CFG["centro_nave"])  # quedarse quieto (un solo clic)
                detenido = True
                esperar(0.1)
            if disparar_kamikaze():
                fase = None; estable = None; detenido = False
                t_disparo = time.time()
                t_tramo = 0.0               # huir de inmediato
            continue

        if not primera:
            # despues del primer kamikaze: acercarse a los NPC solo si NO se ven en la pantalla
            if en_pantalla:
                # ya se ven los NPC en la pantalla de la nave: quedarse quieto, sin clics al minimapa
                if not detenido:
                    click(*CFG["centro_nave"]); detenido = True
                if not juntos:
                    S["msg"] = f"NPC en pantalla - quieto, esperando que se junten (dispersion {spread:.0f}px)"
            else:
                if ahora - t_tramo > 3 and centro:
                    click(*centro); t_tramo = ahora
                detenido = False
        esperar(0.1)

def _hwnds_wordgalaxy():
    """Ventanas del juego: por proceso (WordGalaxy-Client.exe) y por titulo exacto 'WordGalaxy'."""
    hs = []
    for fn in (_hwnds_cliente, _ventanas_wg):
        try:
            for h in fn():
                if h not in hs:
                    hs.append(h)
        except Exception as e:
            log(f"enumerar ventanas ({fn.__name__}): {e}")
    return hs

def maximizar_ventanas():
    """Maximiza las ventanas del juego sin usar el mouse y las deja al fondo, sin activarlas."""
    import ctypes
    u = ctypes.windll.user32
    for t in list(FONDO["tabs"].values()):          # 1) por DevTools (no toca el foco)
        try:
            w = t.call("Browser.getWindowForTarget", targetId=t.id)
            t.call("Browser.setWindowBounds", windowId=w["windowId"], bounds={"windowState": "maximized"})
            log("maximizar por DevTools: ok")
        except Exception as e:
            log(f"maximizar por DevTools fallo: {e}")
    hs = _hwnds_wordgalaxy()
    log(f"ventanas de Windows encontradas: {len(hs)}")
    for h in hs:                                    # 2) por Windows
        try:
            if u.IsIconic(h):
                u.ShowWindow(h, 9)                  # SW_RESTORE
            if not u.IsZoomed(h):
                u.PostMessageW(h, 0x0112, 0xF030, 0)    # WM_SYSCOMMAND / SC_MAXIMIZE (no activa)
                time.sleep(0.3)
            if not u.IsZoomed(h):
                u.ShowWindow(h, 3)                  # SW_MAXIMIZE
                time.sleep(0.3)
            log(f"ventana {h}: maximizada = {bool(u.IsZoomed(h))}")
            u.SetWindowPos(h, 1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)   # al fondo, sin activar
        except Exception as e:
            log(f"maximizar ventana {h} fallo: {e}")
    for t in FONDO["tabs"].values():
        t.t_off = 0.0
        t.frame = None
    time.sleep(0.8)

def _es_launcher(t):
    """True si la ventana es la de las puertas (tiene el menu HANGAR); si no se puede leer, por pixeles."""
    try:
        v = t.js("!!(document.body && /HANGAR/i.test(document.body.innerText))")
        if v is not None:
            return bool(v)
    except Exception as e:
        log(f"leer pagina fallo: {e}")
    FONDO["actual"] = t
    t.frame = None
    return en_launcher()

def _click_start(t):
    """START del launcher: primero por la pagina (no depende del tamano), si no por coordenadas."""
    try:
        ok = t.js("""(()=>{const e=[...document.querySelectorAll('a,button,div,span')].find(
            x=>x.children.length<=2 && /^\\s*[\\u25B6\\u25BA]?\\s*START\\s*$/i.test(x.innerText||''));
            if(e){e.click();return true}return false})()""")
        log(f"click START por pagina: {ok}")
        if ok:
            return True
    except Exception as e:
        log(f"click START por pagina fallo: {e}")
    FONDO["actual"] = t
    click(*CFG["boton_start"])
    log("click START por coordenadas")
    return True

def preparar_ventanas():
    """Maximiza el launcher, pulsa START, maximiza la ventana de la nave y espera a que cargue."""
    S["msg"] = "Maximizando ventanas del juego"
    log("preparar_ventanas: inicio")
    maximizar_ventanas()

    def clasificar():
        launcher = juego = None
        fondo_conectar()
        for t in list(FONDO["tabs"].values()):
            if _es_launcher(t):
                launcher = t
            else:
                juego = t
        log(f"ventanas: {len(FONDO['tabs'])} | launcher={'si' if launcher else 'no'} | nave={'si' if juego else 'no'}")
        return launcher, juego

    launcher, juego = clasificar()
    if juego is None:
        if launcher is None:
            S["msg"] = "No encuentro las ventanas del juego (abrelo con iniciar_juego_fondo.bat)"
            return False
        S["msg"] = "Pulsando START para abrir la nave"
        _click_start(launcher)
        t0 = time.time()
        while time.time() - t0 < 90 and juego is None:     # esperar a que aparezca la ventana de la nave
            esperar(1)
            fondo_conectar()
            if len(FONDO["tabs"]) >= 2:
                maximizar_ventanas()
                launcher, juego = clasificar()
        if juego is None:
            S["msg"] = "No se abrio la ventana de la nave despues de START"
            return False

    S["msg"] = "Esperando a que aparezca la nave"
    t0 = time.time()
    while time.time() - t0 < CFG.get("espera_carga_nave", 240):
        FONDO["actual"] = juego
        juego.frame = None
        try:
            if ubicacion() in ("2-1", "gg"):
                S["msg"] = "Nave cargada"
                log("nave cargada")
                esperar(1)
                return True
        except Exception as e:
            log(f"esperar nave fallo: {e}")
        esperar(1)
    S["msg"] = "La nave no termino de cargar"
    return False

def worker(gate):
    try:
        S["run"].wait()
        if CFG.get("modo_fondo"):
            if not fondo_conectar():
                S["msg"] = "Sin conexion: abre el juego con iniciar_juego_fondo.bat"
                return
            if not preparar_ventanas():
                return
        flujo(gate)
    except SystemExit:
        S["msg"] = "Detenido"
    except Exception as e:
        import traceback
        open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_puertas.log"), "a", encoding="utf-8").write(traceback.format_exc() + "\n")
        S["msg"] = f"Error: {e}"
    finally:
        S["stop"].set()

def cmdline_cliente():
    """Linea de comandos con la que esta corriendo WordGalaxy-Client.exe (para ver si lleva el puerto)."""
    import subprocess
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process -Filter \"Name='WordGalaxy-Client.exe'\" | "
             "Select-Object ProcessId,CommandLine | Format-List | Out-String -Width 4000"],
            capture_output=True, text=True, timeout=20)
        return (r.stdout or r.stderr).strip()
    except Exception as e:
        return f"no pude leer la linea de comandos: {e}"

def puerto_responde():
    try:
        lst = json.load(urllib.request.urlopen(f"http://127.0.0.1:{CFG['puerto_debug']}/json", timeout=3))
        return [(t.get("type"), t.get("title")) for t in lst]
    except Exception:
        return None

# ---------------- GUI ----------------
def gui(gate):
    root = tk.Tk()
    root.title(f"Bot Puertas - {gate}")
    root.attributes("-topmost", True)
    root.geometry("320x280+20+120")
    lbl = tk.Label(root, text="", font=("Consolas", 10), justify="left", anchor="w")
    lbl.pack(fill="both", expand=True, padx=8, pady=8)
    state = {"th": None}

    def iniciar():
        if state["th"] is None:
            S["stop"].clear()
            state["th"] = threading.Thread(target=worker, args=(gate,), daemon=True)
            state["th"].start()
        S["run"].set()
        bp.config(text="Pausar", command=pausar)

    def pausar():
        S["run"].clear()
        bp.config(text="Reanudar", command=iniciar)
        S["msg"] = "Pausado"

    def detener():
        S["stop"].set(); S["run"].set()
        root.after(300, root.destroy)

    bf = tk.Frame(root); bf.pack(pady=6)
    bi = tk.Button(bf, text="Inicio", width=8, command=iniciar); bi.grid(row=0, column=0, padx=3)
    bp = tk.Button(bf, text="Pausar", width=8, command=pausar); bp.grid(row=0, column=1, padx=3)
    tk.Button(bf, text="Detener", width=8, command=detener).grid(row=0, column=2, padx=3)

    def toggle():
        if S["run"].is_set(): pausar()
        else: iniciar()
    keyboard.add_hotkey("f6", toggle)

    def refrescar():
        ini, act = S["ini"], S["act"]
        neto = (act - ini) if (ini is not None and act is not None) else None
        txt = (f"GATE: {gate}\n"
               f"Estado: {S['msg']}\n"
               f"Tiradas: {S['tiradas']}  Kamikazes: {S['kami']}\n"
               f"Uridium inicial: {ini if ini is not None else 'N/D'}\n"
               f"Uridium actual:  {act if act is not None else 'N/D'}\n"
               f"Ganado:  +{S['ganado']:,}\n"
               f"Gastado: -{S['gastado']:,}\n"
               f"Neto:    {neto:+,}" if neto is not None else
               f"GATE: {gate}\nEstado: {S['msg']}\nTiradas: {S['tiradas']}\nUridium: N/D (instala Tesseract)")
        lbl.config(text=txt + "\n\nF6 = pausa/inicio")
        root.after(500, refrescar)
    refrescar()
    root.mainloop()
    S["stop"].set(); S["run"].set()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--coords":
        print("Mueve el mouse. Ctrl+C para salir.")
        try:
            while True:
                print(pyautogui.position(), end="\r"); time.sleep(0.2)
        except KeyboardInterrupt:
            sys.exit()
    if len(sys.argv) > 2 and sys.argv[1] == "--modo":
        try:
            datos = json.load(open(CFG_FILE, encoding="utf-8"))
        except Exception:
            datos = dict(CFG)
        datos["modo_fondo"] = (sys.argv[2].lower() == "fondo")
        json.dump(datos, open(CFG_FILE, "w", encoding="utf-8"), indent=2)
        print("Modo fondo (sin usar tu mouse):" if datos["modo_fondo"] else "Modo normal (usa tu mouse, ventanas a la vista):", "ACTIVADO")
        sys.exit()
    if len(sys.argv) > 1 and sys.argv[1] == "--puerto":
        print(f"Esperando a que el juego abra el puerto {CFG['puerto_debug']} (hasta 25 s)...")
        for _ in range(25):
            r = puerto_responde()
            if r is not None:
                print(f"OK: el puerto responde. Paginas: {r}")
                break
            time.sleep(1)
        else:
            print("NO responde. El juego no abrio el puerto de control.")
            print("Linea de comandos del juego:")
            print(cmdline_cliente())
        sys.exit()
    if len(sys.argv) > 1 and sys.argv[1] == "--diag":
        print("websocket-client instalado:", WS_OK, "| modo_fondo:", CFG.get("modo_fondo"))
        try:
            lst = json.load(urllib.request.urlopen(f"http://127.0.0.1:{CFG['puerto_debug']}/json", timeout=3))
            print("Puerto", CFG["puerto_debug"], "responde. Paginas:", [(t.get("type"), t.get("title")) for t in lst])
        except Exception as e:
            print("Puerto", CFG["puerto_debug"], "NO responde:", e)
        print("Ventanas por proceso:", len(_hwnds_cliente()), "| por titulo:", len(_ventanas_wg()))
        print("Linea de comandos del juego:")
        print(cmdline_cliente())
        hs = _ventanas_wg()
        print("Ventanas WordGalaxy encontradas:", len(hs))
        for i, h in enumerate(hs):
            _traer(h)
            print(f"  ventana {i}: en_launcher = {en_launcher()}")
            cv2.imwrite(f"diag_{i}.png", grab(0, 0, 1920, 1080))
        print("Resolucion pyautogui:", pyautogui.size(), "| OCR:", OCR)
        sys.exit()
    g = (sys.argv[1] if len(sys.argv) > 1 else "KRONOS").upper()
    if g not in GATES:
        print("GATE invalida:", GATES); sys.exit(1)
    gui(g)