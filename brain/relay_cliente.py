# Liga o servidor local (o PC com a placa) ao relay publico (relay/servidor.py, no Railway): manda para la o
# ultimo quadro do cerebro, o ultimo quadro do corpo e os eventos do mercado; recebe de la quantos assistem.
# Quadros binarios nao enfileiram: se a internet atrasar, o mais novo substitui o anterior (sem lag acumulado).
import asyncio
import json
from collections import deque

import aiohttp


class Uplink:
    def __init__(self, url, token, ola_fn, snapshot_fn):
        self.url = url
        self.token = token
        self.ola_fn = ola_fn            # -> dict da mensagem 'ola' (o que a pagina recebe ao conectar)
        self.snapshot_fn = snapshot_fn  # -> lista de str/bytes com o estado atual (resumo, eventos, corpo)
        self.bin = {}                   # tipo -> (seq, bytes): so o mais recente de cada tipo
        self.enviado = {}
        self.textos = deque(maxlen=300)
        self.evento = asyncio.Event()
        self.ligado = False
        self.viewers = 0
        self.seq = 0
        self.enviados = 0
        self.erro = ''

    def push_bin(self, tipo, dados):
        self.seq += 1
        self.bin[tipo] = (self.seq, dados)
        self.evento.set()

    def push_txt(self, s):
        self.textos.append(s)
        self.evento.set()

    async def _ler(self, ws):
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    m = json.loads(msg.data)
                except Exception:
                    continue
                if 'viewers' in m:
                    self.viewers = int(m['viewers'])

    async def rodar(self):
        espera = 1
        while True:
            try:
                async with aiohttp.ClientSession() as sess:
                    async with sess.ws_connect(self.url, params={'token': self.token}, heartbeat=20,
                                               max_msg_size=16 * 1024 * 1024) as ws:
                        self.ligado, espera, self.erro = True, 1, ''
                        print(f'[relay] ligado a {self.url}', flush=True)
                        await ws.send_str(json.dumps(self.ola_fn(), separators=(',', ':')))
                        for item in self.snapshot_fn():
                            if isinstance(item, (bytes, bytearray)):
                                await ws.send_bytes(item)
                            else:
                                await ws.send_str(item)
                        leitor = asyncio.create_task(self._ler(ws))
                        try:
                            while not ws.closed:
                                try:
                                    await asyncio.wait_for(self.evento.wait(), timeout=5)
                                except asyncio.TimeoutError:
                                    pass
                                self.evento.clear()
                                for tipo, (seq, dados) in list(self.bin.items()):
                                    if self.enviado.get(tipo) != seq:
                                        await ws.send_bytes(dados)
                                        self.enviado[tipo] = seq
                                        self.enviados += 1
                                while self.textos:
                                    await ws.send_str(self.textos.popleft())
                        finally:
                            leitor.cancel()
            except Exception as e:
                self.erro = str(e)[:100]
                print(f'[relay] caiu: {self.erro}; tentando em {espera} s', flush=True)
            self.ligado = False
            self.viewers = 0
            await asyncio.sleep(espera)
            espera = min(espera * 2, 30)
