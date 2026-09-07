# Imagem de compartilhamento (og:image, 1200x630) para o link do site aparecer com cara no X e no Telegram:
# a nuvem real dos 138 mil neuronios (site/neurons.bin, cores por regiao) sobre fundo preto, com a marca.
#   py\Scripts\python.exe brain\gerar_og.py  ->  site/og.png
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
SITE = RAIZ / 'site'
W, H = 1200, 630


def fonte(tamanho, negrito=False):
    for nome in (('consolab.ttf' if negrito else 'consola.ttf'), 'cour.ttf', 'arial.ttf'):
        p = Path('C:/Windows/Fonts') / nome
        if p.exists():
            return ImageFont.truetype(str(p), tamanho)
    return ImageFont.load_default()


def main():
    xyz = np.frombuffer((SITE / 'neurons.bin').read_bytes(), dtype='<f4').reshape(-1, 3)
    reg = np.frombuffer((SITE / 'regions.bin').read_bytes(), dtype=np.uint8)
    rj = json.loads((SITE / 'regions.json').read_text())
    cores = np.array([[int(r['color'][1:3], 16), int(r['color'][3:5], 16), int(r['color'][5:7], 16)] for r in rj['regions']], dtype=np.float32) / 255.0
    desconhecido = len(rj['regions']) - 1
    ok = reg != desconhecido
    xyz, reg = xyz[ok], reg[ok]
    # vista de frente: x na horizontal, -y na vertical; enquadra no lado direito da imagem
    x, y = xyz[:, 0], -xyz[:, 1]
    x = (x - x.min()) / np.ptp(x)
    y = (y - y.min()) / np.ptp(y)
    larg, alt = 640, 420
    px = (x * larg + 500).astype(int)
    py = (y * alt + 105).astype(int)
    img = np.zeros((H, W, 3), dtype=np.float32)
    c = cores[reg]
    np.add.at(img, (py, px), c * 0.55)
    # alguns neuronios "acesos": pontos mais fortes e brancos, como na tela
    rng = np.random.default_rng(3)
    acesos = rng.choice(len(px), 900, replace=False)
    np.add.at(img, (py[acesos], px[acesos]), np.ones((900, 3), dtype=np.float32) * 1.4)
    base = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
    brilho = base.filter(ImageFilter.GaussianBlur(2.2))
    base = Image.blend(base, brilho, 0.55)
    forte = base.filter(ImageFilter.GaussianBlur(0.6))
    out = Image.fromarray(np.clip(np.asarray(base, dtype=np.float32) * 1.15 + np.asarray(forte, dtype=np.float32) * 0.5, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(out)
    d.text((72, 150), 'FLY', font=fonte(112, True), fill=(255, 255, 255))
    d.text((76, 290), 'a whole fly brain, alive', font=fonte(34), fill=(217, 220, 227))
    d.text((76, 332), 'on Robinhood Chain', font=fonte(34), fill=(217, 220, 227))
    d.text((76, 400), '138,639 real neurons, simulated live.', font=fonte(21), fill=(122, 128, 144))
    d.text((76, 430), 'Pons trades are her senses.', font=fonte(21), fill=(122, 128, 144))
    d.text((76, 460), 'Her reflexes place the orders.', font=fonte(21), fill=(122, 128, 144))
    d.text((76, 520), 'flybrain.finance', font=fonte(24, True), fill=(244, 211, 106))
    d.line([(72, 575), (1128, 575)], fill=(30, 33, 40), width=1)
    d.text((76, 586), 'no AI agent  ·  no script  ·  her own wallet  ·  never her own token', font=fonte(18), fill=(74, 79, 90))
    out.save(SITE / 'og.png', optimize=True)
    print(f'ok: {SITE / "og.png"} {(SITE / "og.png").stat().st_size / 1e3:.0f} KB, {len(px):,} neuronios desenhados')


if __name__ == '__main__':
    main()
