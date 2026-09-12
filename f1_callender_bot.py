import requests
from datetime import datetime, timezone, timedelta
import zoneinfo

id_instance = "710722735086"
api_token = "79d223920d8b4595b06237b58943208b58ad458e29c949b09b"
chat_id = "120363424796569912@g.us"
host = "https://7107.api.greenapi.com"

f1_url = "https://api.jolpi.ca/ergast/f1/current/next.json"
lisbon_tz = zoneinfo.ZoneInfo("Europe/Lisbon")

def converter_hora(data_str, hora_str):
    dt_utc = datetime.strptime(f"{data_str}T{hora_str}", "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    dt_local = dt_utc.astimezone(lisbon_tz)
    return dt_local.strftime("%d/%m (%H:%M)")

try:
    response = requests.get(f1_url)
    response.raise_for_status()

    race = response.json()['MRData']['RaceTable']['Races'][0]
    race_name = race['raceName']
    race_date_str = race['date'] # Ex: '2026-09-20'
    
    # --- VERIFICAÇÃO: A corrida é nos próximos 7 dias? ---
    hoje = datetime.now(lisbon_tz).date()
    data_corrida = datetime.strptime(race_date_str, "%Y-%m-%d").date()
    
    dias_ate_corrida = (data_corrida - hoje).days
    
    # Se faltarem mais do que 7 dias (ou se já tiver passado), o script pára aqui
    if not (0 <= dias_ate_corrida <= 7):
        print(f"A próxima corrida ({race_name}) é daqui a {dias_ate_corrida} dias. Nenhuma mensagem enviada hoje.")
        exit()
    # ---------------------------------------------------

    # Construir a mensagem com todos os treinos
    message = f"*{race_name}*\n\n"
    
    if 'FirstPractice' in race:
        message += f"*Treino 1:* {converter_hora(race['FirstPractice']['date'], race['FirstPractice']['time'])}\n"
    if 'SecondPractice' in race:
        message += f"*Treino 2:* {converter_hora(race['SecondPractice']['date'], race['SecondPractice']['time'])}\n"
    if 'ThirdPractice' in race:
        message += f"*Treino 3:* {converter_hora(race['ThirdPractice']['date'], race['ThirdPractice']['time'])}\n"
    if 'Sprint' in race:
        message += f"*Sprint:* {converter_hora(race['Sprint']['date'], race['Sprint']['time'])}\n"
    if 'Qualifying' in race:
        message += f"*Qualificação:* {converter_hora(race['Qualifying']['date'], race['Qualifying']['time'])}\n"
        
    message += f"*Corrida:* {converter_hora(race['date'], race['time'])}"

    send_url = f"{host}/waInstance{id_instance}/sendMessage/{api_token}"
    payload = {"chatId": chat_id, "message": message}
    resp = requests.post(send_url, json=payload)
    
    if resp.status_code == 200:
        id_mensagem = resp.json().get("idMessage")
        print("Mensagem enviada com sucesso!")

        pin_url = f"{host}/waInstance{id_instance}/pinMessage/{api_token}"
        pin_payload = {"chatId": chat_id, "idMessage": id_mensagem, "pin": True, "pinType": "pinForEveryone"}
        pin_resp = requests.post(pin_url, json=pin_payload)
        
        if pin_resp.status_code == 200:
            print("Mensagem fixada no grupo com sucesso!")
        else:
            print(f"Aviso: Não foi possível fixar. O bot é admin? Erro: {pin_resp.text}")
    else:
        print(f"Erro ao enviar: {resp.text}")

except Exception as e:
    print(f"Ocorreu um erro: {e}")