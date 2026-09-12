import os
from dotenv import load_dotenv
import requests
import asyncio
import time
import threading
from fastf1.livetiming.client import SignalRClient

load_dotenv()

id_instance = os.getenv("ID_INSTANCE")
api_token = os.getenv("API_TOKEN")
chat_id = os.getenv("CHAT_ID")
host = "https://7107.api.greenapi.com"

ficheiro_dados = "f1_live.txt"

def send_msg(mensagem):
    send_url = f"{host}/waInstance{id_instance}/sendMessage/{api_token}"
    payload = {"chatId": chat_id, "message": mensagem}
    resp = requests.post(send_url, json=payload)
    
    if resp.status_code == 200:
        print("Alerta ao vivo enviado com sucesso!")
    else:
        print(f"Erro ao enviar alerta: {resp.text}")

def init_fastf1():
    print("A conectar aos servidores da F1 em direto...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    cliente = SignalRClient(ficheiro_dados, debug=False)
    loop.run_until_complete(cliente.async_start())

def race_monitor():
    print("A aguardar dados da corrida...")
    time.sleep(5) 
    
    with open(ficheiro_dados, "r", encoding="utf-8") as f:
        f.seek(0, 2)
        estado_pista_anterior = None
        
        while True:
            linha = f.readline()
            if not linha:
                time.sleep(1) 
                continue
                
            if "TrackStatus" in linha:
                if '"Status":"4"' in linha and estado_pista_anterior != "4":
                    print("⚠️ DETETADO SAFETY CAR!")
                    send_msg("⚠️ *SAFETY CAR NA PISTA!* 🟡")
                    estado_pista_anterior = "4"
                    
                elif '"Status":"5"' in linha and estado_pista_anterior != "5":
                    print("🔴 DETETADA BANDEIRA VERMELHA!")
                    send_msg("🔴 *BANDEIRA VERMELHA!* Sessão interrompida.")
                    estado_pista_anterior = "5"
                    
                elif '"Status":"1"' in linha and estado_pista_anterior != "1":
                    print("🟢 PISTA LIMPA!")
                    send_msg("🟢 *PISTA LIMPA!* Corrida retomada.")
                    estado_pista_anterior = "1"

# Iniciar threads
thread = threading.Thread(target=init_fastf1)
thread.start()

race_monitor()
