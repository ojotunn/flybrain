# Sentidos dela lidos DIRETO DA CHAIN: cada compra e venda na curva de um token (o dela, no lancamento) vira
# estimulo em segundos, sem esperar o indexador (a GeckoTerminal atrasa minutos). Le os logs da curva por
# eth_getLogs a cada poucos segundos e classifica pela transacao: buy(quoteIn,minOut,to) leva o ETH em value;
# sell(tokensIn,minOut,to) traz a quantidade no primeiro argumento. Conferido em 07/09: a interface da Pons chama
# a curva direto (to = curva), seletores 0x59a87bc1 (buy) e 0xd04c6983 (sell); bloco de 0,1 s.
import time
from collections import deque

from web3 import Web3


def _seletor(assinatura):
    h = Web3.keccak(text=assinatura)[:4].hex()
    return '0x' + h[2:] if h.startswith('0x') else '0x' + h


SEL_BUY = _seletor('buy(uint256,uint256,address)')
SEL_SELL = _seletor('sell(uint256,uint256,address)')


class SentidosChain:
    def __init__(self, chain, token):
        self.chain = chain
        lanc = chain.lancamento(token)
        if not lanc['exists']:
            raise RuntimeError('token nao e um lancamento da Pons V2')
        self.token, self.curva = lanc['token'], lanc['curva']
        erc = chain.erc20(self.token)
        try:
            self.nome = str(erc.functions.symbol().call())
        except Exception:
            self.nome = self.token[:8]
        try:
            self.decimais = int(erc.functions.decimals().call())
        except Exception:
            self.decimais = 18
        self.bloco = int(chain.w3.eth.block_number)     # comeca de agora: sem historico velho
        self.preco_eth = 0.0
        self.historico = deque(maxlen=600)
        self.vistos = set()
        self.erro = ''
        self.lidos = 0
        self._preco()

    def _preco(self):
        try:
            R, T = self.chain.curva(self.curva).functions.getReserves().call()
            self.preco_eth = (R / T) if T else 0.0
        except Exception as e:
            self.erro = str(e)[:80]

    def ler(self, eth_usd):
        """Trades novos desde a ultima leitura, no formato dos trades da GeckoTerminal (+ fonte='chain')."""
        w3 = self.chain.w3
        try:
            atual = int(w3.eth.block_number)
            if atual <= self.bloco:
                return []
            logs = w3.eth.get_logs({'address': self.curva, 'fromBlock': self.bloco + 1, 'toBlock': atual})
            self.bloco = atual
            self.erro = ''
        except Exception as e:
            self.erro = str(e)[:80]
            return []
        hashes = list(dict.fromkeys(Web3.to_hex(l['transactionHash']) for l in logs))
        if hashes:
            self._preco()
        novos = []
        for h in hashes:
            if h in self.vistos:
                continue
            self.vistos.add(h)
            try:
                tx = w3.eth.get_transaction(h)
            except Exception:
                continue
            dados = Web3.to_hex(tx['input']).lower()
            sel = dados[:10]
            quando = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            if sel == SEL_BUY or int(tx['value']) > 0:
                kind, usd = 'buy', int(tx['value']) / 1e18 * eth_usd
            elif sel == SEL_SELL and len(dados) >= 74:
                kind, usd = 'sell', int(dados[10:74], 16) / 10 ** self.decimais * self.preco_eth * eth_usd
            else:
                continue                                    # outra chamada na curva (aprovacao, admin): nao e trade
            t = {'tx': h, 'kind': kind, 'usd': float(usd), 'de': str(tx['from']), 'quando': quando,
                 'preco_usd': self.preco_eth * eth_usd, 'fonte': 'chain'}
            novos.append(t)
            self.historico.append(t)
            self.lidos += 1
        if len(self.vistos) > 5000:
            self.vistos = set(t['tx'] for t in self.historico)
        return novos
