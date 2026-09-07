@echo off
cd /d "%~dp0"
rem Piso do corpo: preto, ardosia, bancada, madeira, banana, musgo ou xadrez. Cores: real ou original.
set FLY_CORPO_PISO=preto
set FLY_CORPO_CORES=real
rem Corpo: pose (a mosca e desenhada no navegador; leve p/ internet), jpeg (render local) ou ambos.
set FLY_CORPO_SAIDA=pose
rem Site publico: relay no Railway (relay/servidor.py) em flybrain.finance. O token fica em relay.token (fora do git);
rem o MESMO valor vai na variavel FLY_RELAY_TOKEN do servico no Railway.
set FLY_RELAY_URL=wss://flybrain.finance/fonte
if exist relay.token set /p FLY_RELAY_TOKEN=<relay.token
rem Mercado: modo real (carteira dela em mercado\carteira.json) ou papel. Em DOLAR: teto por ordem e lote (fracao do saldo).
set FLY_MERCADO_MODO=real
set FLY_MERCADO_MAX_ORDEM_USD=5
set FLY_MERCADO_ORDEM=0.05
rem so no modo papel: saldo virtual inicial em ETH
set FLY_MERCADO_SALDO_ETH=0.05
echo ==== FLY - cerebro (porta 8435) + corpo 3D ====
echo Abra http://localhost:8435 no navegador. Ctrl+C aqui encerra o cerebro e salva as sinapses.
start "FLY corpo 3D" "py\Scripts\python.exe" "corpo\corpo.py"
start "FLY mercado" "py\Scripts\python.exe" "mercado\mercado.py"
"py\Scripts\python.exe" "brain\servidor.py"
pause
