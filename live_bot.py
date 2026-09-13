import os
import json
from dotenv import load_dotenv
import requests
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
        print(f"Alerta enviado: {mensagem}")
    else:
        print(f"Erro ao enviar alerta: {resp.text}")

def init_fastf1():
    print("A conectar aos servidores da F1 em direto...")
    cliente = SignalRClient(ficheiro_dados, debug=False)
    cliente.start()

def live_monitor():
    print("A aguardar criação do ficheiro de dados...")
    
    while not os.path.exists(ficheiro_dados):
        time.sleep(1)
        
    print("Ficheiro detetado! A monitorizar a corrida...")
    time.sleep(2)
    
    mensagens_vistas = set()
    
    with open(ficheiro_dados, "r", encoding="utf-8") as f:
        f.seek(0, 2)
        estado_pista_anterior = None
        
        while True:
            linha = f.readline()
            if not linha:
                time.sleep(1) 
                continue
                
            # 1. Monitorizar Estado da Pista
            if "TrackStatus" in linha:
                if '"Status":"4"' in linha and estado_pista_anterior != "4":
                    send_msg("*SAFETY CAR NA PISTA!*")
                    estado_pista_anterior = "4"
                    
                elif '"Status":"5"' in linha and estado_pista_anterior != "5":
                    send_msg("*BANDEIRA VERMELHA!* Sessão interrompida.")
                    estado_pista_anterior = "5"
                    
                elif '"Status":"1"' in linha and estado_pista_anterior != "1":
                    send_msg("*PISTA LIMPA!* Corrida retomada.")
                    estado_pista_anterior = "1"

            # 2. Monitorizar Direção de Prova
            elif "RaceControlMessages" in linha:
                try:
                    partes = linha.split(":", 1)
                    if len(partes) > 1:
                        dados_json = json.loads(partes[1].strip())
                        
                        for msg_obj in dados_json.get("Messages", []):
                            texto_mensagem = msg_obj.get("Message", "")
                            
                            if texto_mensagem in mensagens_vistas:
                                continue
                            texto_upper = texto_mensagem.upper()
                            
                            if "INVESTIGATION" in texto_upper:
                                send_msg(f"*Investigação:* {texto_mensagem}")
                                mensagens_vistas.add(texto_mensagem)
                                
                            elif "PENALTY" in texto_upper:
                                send_msg(f"*Penalização:* {texto_mensagem}")
                                mensagens_vistas.add(texto_mensagem)
                                
                except json.JSONDecodeError:
                    pass
                except Exception as e:
                    print(f"Erro ao processar Race Control: {e}")

thread = threading.Thread(target=init_fastf1, daemon=True)
thread.start()

live_monitor()