#!/usr/bin/env python3
"""
Visualizzatore di calcolo combinatorio.

Disegna il diagramma ad albero di:
  - disposizioni con ripetizione   D'(n,k) = n^k
  - disposizioni semplici          D(n,k)  = n(n-1)...(n-k+1)
  - permutazioni semplici          P(n)    = n!
  - permutazioni con ripetizione   P(n; k1, k2, ...) = n! / (k1! k2! ...)
  - combinazioni semplici          C(n,k)  = D(n,k) / k!

Ogni colonna dell'albero e' un "passo" e riporta quanti nodi contiene,
cosi' il legame con la formula e' visibile direttamente nel disegno.

Requisiti: Python 3.8+ e matplotlib  (pip install matplotlib)
"""

import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from collections import Counter
from math import comb, factorial, perm, prod

from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
# import espliciti: servono a PyInstaller per includere i formati di salvataggio
import matplotlib.backends.backend_pdf  # noqa: F401
import matplotlib.backends.backend_svg  # noqa: F401

# ---------------------------------------------------------------------------
# Parametri grafici
# ---------------------------------------------------------------------------
MAX_FOGLIE = 500        # oltre questo numero l'albero non viene disegnato
PASSO_Y = 26            # distanza verticale tra due foglie (pixel)
MARGINE = 40
SPAZIO_TESTATA = 80     # spazio in alto per le intestazioni dei passi
DPI = 100

COLORE_RAMI = "#6b7280"
COLORE_TESTO = "#1f2937"
COLORE_PASSI = "#1d4ed8"
COLORE_CONTATORE = "#9ca3af"

TIPI = {
    "Disposizioni con ripetizione": "dr",
    "Disposizioni semplici": "ds",
    "Permutazioni semplici": "ps",
    "Permutazioni con ripetizione": "pr",
    "Combinazioni semplici": "cs",
}

_APICI = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")


def apice(n):
    return str(n).translate(_APICI)


# figura invisibile usata solo per misurare quanto spazio occupa un testo
_FIG_MISURE = Figure(dpi=DPI)
FigureCanvasAgg(_FIG_MISURE)


def larghezza_testo(testo, dimensione, interlinea=1.2):
    """Larghezza in pixel di un testo (anche multilinea o con formule)."""
    t = _FIG_MISURE.text(0, 0, testo, fontsize=dimensione, linespacing=interlinea)
    w = t.get_window_extent(renderer=_FIG_MISURE.canvas.get_renderer()).width
    t.remove()
    return w


# ---------------------------------------------------------------------------
# Logica combinatoria
# ---------------------------------------------------------------------------
def leggi_elementi(testo):
    """'A,B,C' -> ['A','B','C'];  'ABC' o 'A B C' -> ['A','B','C'].
    Con le virgole si possono usare elementi di piu' caratteri (es. 10,20,30)."""
    testo = testo.strip()
    if "," in testo:
        return [t.strip() for t in testo.split(",") if t.strip()]
    return [c for c in testo if not c.isspace()]


class Nodo:
    def __init__(self, seq, indici, livello):
        self.seq = seq          # elementi scelti finora
        self.indici = indici    # posizioni degli elementi scelti (se servono)
        self.livello = livello
        self.figli = []
        self.y = 0.0


def scelte_possibili(tipo, elementi, nodo, k):
    """Restituisce le coppie (indice, elemento) che si possono scegliere
    al passo successivo, a partire dal nodo dato."""
    n = len(elementi)
    if tipo == "dr":                        # tutto, sempre
        return list(enumerate(elementi))
    if tipo in ("ds", "ps"):                # solo elementi non ancora usati
        return [(i, e) for i, e in enumerate(elementi) if i not in nodo.indici]
    if tipo == "cs":                        # solo elementi successivi all'ultimo,
        inizio = nodo.indici[-1] + 1 if nodo.indici else 0   # lasciando spazio
        fine = n - (k - nodo.livello)                        # per i passi che mancano
        return [(i, elementi[i]) for i in range(inizio, fine + 1)]
    if tipo == "pr":                        # elementi distinti ancora disponibili
        rimasti = Counter(elementi) - Counter(nodo.seq)
        return [(None, e) for e in dict.fromkeys(elementi) if rimasti[e] > 0]
    raise ValueError(tipo)


