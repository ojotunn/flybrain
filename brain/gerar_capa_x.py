# Capa do X (1500x500 e 3000x1000) com a nuvem REAL dos 138 mil neuronios (site/neurons.bin) e a marca.
# Variante "real" (dados do site); a variante ilustrada vem do Gemini (brand/capa-x-gemini-raw.png + texto aqui).
#   py\Scripts\python.exe brain\gerar_capa_x.py            -> brand/capa-x-real-1500x500.png (+ 3000x1000)
#   py\Scripts\python.exe brain\gerar_capa_x.py <arte.png>  -> brand/capa-x-<nome>-1500x500.png: a arte inteira
#                                                             encostada a direita num quadro 3:1, texto a esquerda
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
SITE = RAIZ / 'site'
BRAND = RAIZ / 'brand'
W, H = 3000, 1000          # 2x; a versao 1500x500 e reduzida no fim


def fonte(tamanho, negrito=False):
    for nome in (('consolab.ttf' if negrito else 'consola.ttf'), 'cour.ttf', 'arial.ttf'):
        p = Path('C:/Windows/Fonts') / nome
        if p.exists():
            return ImageFont.truetype(str(p), tamanho)
    return ImageFont.load_default()


def nuvem(larg, alt, x0, y0):
    """Nuvem real dos neuronios (vista de frente) numa imagem preta W x H."""
    xyz = np.frombuffer((SITE / 'neurons.bin').read_bytes(), dtype='<f4').reshape(-1, 3)
    reg = np.frombuffer((SITE / 'regions.bin').read_bytes(), dtype=np.uint8)
    rj = json.loads((SITE / 'regions.json').read_text())
    cores = np.array([[int(r['color'][1:3], 16), int(r['color'][3:5], 16), int(r['color'][5:7], 16)] for r in rj['regions']], dtype=np.float32) / 255.0
    ok = reg != len(rj['regions']) - 1
    xyz, reg = xyz[ok], reg[ok]
    x, y = xyz[:, 0], -xyz[:, 1]
    x = (x - x.min()) / np.ptp(x)
    y = (y - y.min()) / np.ptp(y)
    px = (x * larg + x0).astype(int)
    py = (y * alt + y0).astype(int)
    img = np.zeros((H, W, 3), dtype=np.float32)
    np.add.at(img, (py, px), cores[reg] * 0.5)
    rng = np.random.default_rng(5)
    acesos = rng.choice(len(px), 1400, replace=False)
    np.add.at(img, (py[acesos], px[acesos]), np.ones((1400, 3), dtype=np.float32) * 1.4)
    base = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
    brilho = base.filter(ImageFilter.GaussianBlur(4))
    base = Image.blend(base, brilho, 0.55)
    forte = base.filter(ImageFilter.GaussianBlur(1.2))
    return Image.fromarray(np.clip(np.asarray(base, dtype=np.float32) * 1.15 + np.asarray(forte, dtype=np.float32) * 0.5, 0, 255).astype(np.uint8))


def texto(img):
    """Bloco de texto estreito (ate ~900 px) na esquerda, para nao encostar na mosca da arte."""
    d = ImageDraw.Draw(img)
    d.text((150, 200), 'FLY', font=fonte(190, True), fill=(255, 255, 255))
    d.text((158, 430), 'a whole fly brain,', font=fonte(50), fill=(217, 220, 227))
    d.text((158, 490), 'alive on Robinhood Chain', font=fonte(50), fill=(217, 220, 227))
    d.text((158, 590), '138,639 real neurons, simulated live.', font=fonte(30), fill=(140, 146, 160))
    d.text((158, 632), 'Pons trades are her senses.', font=fonte(30), fill=(140, 146, 160))
    d.text((158, 674), 'Her reflexes place the orders.', font=fonte(30), fill=(140, 146, 160))
    d.text((158, 716), 'No AI agent. No script.', font=fonte(30), fill=(140, 146, 160))
    d.text((158, 820), 'flybrain.finance', font=fonte(44, True), fill=(244, 211, 106))
    d.text((158, 880), '@RobinhoodFLY', font=fonte(32), fill=(120, 126, 140))
    return img


def salvar(img, nome):
    BRAND.mkdir(exist_ok=True)
    img.save(BRAND / f'{nome}-3000x1000.png', optimize=True)
    img.resize((1500, 500), Image.LANCZOS).save(BRAND / f'{nome}-1500x500.png', optimize=True)
    print('->', BRAND / f'{nome}-1500x500.png')


def main():
    if len(sys.argv) > 1:
        arte = Image.open(sys.argv[1]).convert('RGB')
        aw, ah = arte.size
        # quadro 3:1 com a arte inteira encostada a direita; o que sobra a esquerda e preto (zona do texto)
        if aw / ah < 3:
            quadro = Image.new('RGB', (ah * 3, ah), (0, 0, 0))
            quadro.paste(arte, (ah * 3 - aw, 0))
            # emenda suave entre o preto e a borda esquerda da arte
            faixa = 220
            for i in range(faixa):
                x = ah * 3 - aw + i
                col = quadro.crop((x, 0, x + 1, ah))
                quadro.paste(Image.blend(Image.new('RGB', (1, ah), (0, 0, 0)), col, i / faixa), (x, 0))
        else:
            nw = int(ah * 3)
            quadro = arte.crop((aw - nw, 0, aw, ah))
        img = quadro.resize((W, H), Image.LANCZOS)
        nome = Path(sys.argv[1]).stem.replace('-raw', '').replace('capa-x-', '')
        salvar(texto(img), 'capa-x-' + nome)
    else:
        img = nuvem(1500, 900, 1350, 50)
        salvar(texto(img), 'capa-x-real')


if __name__ == '__main__':
    main()
