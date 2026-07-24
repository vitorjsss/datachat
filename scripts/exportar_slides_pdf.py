"""
DataChat NoSQL — Exporta docs/slides_semana2.html para PDF.

Abre o deck num Chromium headless (Playwright), navega slide a slide com a
mesma seta ArrowRight que a apresentação usa no navegador, tira um
screenshot de cada um e junta tudo num PDF — um slide por página, na ordem
exata da apresentação.

Não usa "imprimir para PDF": captura o slide exatamente como ele aparece
na tela (mesmo layout, mesmas fontes), em vez de depender do reflow do
media query de impressão.

Requer:
    pip install playwright pillow
    playwright install chromium

Uso:
    python scripts/exportar_slides_pdf.py
"""

import pathlib

from PIL import Image
from playwright.sync_api import sync_playwright

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SLIDES_HTML = RAIZ / "docs" / "slides_semana2.html"
SAIDA_PDF = RAIZ / "docs" / "slides_semana2.pdf"
PASTA_TEMP = RAIZ / "docs" / "_slides_png_tmp"

LARGURA, ALTURA = 1920, 1080  # 16:9, resolução comum de projetor
ESPERA_TRANSICAO_MS = 450     # a transição de opacidade do deck é de 320ms


def exportar():
    if not SLIDES_HTML.exists():
        raise SystemExit(f"Não encontrei {SLIDES_HTML}")

    PASTA_TEMP.mkdir(exist_ok=True)
    caminhos_png = []

    with sync_playwright() as p:
        navegador = p.chromium.launch()
        pagina = navegador.new_page(viewport={"width": LARGURA, "height": ALTURA})
        pagina.goto(SLIDES_HTML.as_uri())
        pagina.wait_for_selector(".slide.is-active")
        # Some os controles de navegação (setas, contador, barra de progresso) —
        # fazem sentido ao vivo no navegador, não num PDF estático.
        pagina.add_style_tag(content=".nav-chrome, .progress, .slide-idx { display: none !important; }")

        total = int(pagina.locator("#counterTotal").inner_text())
        print(f"Capturando {total} slides de {SLIDES_HTML.name}...")

        for i in range(1, total + 1):
            pagina.wait_for_timeout(ESPERA_TRANSICAO_MS)
            caminho = PASTA_TEMP / f"slide_{i:02d}.png"
            pagina.screenshot(path=str(caminho))
            caminhos_png.append(caminho)
            print(f"  slide {i}/{total} capturado")
            if i < total:
                pagina.keyboard.press("ArrowRight")

        navegador.close()

    print("Montando o PDF...")
    imagens = [Image.open(c).convert("RGB") for c in caminhos_png]
    imagens[0].save(SAIDA_PDF, save_all=True, append_images=imagens[1:])

    for c in caminhos_png:
        c.unlink()
    PASTA_TEMP.rmdir()

    print(f"PDF gerado em: {SAIDA_PDF}  ({total} páginas)")


if __name__ == "__main__":
    exportar()
