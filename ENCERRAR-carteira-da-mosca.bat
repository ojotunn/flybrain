@echo off
cd /d "%~dp0"
rem Ferramenta do dono: vende os tokens da mosca na curva e manda o ETH para a carteira do Michel.
rem Pede SIM antes de cada passo. A chave dela nunca aparece na tela.
"py\Scripts\python.exe" "mercado\encerrar.py" 0x3EF754638fF72dC83693B3D099eEf2C335D804A7
pause
