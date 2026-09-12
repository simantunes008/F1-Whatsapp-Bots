import os
from dotenv import load_dotenv
import requests
from datetime import datetime, timezone
import zoneinfo

load_dotenv()

id_instance = os.getenv("ID_INSTANCE")
api_token = os.getenv("API_TOKEN")
chat_id = os.getenv("CHAT_ID")
host = "https://7107.api.greenapi.com"

f1_url = "https://api.jolpi.ca/ergast/f1/current/next.json"
lisbon_tz = zoneinfo.ZoneInfo("Europe/Lisbon")

try:
    response = requests.get(f1_url)
    response.raise_for_status()
    
    races_data = response.json()['MRData']['RaceTable']['Races']
    if not races_data:
        print("Não foram encontradas próximas corridas.")
        exit()
        
    race = races_data[0]
    race_name = race['raceName']
    
    if 'Qualifying' not in race:
        print(f"A próxima corrida ({race_name}) não tem dados de qualificação estruturados.")
        exit()
        
    qualifying_date_str = race['Qualifying']['date']
    hoje = datetime.now(lisbon_tz).date()
    data_quali = datetime.strptime(qualifying_date_str, "%Y-%m-%d").date()
    
    if data_quali != hoje:
        print(f"Hoje não é o dia da qualificação. A qualificação é a {data_quali}.")
        exit()

    season = race['season']
    round_num = race['round']
    qualifying_url = f"https://api.jolpi.ca/ergast/f1/{season}/{round_num}/qualifying.json"
    
    quali_resp = requests.get(qualifying_url)
    quali_resp.raise_for_status()
    
    quali_data = quali_resp.json()['MRData']['RaceTable']['Races']
    if not quali_data or 'QualifyingResults' not in quali_data[0]:
        print("A qualificação já ocorreu, mas os resultados/grelha ainda não foram publicados na API.")
        exit()
        
    results = quali_data[0]['QualifyingResults']
    
    message = f"*Grelha de Partida - {race_name}*\n\n"
    
    for driver_res in results[:10]:
        pos = driver_res['position']
        name = f"{driver_res['Driver']['givenName']} {driver_res['Driver']['familyName']}"
        constructor = driver_res['Constructor']['name']
        message += f"{pos}. {name} ({constructor})\n"

    send_url = f"{host}/waInstance{id_instance}/sendMessage/{api_token}"
    payload = {"chatId": chat_id, "message": message}
    resp = requests.post(send_url, json=payload)
    
    if resp.status_code == 200:
        id_mensagem = resp.json().get("idMessage")
        print("Grelha de partida enviada com sucesso!")

        pin_url = f"{host}/waInstance{id_instance}/pinMessage/{api_token}"
        pin_payload = {"chatId": chat_id, "idMessage": id_mensagem, "pin": True, "pinType": "pinForEveryone"}
        pin_resp = requests.post(pin_url, json=pin_payload)
        
        if pin_resp.status_code == 200:
            print("Grelha fixada no grupo com sucesso!")
        else:
            print(f"Aviso: Não foi possível fixar. Erro: {pin_resp.text}")
    else:
        print(f"Erro ao enviar: {resp.text}")

except Exception as e:
    print(f"Ocorreu um erro: {e}")
