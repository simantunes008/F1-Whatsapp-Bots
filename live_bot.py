import asyncio
import time
import threading
from fastf1.livetiming.client import SignalRClient

ficheiro_dados = "f1_live.txt"

def iniciar_fastf1():
    """Esta função liga-se aos servidores da F1 e começa a gravar os dados"""
    print("A conectar aos servidores da F1...")
    # O cliente SignalR precisa de correr num loop assíncrono
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Inicia a gravação (fica a correr até a sessão acabar)
    cliente = SignalRClient(ficheiro_dados, debug=False)
    loop.run_until_complete(cliente.async_start())

def monitorizar_corrida():
    """Esta função lê o ficheiro em tempo real e deteta o Safety Car"""
    print("A aguardar dados da corrida...")
    time.sleep(5) # Espera que o ficheiro seja criado
    
    with open(ficheiro_dados, "r", encoding="utf-8") as f:
        # Vai para o fim do ficheiro
        f.seek(0, 2)
        
        estado_pista_anterior = None
        
        while True:
            linha = f.readline()
            if not linha:
                time.sleep(1) # Se não houver dados novos, espera 1 segundo
                continue
                
            # Procurar pacotes de dados de 'TrackStatus' (Estado da pista)
            if "TrackStatus" in linha:
                # O status 4 significa Safety Car, 5 significa Red Flag, 1 é Pista Limpa
                if '"Status":"4"' in linha and estado_pista_anterior != "4":
                    print("⚠️ DETETADO SAFETY CAR! -> Enviar WhatsApp aqui")
                    # colocar_aqui_a_funcao_do_whatsapp("⚠️ *SAFETY CAR NA PISTA!*")
                    estado_pista_anterior = "4"
                    
                elif '"Status":"1"' in linha and estado_pista_anterior != "1":
                    print("🟢 PISTA LIMPA! -> Enviar WhatsApp aqui")
                    estado_pista_anterior = "1"

# 1. Iniciar a ligação à F1 num processo separado (Thread) para não bloquear o código
thread_f1 = threading.Thread(target=iniciar_fastf1)
thread_f1.start()

# 2. Começar a ler os dados em tempo real no processo principal
monitorizar_corrida()