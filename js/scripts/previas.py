"""Prévias para conferir o player a olho: a folha do Python e a mesma folha desenhada pelo JavaScript no Chrome, lado a
lado, nos pacotes classico, vivo e 3d (com volume), mais um retrato da página de demonstração.

  python js/scripts/previas.py --saida PASTA [--chrome caminho\\chrome.exe] [--t 1.2] [--escala 2]

Sobe um servidor estático temporário só em 127.0.0.1 (porta livre escolhida pelo sistema; módulos ES não carregam de
file://), tira os retratos com o Chrome sem janela (perfil temporário dentro de PASTA, apagado no fim) e desliga o
servidor. Só biblioteca padrão e Pillow (que o pacote Python já usa).
"""
from __future__ import annotations

import argparse
import functools
import shutil
import subprocess
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parents[2]
CHROMES = [Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
           Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
           Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"), Path("/usr/bin/google-chrome")]
PORTAS_PROIBIDAS = {5180, 5210, 5211}
# nome, argumentos da folha do Python, parâmetros da folha.html, título
CASOS = [
    ("classico", ["--pacote", "classico", "--chapado"], "pacote=classico&volume=0", "classico"),
    ("vivo", ["--pacote", "vivo", "--chapado"], "pacote=vivo&volume=0", "vivo"),
    ("3d_volume", ["--pacote", "3d"], "pacote=3d&volume=1", "3d com volume"),
    # sem acentos nos títulos: a fonte padrão do Pillow, a das faixas, não tem todos
    ("terminal", ["--pacote", "terminal"], "pacote=terminal", "terminal (tinta ascii, fosforo verde)"),
    ("terminal_blocos_ambar", ["--pacote", "terminal", "--tinta", "blocos", "--fosforo", "ambar"],
     "pacote=terminal&tinta=blocos&fosforo=ambar", "terminal (tinta blocos, fosforo ambar)"),
]


class Silencioso(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def servidor() -> ThreadingHTTPServer:
    while True:
        srv = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Silencioso, directory=str(RAIZ)))
        if srv.server_address[1] not in PORTAS_PROIBIDAS:
            return srv
        srv.server_close()


def retrato(chrome: Path, url: str, destino: Path, largura: int, altura: int, perfil: Path, escala: float = 1) -> None:
    subprocess.run([str(chrome), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                    "--no-default-browser-check", f"--user-data-dir={perfil}", f"--window-size={largura},{altura}",
                    f"--force-device-scale-factor={escala}", "--virtual-time-budget=4000", f"--screenshot={destino}", url],
                   check=True, capture_output=True, timeout=120)
    if not destino.exists():
        raise RuntimeError(f"o Chrome não gravou {destino}")


def lado_a_lado(py: Path, js: Path, destino: Path, titulo: str) -> None:
    a, b = Image.open(py).convert("RGB"), Image.open(js).convert("RGB")
    faixa = 44
    w = max(a.width, b.width)
    img = Image.new("RGB", (w, a.height + b.height + 2 * faixa), (18, 17, 16))
    d = ImageDraw.Draw(img)
    fonte = ImageFont.load_default(22)
    d.text((14, faixa // 2), f"{titulo} · Python (Pillow, python -m mascotinhos folha)", font=fonte, fill=(229, 229, 229), anchor="lm")
    img.paste(a, (0, faixa))
    y = faixa + a.height
    d.line((0, y, w, y), fill=(224, 122, 87), width=2)
    d.text((14, y + faixa // 2), f"{titulo} · JavaScript (SVG no Chrome, js/demo/folha.html)", font=fonte, fill=(229, 229, 229), anchor="lm")
    img.paste(b, (0, y + faixa))
    img.save(destino)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--saida", required=True, type=Path)
    ap.add_argument("--chrome", type=Path)
    ap.add_argument("--t", type=float, default=1.2)
    ap.add_argument("--escala", type=int, default=2)
    args = ap.parse_args()
    chrome = args.chrome or next((c for c in CHROMES if c.exists()), None)
    if not chrome or not chrome.exists():
        print("não achei o Chrome: passe --chrome", file=sys.stderr)
        return 2
    saida = args.saida.resolve()
    saida.mkdir(parents=True, exist_ok=True)
    perfil = saida / "_perfil_chrome"
    e = args.escala
    largura, altura = (12 + 90 + 6 * 156 + 12) * e, (26 + 3 * 170 + 12) * e
    srv = servidor()
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}/js/demo"
    try:
        for nome, argumentos, consulta, titulo in CASOS:
            py, js = saida / f"folha_python_{nome}.png", saida / f"folha_js_{nome}.png"
            cmd = [sys.executable, "-m", "mascotinhos", "folha", *argumentos, "--t", str(args.t), "--escala", str(e), "-o", str(py)]
            subprocess.run(cmd, cwd=RAIZ, check=True, capture_output=True)
            retrato(chrome, f"{base}/folha.html?{consulta}&t={args.t}&escala={e}", js, largura, altura, perfil)
            lado_a_lado(py, js, saida / f"comparacao_{nome}.png", f"{titulo}, t = {args.t:g} s")
            print(f"ok  {nome}: {py.name}, {js.name}, comparacao_{nome}.png")
        retrato(chrome, f"{base}/index.html?pacote=vivo", saida / "demo_vivo.png", 1280, 1900, perfil)
        retrato(chrome, f"{base}/index.html?pacote=3d&volume=1", saida / "demo_3d_volume.png", 1280, 1900, perfil)
        retrato(chrome, f"{base}/index.html?pacote=terminal&limite=87", saida / "demo_terminal.png", 1280, 1900, perfil)
        print("ok  demo_vivo.png, demo_3d_volume.png, demo_terminal.png")
    finally:
        srv.shutdown()
        srv.server_close()
        shutil.rmtree(perfil, ignore_errors=True)
    print(f"prévias em {saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
