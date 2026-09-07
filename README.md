# fly — um cérebro de mosca inteiro, vivo, na tela

Simulação do conectoma completo da *Drosophila* (138.639 neurônios, 15 milhões de sinapses)
rodando na GPU e desenhada ao vivo no navegador. Cada neurônio que dispara acende na posição real.
As compras e vendas do token vão entrar como estímulos sensoriais (açúcar, amargo, sombra, vibração, odor)
e os neurônios descendentes dizem o que ela quer fazer (comer, andar, virar, recuar, fugir, se limpar).

## Rodar

1. `START-Windows.bat` (usa o venv `py\`, que reaproveita o torch ROCm do Atelier). Abre duas janelas:
   o corpo 3D e o cérebro com o servidor. O corpo fica tentando conectar até o cérebro subir.
2. Abrir http://localhost:8435. O cérebro leva uns 10 s para carregar; o corpo, uns 20 s.
3. Ctrl+C na janela do cérebro encerra e salva as sinapses e a "vida" em `brain/data/estado/`. Fechar a
   janela do corpo encerra a física (não tem estado para salvar).

Variáveis: `FLY_PORT` (8435), `FLY_AMBIENTE_HZ` (0), `FLY_PLASTICIDADE` (1), `FLY_MAX_IDX` (4000 índices por quadro).

## O que a dinâmica medida impõe (06/09/2026)

- **Sem entrada o modelo é mudo** (0 disparos). Não há atividade espontânea. A tela só acende com estímulo,
  então o show depende de estímulos frequentes vindos de eventos reais.
- **Ruído difuso prende a rede.** Qualquer taxa de fundo nos 16 mil neurônios sensoriais, até 0,05 Hz, leva a rede
  a um estado de ~8 mil neurônios a ~58 Hz (467 mil disparos/s) que se sustenta sem entrada. Nesse estado os
  reflexos morrem (fuga 85 Hz → 0). Por isso `FLY_AMBIENTE_HZ` é 0.
- **Estímulos específicos são seguros:** açúcar 8–10 mil disparos/s (probóscide 53–64 Hz, até 2 s), amargo 6 mil,
  sombra LC4 21 mil (fuga 85–93 Hz), vibração JO 32 mil (limpeza 8–11 Hz), P9 (andar 39 Hz). Combinados também.
  **Odor Or56a prende a rede** e está bloqueado (`ESTIMULOS_BLOQUEADOS`).
- **Detector de crise:** acima de 100 mil disparos/s por 200 ms de cérebro sem estímulo ativo, o motor reinicia
  a membrana (as sinapses ficam), conta a crise e registra em `/api/eventos`. A tela mostra "blackouts since birth".

Se mudar os dados, rodar `py\Scripts\python.exe brain\preparar_dados.py` antes de subir.

## Estrutura

- `brain/vendor/` — modelo LIF (Shiu et al. 2024) e listas de neurônios, copiados do repositório fly-brain (MIT).
- `brain/motor.py` — o cérebro: thread na GPU, estímulos com validade, plasticidade, quadros numa fila.
- `brain/servidor.py` — aiohttp: site estático, WebSocket `/ws`, `/api/estado`, `/api/estimulo`, `/api/eventos`.
- `brain/preparar_dados.py` — gera `site/neurons.bin`, `site/regions.bin`, `site/regions.json` e `brain/data/neuronios.parquet`.
- `site/index.html` — a tela (en-US): cérebro em 3D (three.js 0.158 do cdnjs), barras motoras, botões de estímulo,
  slider de velocidade do corpo. Nuvem dos 138 mil neurônios (shader de pontos aditivo, calor por neurônio
  decaindo a cada quadro) dentro da **casca translúcida** com borda fresnel, girando devagar; arrastar gira.
- **Rotação sincronizada** (06/09): o servidor mantém um relógio de rotação (`FLY_ROT_RAD_S`, 0,12 rad/s) e
  manda `rot` em cada quadro do cérebro. A página gira o cérebro por ele (com `ROT_FRENTE` = π, porque o eixo z
  dos dados cresce para trás e a vista inicial deve ser a cara dela); arrastar desloca só naquela tela e volta ao
  sincronismo em segundos. O corpo, no modo cinemático, orbita a câmera em volta da mosca com azimute
  `yaw − rot` (`renderizar_orbita`): rot = 0 é de frente para a cara dela e para a face anterior do cérebro; os
  lados batem (lado esquerdo dela = x negativo nos dados). A mosca não gira, a câmera gira.
- **Voo e cabeça** (06/09, modo cinemático): as asas ganharam duas dobradiças cada (abrir no eixo vertical,
  bater no eixo do corpo; no referencial da asa, girado 90°, são z e y) e o sentido é calibrado na partida
  medindo para onde a ponta vai (`calibrar_asas`). A fuga (fibra gigante) vira decolagem: sobe a 5 mm em 0,5 s,
  asas abrem e batem a 9 Hz estilizados, pernas recolhem, voa a 35 mm/s virando pelos neurônios de curva, e
  pousa quando a fibra silencia (mínimo 2 s no ar). A cabeça usa as juntas pelos EIXOS, não pelos nomes do
  flygym (que estão trocados): pitch = `joint_Head`, yaw = `joint_Head_roll`. Abaixa para comer, acompanha a
  curva, balança com a marcha, sacode na limpeza. Rótulos FLYING e LANDING na página.
- `brain/estimulos_extra.py` — **entradas e saídas extras por tipo celular** (06/09), regeneradas do parquet
  (a troca para a Janelia refaz sozinha, se os tipos tiverem o mesmo nome). Testado no cérebro isolado
  (400 ms, plasticidade off):
  - seguros: `lc16` (151 células visuais de objeto atrás; só vira um pouco), `eye_touch` (1.113 cerdas do olho
    a 40 Hz → limpeza ~22 Hz), `reward` (307 neurônios de dopamina PAM → só estado, 40 Hz), `mdn` (4 neurônios
    de comando de ré a 100 Hz → ré ~63 Hz);
  - **bloqueados:** `vinegar` (175 ORNs, prende a rede já a 30 Hz) e `heat` (7 células de calor, prende a 50 Hz).
    Tudo que entra pelo lobo antenal prende, igual ao odor Or56a. Paladar, visão, cerdas e dopamina são seguros.
  - saídas novas lidas como os descendentes: `halt` (DNp09, 2) e `reward` (PAM, 307).
- **Comportamentos novos no corpo** (06/09): ré (MDN → marcha invertida), limpeza dos olhos (variante das
  pernas da frente, cabeça baixa), sobressalto (fibra gigante entre 12 e 30 % → pulinho sem asas; acima disso
  decola), parada (DNp09 acima de 5 % E maior que a marcha, porque dispara junto com o P9), excitação (dopamina
  sobe rápido e decai em 30 s: marcha 40 % mais rápida, antenas e cabeça mais inquietas, rótulo EXCITED), e
  fisiologia de repouso declarada no rodapé (antenas tremem de leve, sacadas de cabeça a cada 2,5–6 s).
- `corpo/aparencia.py` — **cores de mosca real e pisos** (06/09). O NeuroMechFly pinta a mosca com texturas
  laranja; multiplicar pelo rgba do material só escurece. Então as texturas são recoloridas na memória do modelo
  depois de compilar e antes do primeiro render: a luminância de cada pixel vira uma rampa entre duas cores de
  *Drosophila* (castanho no tórax e cabeça, faixas pretas no abdômen com contraste realçado e suavizado, ponta
  escura por materiais próprios em A3/A4/A5 criados antes de compilar, pernas castanhas, olho vermelho-tijolo com
  brilho, asas translúcidas com brilho). Pisos gerados por código em `corpo/texturas/` (`gerar_pisos`): ardósia,
  bancada branca, madeira, casca de banana, musgo, mais o xadrez embutido e o **preto** (liso, reflectância 0,18,
  só o reflexo da mosca; escolha do Michel, é o padrão). Escolha no `START-Windows.bat`:
  `FLY_CORPO_PISO` e `FLY_CORPO_CORES` (real | original). Folha de opções renderizada por
  `scratchpad/opcoes_visual.py` na sessão de 06/09.
- `brain/preparar_casca.py` — gera `site/shell.bin` a partir da malha do cérebro inteiro do template FlyWire
  (pacote `flybrains`, 25 mil vértices), no mesmo espaço normalizado dos neurônios. Uns 5 mil neurônios ficam
  fora da casca: são os fotorreceptores e a lâmina, os olhos, que o molde não inclui. Antes do lançamento,
  trocar pela malha da Janelia (CC BY).
- `corpo/corpo.py` — o **corpo 3D** (NeuroMechFly v2 via flygym 1.2.1 + MuJoCo 3.2.7, física a 1e-4 s).
  Processo separado: lê as taxas motoras pelo WebSocket do servidor e devolve quadros JPEG por
  `POST /corpo/quadro`; o servidor repassa aos espectadores como quadro de tipo `corpo` e guarda o último
  em `GET /corpo/ultimo.jpg`. Tradução neurônio→movimento copiada do fly-brain: fuga > limpeza > alimentação
  > marcha, histerese de 0,3 s de mosca; marcha pelo `HybridTurningController` com drive esquerdo/direito,
  limpeza por oscilação das pernas da frente, alimentação por uma junta de probóscide acrescentada ao Rostrum.
  A mosca precisa de sensores de contato em tíbia e tarsos (exigência do controlador). Arena `Palco`: céu e
  chão escuros. `MUJOCO_GL=glfw`. Variáveis: `FLY_SERVIDOR`, `FLY_CORPO_W/H`, `FLY_CORPO_JPEG`, `FLY_CORPO_PLAY`,
  `FLY_CORPO_DT`, `FLY_CORPO_SUB`, `FLY_CORPO_AFINIDADE`. O boneco SVG anterior foi descartado (06/09: "horroroso").

### Tempo real: modo cinemático (padrão desde 06/09/2026)

Com física, o teto nesta máquina é 4× mais lento que o relógio mesmo em C puro (`mj_step` direto, sem Python:
1.264 passos/s a 2e-4). Passo 4e-4 chega a tempo real mas a marcha degrada e a fuga salta; 5e-4 derruba a mosca.
Então **tempo real com física é impossível aqui**, e o padrão virou `FLY_CORPO_MODO=cinematico`:

- mesmo modelo anatômico, mesmas trajetórias de perna gravadas de mosca real (`PreprogrammedSteps`), ritmadas
  pelo gerador de marcha (CPG a 1 ms) com amplitude = |drive| de cada lado e sentido pelo sinal, igual ao
  controlador; o corpo se desloca por cinemática (13 mm/s × drive médio, giro 1,5 rad/s × diferença);
- sem contato nem gravidade simulados: a pose de repouso vem de 0,3 s de física no início e depois fica fixa;
- probóscide estende/recolhe com suavização; limpeza = oscilação das pernas da frente + antenas; fuga = corrida
  1,3 + salto curto de 1,2 mm; balanço leve do corpo na marcha;
- 30 quadros/s cravados (`FLY_CORPO_FPS`), renderização própria sem acumular a lista de quadros do flygym;
- câmera `YawOnlyCamera`: segue a direção da mosca com suavização, então a vista é sempre lateral mesmo quando
  ela vira (com a `Camera` fixa ela aparecia de frente ou de costas depois de virar).

O rodapé do corpo diz "real time · recorded fly leg trajectories, rhythm and direction from her neurons".
O modo `fisica` continua disponível (contato real, ~4,4×), para clipes.

### "Parece time-lapse" (06/09, segunda rodada)

Duas causas, as duas corrigidas:

- **Ritmo fixo.** O controlador do flygym anda sempre a 12 Hz e só encurta a passada quando o drive cai; na
  tela vira vibração. Agora o ritmo vai de 4 a 14 Hz com o drive (`FREQ_MIN_HZ`/`FREQ_MAX_HZ`), como a mosca
  real, e a velocidade do corpo é passada × ritmo (`PASSADA_MM` = 1,17 mm, calibrada na física) para o pé não
  deslizar.
- **Poucos quadros por passada.** 12 passadas/s a 30 fps dá 2,5 quadros por passada e o olho lê como
  estroboscópio. Agora são **60 fps** (`FLY_CORPO_FPS`), sustentados com o cérebro no ar.

Para os 60 fps chegarem inteiros, o envio de quadros passou de um POST por quadro (chegava aos trancos, buracos
de 1,7 s) para um **WebSocket persistente** `/corpo/ws`; o corpo lê as taxas em `/ws?papel=corpo` e o servidor
não devolve os próprios quadros para essa conexão (senão o leitor atrasa segundos). A página mostra
"60 fps sent, 60 received".

**Controle de velocidade na página** (dev): slider "Body speed" 30–100 % manda `{"corpo_tempo": x}` pelo
WebSocket; o servidor põe em `body_cfg` de cada quadro e o corpo aplica em ~1 s (escala de tempo da cinemática).
Serve para calibrar no olho; o valor escolhido vira o padrão `FLY_CORPO_TEMPO`.

### Velocidade do corpo no modo física (medido 06/09/2026, "a animação está muito devagar")

| Configuração | passos de física/s | lentidão | marcha em 0,6 s |
|---|---|---|---|
| 1e-4, decisão a cada passo (original) | 560 | 18× | 8,1 mm |
| 2e-4, decisão a cada passo | 510 | 10× | 8,4 mm |
| 2e-4, 8 sub-passos remendados (**padrão**) | 1.400 | 3,5× | 8,5 mm |
| 2e-4, 16 sub-passos | 1.370 | 3,6× | 6,7 mm (degrada) |

"Remendado" = a física roda em `dt` e o controlador é avisado que o passo dele é `SUB*dt` (`remendar()`:
`sim.timestep`, `cpg_network.timestep`, `max_increment`, persistências). Só sub-passos, sem o remendo, fazem a
mosca quase parar, porque o gerador de marcha avança uma vez por decisão. Fuga (16 mm/s) e limpeza continuam
iguais. No processo real, com JPEG e WebSocket, dá 4,4×. Com o cérebro no ar caía para 5,8× por disputa de CPU;
`reservar_cpu()` põe o corpo nos núcleos 0xFF00 com prioridade acima do normal e o cérebro em 0x00FF, e volta a
4,4×. A tela mostra "N× slow motion" no rodapé do corpo. A marcha usa escala própria (`ESCALA_MARCHA` = 100 Hz):
P9 a 39–57 Hz dava drive 0,2 com a escala de 200 e a mosca mal andava.

## Protocolo do quadro

Binário: `[uint32 tamanho][JSON][uint32 × N]`. O JSON traz tempo de cérebro, velocidade, disparos por região,
taxa (Hz) dos sete grupos motores, estímulos ativos, espectadores e sinapses alteradas. Os uint32 são os
índices dos neurônios que dispararam no quadro (amostrados se passarem de `FLY_MAX_IDX`).

## Licenças — ler antes de lançar

- Código do modelo e do fly-brain: MIT (`brain/vendor/LICENSE-fly-brain.txt`).
- **Dados do FlyWire (`brain/data/flywire/`): CC BY-NC 4.0, uso não comercial.** Servem para desenvolver.
  Antes de qualquer lançamento com taxa, trocar pelo conectoma **Male CNS da Janelia (CC BY 4.0)**:
  grafo de conexões, neurotransmissor por neurônio e tipos celulares em https://male-cns.janelia.org/download/.
  A troca é refazer `vendor/neuronios.py` por tipo celular e regenerar os dados.
- NeuroMechFly/flygym e MuJoCo (fase do corpo): Apache 2.0.

## Página pública e página de desenvolvimento (07/09/2026)

- `/` → `site/publico.html`: o que o espectador vê. Cérebro em 3D, corpo, painel com "what she wants to do",
  o mercado com os cards, e um "Under the hood" fechado com as regiões e o texto de honestidade. Sem botões,
  sem slider. Tecla **C** ou o botão "cinema mode" esconde o painel (para clipes e para o X).
- `/dev` → `site/index.html`: a mesma cena com os botões de estímulo, o slider de velocidade e o auto-stimulate.
  Vai ganhar senha antes do site público.
- O corpo passou a renderizar em **1280×540** (2,37:1) e a página encaixa com `object-fit: contain`: a faixa do
  corpo é larga e baixa, e com piso e céu pretos a borda do encaixe some. Antes cortava a mosca. Câmera a 5,6 mm.

### Estilo da página pública: painel de instrumento (07/09/2026)

Michel perguntou se podia ser no estilo do site do Gogh (app de desenho cinza-claro). Decisão: pegar do Gogh
a **barra do topo** (marca, LIVE pulsando, contrato com copiar em um clique, link do X) e a disciplina dos
rótulos, mas manter o preto, porque a cena é o produto. Resultado: preto contínuo, sem caixas, só linhas de
1 px; tudo em monoespaçada (JetBrains Mono → Cascadia → Consolas); uma cor de vida (verde) para LIVE, compra e
"reacting"; vermelho só para venda, fuga e apagão; amarelo só nas barras motoras; o resto cinza. O contrato e
o X são as constantes `CA` e `X_URL` no topo do script de `publico.html` (vazias = "not launched yet").
Logo à mão dele pode entrar depois no lugar da marca em texto.

## Plasticidade que não mata (07/09/2026)

O decaimento do fly-brain puxa todas as sinapses para zero (1e-7 por atualização: ×0,88 em 21 min de cérebro,
×0,34 em 3 h). Numa vida de dias ela ficaria muda. Agora o decaimento puxa de volta para o valor **original do
conectoma** (`_base` em `motor.py`): o que ela aprendeu esquece devagar, a fiação nunca some. O estado salvo da
primeira noite (já decaído em 12 %) foi apagado para ela recomeçar limpa; o contador "synapses changed since
birth" volta a fazer sentido.

## Mercado → sentidos → reflexo → ordem (07/09/2026; papel ou real)

`mercado/mercado.py`, terceiro processo (o `.bat` já abre). **Sem agente, sem IA de linguagem**: tudo é
tabela e regra fixa, e o único lugar com "decisão" é o cérebro.

- **Fonte:** GeckoTerminal indexa as curvas da Pons V2 na Robinhood Chain (`/networks/robinhood/dexes/pons-v2`).
  Preço em ETH por token, volume, e os 300 últimos trades com carteira, valor e hora. Atraso de minutos; para o
  modo real, ler a curva na chain. Limite ~30 chamadas/min (respeitado com leitura a cada 15 s).
- **Token:** o de maior volume 24h da Pons V2 no momento (`FLY_MERCADO_POOL` fixa um). Sem relação com projeto
  nenhum. Troca sozinho se ficar 1 h sem trade.
- **Mapa mercado → sentido (público, 07/09 v2, para todas as reações aparecerem):** limiares relativos ao
  token (p50 e p90 do valor dos últimos 300 trades), não dólares fixos.

  | Evento na Pons | Sentido | O que ela tende a fazer |
  |---|---|---|
  | compra | açúcar, 150 ms a 2,5 s pelo valor | come (FEEDING) |
  | compra ≥ p90 | + dopamina 500 ms | fica EXCITED |
  | primeira compra de uma carteira | + dopamina 300 ms | EXCITED |
  | venda | amargo | cérebro reage; carteira vende 25 % após 6 s |
  | venda ≥ p50 | + empurrão de ré 300 ms | BACKING UP |
  | venda ≥ p90 | + sombra 400 ms | ESCAPE / FLYING |
  | ≥ 6 trades num minuto | vibração (1×/min) | GROOMING |
  | ≥ 4 vendas num minuto | sombra 500 ms (1×/2 min) | ESCAPE / FLYING |
  | preço +2 % em 5 min | impulso de andar (1×/2 min) | anda |
  | preço −2 % em 5 min | empurrão de ré | BACKING UP |
  | 4 min sem nada | poeira nos olhos (1×/4 min) | GROOMING EYES |

  Antes (v1) só compra/venda viravam açúcar/amargo e sombra exigia $100: na prática ela só comia.
- **Regras reflexo → ordem (públicas, `REGRAS`):** probóscide ≥ 30 Hz por 2 s → compra 5 % do saldo
  (`FLY_MERCADO_ORDEM`, fração); fuga ≥ 40 Hz por 0,5 s ou ré ≥ 30 Hz por 0,5 s → vende tudo; **regra de ponte
  declarada:** amargo ativo por 6 s → vende 25 % do que tem (o amargo acende o cérebro mas não chega aos motores
  lidos; igual ao `bitter_escape` do fly-brain); intervalo mínimo 20 s entre ordens; **teto por ordem**
  (compra e venda) `FLY_MERCADO_MAX_ORDEM_USD` (US$ 5; 0 = sem teto). **Valores em dólar** (decisão do Michel,
  07/09: "vou dar 100 dólares para ela"): `FLY_MERCADO_SALDO_USD` (100) e o teto são convertidos para ETH pelo
  preço implícito da Pons na primeira leitura (ETH ≈ US$ 2.500 em 07/09 → 0,04 ETH). Taxa da curva 1 %.
  Primeira noite (06→07/09): 10 compras de lote fixo, nenhuma venda, saldo zerado. Daí o lote em fração e a
  venda pelo amargo.
- **Replay:** se a Pons ficar 90 s sem trade novo, reprisa os últimos 40 trades, um a cada 8 s, marcados
  `replay` na tela (`FLY_MERCADO_REPLAY=0` desliga). Para a noite não ficar parada.
- **Canal:** `POST/GET /api/mercado` no servidor; eventos (`trade`, `sinal`, `ordem`, `info`, `resumo`) vão por
  WebSocket para a página, que mostra o resumo (token, preço, carteira, PnL) e os últimos 8 cards.
- **Carteira dela (07/09):** `mercado/carteira.py gerar --auto` criou o keystore `mercado/carteira.json` com
  senha aleatória em `mercado/carteira.senha` (os dois fora do git; **perder os arquivos = perder o dinheiro**;
  copiar os dois para um lugar seguro). Endereço público: `0x4431BcB5b68A3831e9e340011a1F2aB6404f7dfD`.
  Decisão do Michel: carteira separada da de lançamento; ele saca as creator fees à mão e envia para ela.
  `carteira.carregar()` abre o keystore para o modo real. O processo dela nunca terá função de saque.
### Modo real na curva da Pons V2 (07/09/2026, padrão no `.bat`)

`FLY_MERCADO_MODO=real` liga a `CarteiraReal` (em `mercado.py`), que tem a mesma interface da carteira de papel
mas lê o saldo da chain e executa em `mercado/pons.py` (web3, escrito do zero; interface dos contratos na doc
V2 da Pons). O que está lá:

- **Contratos:** fábrica `0x7eD598BcEf8bd9Edd8C97A195C6d13f40801EC7e` (`getLaunchedToken(token)` dá a curva, a
  fase e a taxa do criador); curva com `buy(quoteIn, minTokensOut, recipient)` pagável (o ETH vai em `value`),
  `sell(tokensIn, minQuoteOut, recipient)` (precisa de `approve` do token para a curva, feito uma vez com
  allowance máxima) e as views `getReserves`, `sellableTokens`, `feeBps`, `creatorTaxBps`,
  `currentSnipeTaxBps(addr)`, `graduated`, `isNativeQuote`. A "pool" da GeckoTerminal **é** o endereço da curva;
  o token vem em `relationships.base_token` (`robinhood_0x...`).
- **Cotação:** taxas (fee, criador, snipe) saem da entrada; o resto move produto constante
  `out = net·T/(R+net)`, limitado a `sellableTokens`. Conferido na chain: 0,0002 ETH → 116.840,94 ROBIN, exato.
  Venda: `bruto = tokens·R/(T+tokens)` menos as taxas. Mínimo aceito = cotação − 3 % (`SLIPPAGE`).
- **Regras extras do real:** reserva de gás `FLY_MERCADO_RESERVA_GAS` (0,0015 ETH) nunca é gasta; só adota
  curva **ativa (fase 0)**, e a cada 5 min confere se graduou (graduou → card, larga o token, escolhe outro);
  não troca de token enquanto segurar tokens; venda não deixa poeira (se o resto valeria < US$ 0,25, vai tudo);
  falha numa ordem vira card de erro e pausa 2 min. Saldo relido a cada 30 s: diferença que não veio de ordem
  dela é **depósito ou saque do Michel** → card "wallet topped up" e a base do PnL move junto.
- **Gás medido (07/09):** preço 0,31 gwei; compra 97.755 gas, venda 75.791 + approve → uns 4 centavos por ordem.
- **Teste de centavos** (`mercado/teste_real.py [ETH] [--seco]`; `--seco` só cota e simula): 07/09, compra
  `0x2302bf2e…3b19` e venda `0x7b79945c…3b03e` no ROBIN, custo total 0,000072 ETH (taxa 1 % ida e volta + gás).
- **Tela:** cards de ordem trazem o link da transação no explorer (`robinhoodchain.blockscout.com`) e o resumo
  mostra o endereço dela.
- Nomes de token com emoji derrubavam o console cp1252 → `sys.stdout.reconfigure(errors='replace')`.

## Site público (07/09/2026): mosca desenhada no navegador + relay no Railway

O JPEG de 1280×540 a 60 fps servia no localhost, mas eram ~3 MB/s por espectador. Para a internet, dois
pedaços novos:

- **Mosca no navegador** (`site/fly-cliente.js`): `corpo/exportar_modelo.py` exporta o modelo compilado pelo
  MuJoCo (71 corpos, 93 juntas, 69 malhas, texturas já recoloridas) para `site/fly-model.json` + `.bin` +
  `site/fly-tex/`. As malhas são decimadas por quádricas (`fast_simplification`) mantendo a UV por vértice:
  502 mil → 117 mil triângulos, 1,4 MB + 272 KB de textura. O corpo manda **poses** (`FLY_CORPO_SAIDA=pose`,
  padrão): o `qpos` inteiro (99 floats) + a câmera, 30×/s, ~400 B cada (`corpo/corpo3d_envio.py`). A página
  refaz a cinemática direta igual ao `mj_kinematics` (pais antes dos filhos, dobradiça em torno do próprio
  `jnt_pos`, junta livre da raiz direto do qpos), interpola entre os dois últimos quadros (50 ms de atraso) e
  desenha em three.js com chão preto e reflexo (cópia espelhada em z, translúcida). `jpeg` e `ambos` seguem
  disponíveis. Refazer a exportação se o modelo ou as cores mudarem.
- **Índices dos neurônios em delta-varint** (`enc: 'dv'` no cabeçalho): ordenados, diferença em varint de 7 bits,
  ~1 byte por neurônio em vez de 4. As duas páginas decodificam (`decodeDV`).
- **Relay** (`relay/servidor.py`, aiohttp, roda no Railway com o `Procfile` + `requirements.txt` da raiz): o PC
  conecta em `/fonte?token=…` (`brain/relay_cliente.py`, ligado por `FLY_RELAY_URL` + `FLY_RELAY_TOKEN`) e manda
  o último quadro do cérebro, o último do corpo e os eventos do mercado; os espectadores conectam em `/ws` e
  recebem o mesmo protocolo da página local (a página não muda). Cada espectador tem fila de 6: quem atrasa
  perde quadro, não acumula. O relay devolve `{"viewers": n}` e o número entra no campo `viewers` dos quadros.
  Sem `/dev`, sem estímulo pelo público. `/health` mostra se a fonte está ligada.
- **Domínio (07/09): `flybrain.finance`** (Michel comprou; ele escreveu "flybrian" no chat, conferir a grafia no
  registrador). O `.bat` já aponta `FLY_RELAY_URL=wss://flybrain.finance/fonte` e lê o token de `relay.token`
  (arquivo na raiz, fora do git, gerado com `secrets.token_urlsafe(36)`). Os meta tags de compartilhamento
  (og:*, twitter:*), o canonical e a imagem `site/og.png` (`brain/gerar_og.py`: nuvem real dos neurônios + marca,
  1200×630) usam esse domínio; se o domínio for outro, trocar nos meta tags de `publico.html`, no `gerar_og.py`
  e no `.bat`.
- **No Railway (07/09, criado pela CLI):** projeto `flybrain`, serviço `flybrain` ligado ao GitHub
  `ojotunn/flybrain` (push na main = redeploy), variável `FLY_RELAY_TOKEN` = conteúdo de `relay.token`.
  URL do serviço: `https://flybrain-production.up.railway.app`. Domínio `www.flybrain.finance` registrado no
  serviço; a raiz `flybrain.finance` a CLI recusou enquanto o domínio não existia no DNS (adicionar de novo pelo
  `railway domain flybrain.finance --service flybrain` ou pelo painel). **DNS no registrador:** `www` CNAME →
  `svl3c17d.up.railway.app` e TXT `_railway-verify.www` com o valor que o `railway domain status` mostra; para a
  raiz (apex) o DNS precisa de ALIAS/ANAME ou CNAME flattening (Cloudflare gratuito resolve; o proxy laranja
  passa WebSocket). Testado ponta a ponta com o relay local na porta 8436 e depois no Railway
  (`/health` com `fonte: true`).
- **Página:** carteira dela na barra do topo (copiar) e em números grandes no painel; ABOUT abre a descrição da
  tecnologia (cérebro, corpo, mapa do mercado, regras das ordens, o que não existe, créditos).

## Próximos passos

1. Michel cria o serviço no Railway e aponta o `.bat` para ele; domínio próprio.
2. Troca para o conectoma da Janelia (licença) antes do token com taxa.
3. Vigia que reinicia os três processos se um cair; adote um neurônio; relatório diário; segunda mosca; mundo
   virtual com manchas de açúcar.