def costruisci_albero(tipo, elementi, k):
    radice = Nodo([], (), 0)

    def espandi(nodo):
        if nodo.livello == k:
            return
        for i, e in scelte_possibili(tipo, elementi, nodo, k):
            figlio = Nodo(nodo.seq + [e], nodo.indici + (i,), nodo.livello + 1)
            nodo.figli.append(figlio)
            espandi(figlio)

    espandi(radice)
    return radice


def numero_sequenze(tipo, elementi, k):
    n = len(elementi)
    if tipo == "dr":
        return n ** k
    if tipo in ("ds", "ps"):
        return perm(n, k)
    if tipo == "cs":
        return comb(n, k)
    if tipo == "pr":
        return factorial(n) // prod(factorial(c) for c in Counter(elementi).values())
    raise ValueError(tipo)


def testata_passo(tipo, elementi, i, k, conteggio):
    """Formula (mathtext) da scrivere sopra la colonna del passo i."""
    n = len(elementi)
    if tipo == "dr":
        return rf"${n}^{{{i}}} = {conteggio}$"
    if tipo in ("ds", "ps"):
        if i == 1:
            return rf"${conteggio}$"
        fattori = r" \cdot ".join(str(n - j) for j in range(i))
        return rf"${fattori} = {conteggio}$"
    if tipo == "cs":
        if i < k:
            return f"{conteggio} nodi"
        return rf"$\dfrac{{{perm(n, k)}}}{{{k}!}} = {conteggio}$"
    if tipo == "pr":
        if i < k:
            return f"{conteggio} nodi"
        den = r" \cdot ".join(f"{c}!" for c in Counter(elementi).values())
        return rf"$\dfrac{{{n}!}}{{{den}}} = {conteggio}$"
    raise ValueError(tipo)


def spiegazione(tipo, elementi, k):
    """Testo del riquadro con la formula generale e quella sostituita."""
    n = len(elementi)
    tot = numero_sequenze(tipo, elementi, k)
    if tipo == "dr":
        return (f"D'(n, k) = nᵏ\nD'({n}, {k}) = {n}{apice(k)} = {tot}\n\n"
                f"A ogni passo si può scegliere di nuovo fra tutti gli {n} "
                f"elementi: ogni nodo ha sempre {n} rami e il numero di "
                f"sequenze si moltiplica per {n} a ogni passo.")
    if tipo == "ds":
        fattori = "·".join(str(n - j) for j in range(k))
        return (f"D(n, k) = n·(n−1)·…·(n−k+1)\nD({n}, {k}) = {fattori} = {tot}\n\n"
                "Un elemento già scelto non si può riusare: a ogni passo "
                "c'è un ramo in meno rispetto al passo precedente.")
    if tipo == "ps":
        return (f"P(n) = n!\nP({n}) = {n}! = {tot}\n\n"
                "È il caso particolare delle disposizioni semplici con k = n: "
                "si usano tutti gli elementi e conta solo l'ordine.")
    if tipo == "pr":
        conti = Counter(elementi)
        den = "·".join(f"{c}!" for c in conti.values())
        dettaglio = ", ".join(f"{e} ×{c}" for e, c in conti.items())
        return (f"P = n! / (k₁!·k₂!·…)\nP = {n}! / ({den}) = {tot}\n\n"
                f"Elementi: {dettaglio}.\n"
                f"Se gli elementi uguali fossero distinguibili ci sarebbero "
                f"{n}! = {factorial(n)} sequenze; scambiando tra loro gli "
                f"elementi uguali ogni sequenza compare {factorial(n) // tot} "
                f"volte, quindi si divide.")
    if tipo == "cs":
        return (f"C(n, k) = D(n, k) / k!\nC({n}, {k}) = {perm(n, k)} / {k}! = {tot}\n\n"
                "Scegliendo gli elementi sempre in ordine crescente ogni gruppo "
                "compare una volta sola. Ciascun gruppo corrisponde a "
                f"{k}! = {factorial(k)} disposizioni, cioè ai suoi riordinamenti.")
    raise ValueError(tipo)


# ---------------------------------------------------------------------------
# Disegno
# ---------------------------------------------------------------------------
def crea_figura(tipo, elementi, k, parole_complete=True,
                numera_foglie=True, mostra_passi=True):
    radice = costruisci_albero(tipo, elementi, k)

    # posizione verticale: foglie in ordine, genitore a meta' tra primo e ultimo figlio
    foglie = []
    conteggi = Counter()

    def posiziona(nodo):
        conteggi[nodo.livello] += 1
        if not nodo.figli:
            nodo.y = len(foglie)
            foglie.append(nodo)
        else:
            for f in nodo.figli:
                posiziona(f)
            nodo.y = (nodo.figli[0].y + nodo.figli[-1].y) / 2

    posiziona(radice)

    separatore = "" if all(len(e) == 1 for e in elementi) else ","

    def etichetta(nodo):
        return separatore.join(nodo.seq) if parole_complete else nodo.seq[-1]

    testate = ([f"{i}° passo\n" + testata_passo(tipo, elementi, i, k, conteggi[i])
                for i in range(1, k + 1)] if mostra_passi else [])

    # la colonna deve contenere sia le parole dei nodi sia l'intestazione più larga
    w_etichetta = max(larghezza_testo(etichetta(f), 11) for f in foglie)
    w_testata = max((larghezza_testo(t, 10, 1.6) for t in testate), default=0)
    col = max(90, w_etichetta + 50, w_testata + 30)
    larghezza = 2 * MARGINE + k * col + max(w_etichetta / 2 + 60, w_testata / 2)
    altezza = SPAZIO_TESTATA + (len(foglie) - 1) * PASSO_Y + 2 * MARGINE

    fig = Figure(figsize=(larghezza / DPI, altezza / DPI), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, larghezza)
    ax.set_ylim(altezza, 0)
    ax.axis("off")

    def px(nodo):
        return MARGINE + nodo.livello * col

    def py(nodo):
        return SPAZIO_TESTATA + MARGINE / 2 + nodo.y * PASSO_Y

    def visita(nodo):
        for f in nodo.figli:
            ax.plot([px(nodo), px(f)], [py(nodo), py(f)],
                    color=COLORE_RAMI, lw=1, zorder=1)
            visita(f)
        if nodo.livello == 0:
            ax.plot(px(nodo), py(nodo), "o", color=COLORE_TESTO, ms=6, zorder=3)
        else:
            ax.text(px(nodo), py(nodo), etichetta(nodo), ha="center", va="center",
                    fontsize=11, color=COLORE_TESTO, zorder=2,
                    bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none"))

    visita(radice)

    if numera_foglie:
        for j, f in enumerate(foglie, start=1):
            ax.text(px(f) + w_etichetta / 2 + 12, py(f), f"({j})",
                    ha="left", va="center", fontsize=9, color=COLORE_CONTATORE)

    for i, testo in enumerate(testate, start=1):
        ax.text(MARGINE + i * col, SPAZIO_TESTATA - 8, testo,
                ha="center", va="bottom", fontsize=10,
                color=COLORE_PASSI, linespacing=1.6)

    return fig, larghezza, altezza


# ---------------------------------------------------------------------------
# Interfaccia
# ---------------------------------------------------------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Calcolo combinatorio – diagrammi ad albero")
        self.geometry("1250x780")
        self.minsize(900, 550)

        self.fig = None
        self.fig_canvas = None

        self.var_tipo = tk.StringVar(value="Disposizioni con ripetizione")
        self.var_el = tk.StringVar(value="A,B,C")
        self.var_k = tk.IntVar(value=3)
        self.var_parole = tk.BooleanVar(value=True)
        self.var_numeri = tk.BooleanVar(value=True)
        self.var_passi = tk.BooleanVar(value=True)

        self._costruisci_controlli()
        self._costruisci_area_disegno()
        self._aggiorna_stato_k()
        self.genera()

    # --- pannello di sinistra -------------------------------------------
    def _costruisci_controlli(self):
        pannello = ttk.Frame(self, padding=14)
        pannello.pack(side="left", fill="y")

        ttk.Label(pannello, text="Tipologia").pack(anchor="w")
        cb = ttk.Combobox(pannello, textvariable=self.var_tipo, values=list(TIPI),
                          state="readonly", width=30)
        cb.pack(anchor="w", pady=(2, 12))
        cb.bind("<<ComboboxSelected>>", lambda e: (self._aggiorna_stato_k(), self.genera()))

        ttk.Label(pannello, text="Elementi (es. A,B,C  oppure  ABC)").pack(anchor="w")
        voce = ttk.Entry(pannello, textvariable=self.var_el, width=32)
        voce.pack(anchor="w", pady=(2, 12))
        voce.bind("<Return>", lambda e: self.genera())

        ttk.Label(pannello, text="Lunghezza k").pack(anchor="w")
        self.spin_k = ttk.Spinbox(pannello, from_=1, to=10, textvariable=self.var_k,
                                  width=6, command=self.genera)
        self.spin_k.pack(anchor="w", pady=(2, 12))
        self.spin_k.bind("<Return>", lambda e: self.genera())

        for testo, var in (("Parole complete nei nodi", self.var_parole),
                           ("Numera le foglie", self.var_numeri),
                           ("Mostra i passi", self.var_passi)):
            ttk.Checkbutton(pannello, text=testo, variable=var,
                            command=self.genera).pack(anchor="w")

        pulsanti = ttk.Frame(pannello)
        pulsanti.pack(anchor="w", pady=14)
        ttk.Button(pulsanti, text="Disegna", command=self.genera).pack(side="left")
        ttk.Button(pulsanti, text="Salva immagine…",
                   command=self.salva).pack(side="left", padx=6)

        ttk.Separator(pannello).pack(fill="x", pady=6)
        self.lbl_formula = ttk.Label(pannello, text="", wraplength=290,
                                     justify="left", font=("TkDefaultFont", 11))
        self.lbl_formula.pack(anchor="w", pady=6)

    # --- area scorrevole di destra ---------------------------------------
    def _costruisci_area_disegno(self):
        cornice = ttk.Frame(self)
        cornice.pack(side="right", fill="both", expand=True)
        cornice.rowconfigure(0, weight=1)
        cornice.columnconfigure(0, weight=1)

        self.area = tk.Canvas(cornice, background="white", highlightthickness=0)
        sy = ttk.Scrollbar(cornice, orient="vertical", command=self.area.yview)
        sx = ttk.Scrollbar(cornice, orient="horizontal", command=self.area.xview)
        self.area.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        self.area.grid(row=0, column=0, sticky="nsew")
        sy.grid(row=0, column=1, sticky="ns")
        sx.grid(row=1, column=0, sticky="ew")

        # rotellina: verticale; Shift+rotellina: orizzontale
        self.bind_all("<MouseWheel>", lambda e: self._scorri(e, False))
        self.bind_all("<Shift-MouseWheel>", lambda e: self._scorri(e, True))
        for tasto in ("<Button-4>", "<Button-5>"):                    # Linux (X11)
            self.bind_all(tasto, lambda e: self._scorri(e, False))
            self.bind_all("<Shift-" + tasto[1:], lambda e: self._scorri(e, True))

    def _scorri(self, evento, orizzontale):
        if evento.num == 4:                 # Linux, rotellina in su
            passi = -1
        elif evento.num == 5:               # Linux, rotellina in giù
            passi = 1
        elif sys.platform == "darwin":      # macOS: delta piccoli (±1, ±2, ...)
            passi = -evento.delta
        else:                               # Windows: delta multipli di 120
            passi = int(-evento.delta / 120)
        if passi:
            vista = self.area.xview_scroll if orizzontale else self.area.yview_scroll
            vista(passi, "units")

    def _aggiorna_stato_k(self):
        tipo = TIPI[self.var_tipo.get()]
        self.spin_k.configure(state="disabled" if tipo in ("ps", "pr") else "normal")

    def _pulisci_area(self):
        if self.fig_canvas is not None:
            self.fig_canvas.get_tk_widget().destroy()
            self.fig_canvas = None
        self.area.delete("all")

    def _messaggio(self, testo):
        self._pulisci_area()
        self.fig = None
        self.area.create_text(30, 30, text=testo, anchor="nw",
                              font=("TkDefaultFont", 12), fill="#374151")
        self.area.configure(scrollregion=(0, 0, 800, 200))

    # --- azioni ------------------------------------------------------------
    def genera(self):
        tipo = TIPI[self.var_tipo.get()]
        elementi = leggi_elementi(self.var_el.get())

        if not elementi:
            self.lbl_formula.configure(text="")
            self._messaggio("Inserisci almeno un elemento.")
            return
        if tipo != "pr" and len(set(elementi)) != len(elementi):
            self.lbl_formula.configure(text="")
            self._messaggio("Per questa tipologia gli elementi devono essere distinti.\n"
                            "Con elementi ripetuti usa le permutazioni con ripetizione.")
            return

        n = len(elementi)
        if tipo in ("ps", "pr"):
            k = n
            self.var_k.set(k)
        else:
            try:
                k = int(self.spin_k.get())
            except ValueError:
                self._messaggio("La lunghezza k deve essere un numero intero.")
                return
            if k < 1:
                self._messaggio("La lunghezza k deve essere almeno 1.")
                return
            if tipo in ("ds", "cs") and k > n:
                self.lbl_formula.configure(text="")
                self._messaggio(f"Con {n} elementi distinti senza ripetizione "
                                f"k non può superare {n}.")
                return

        self.lbl_formula.configure(text=spiegazione(tipo, elementi, k))

        totale = numero_sequenze(tipo, elementi, k)
        if totale > MAX_FOGLIE:
            self._messaggio(f"L'albero avrebbe {totale} foglie: troppe per essere "
                            f"disegnato in modo leggibile (limite {MAX_FOGLIE}).\n"
                            "La formula a sinistra resta valida.")
            return

        self.fig, larghezza, altezza = crea_figura(
            tipo, elementi, k,
            parole_complete=self.var_parole.get(),
            numera_foglie=self.var_numeri.get(),
            mostra_passi=self.var_passi.get())

        self._pulisci_area()
        self.fig_canvas = FigureCanvasTkAgg(self.fig, master=self.area)
        self.fig_canvas.draw()
        self.area.create_window(0, 0, window=self.fig_canvas.get_tk_widget(), anchor="nw")
        self.area.configure(scrollregion=(0, 0, larghezza, altezza))
        self.area.xview_moveto(0)
        self.area.yview_moveto(0)

    def salva(self):
        if self.fig is None:
            messagebox.showinfo("Salva immagine", "Non c'è nessun albero da salvare.")
            return
        percorso = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf"), ("PNG", "*.png"), ("SVG", "*.svg")])
        if not percorso:
            return
        try:
            self.fig.savefig(percorso, bbox_inches="tight", dpi=200)
        except Exception as errore:
            messagebox.showerror("Salva immagine",
                                 f"Impossibile salvare il file:\n{errore}")
        else:
            messagebox.showinfo("Salva immagine", f"File salvato:\n{percorso}")


if __name__ == "__main__":
    App().mainloop()
