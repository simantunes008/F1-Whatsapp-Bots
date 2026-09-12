import os
from dotenv import load_dotenv
import requests
from datetime import datetime, timezone, timedelta
import zoneinfo

load_dotenv()

id_instance = os.getenv("ID_INSTANCE")
api_token = os.getenv("API_TOKEN")
chat_id = os.getenv("CHAT_ID")
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
    race_date_str = race['date']
    
    now = datetime.now(lisbon_tz).date()
    race_date = datetime.strptime(race_date_str, "%Y-%m-%d").date()
    
    days_until_race = (race_date - now).days
    
    if not (0 <= days_until_race <= 7):
        print(f"Next race is in {days_until_race} days. No message sent")
        exit()

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
        print("Message sent")

        pin_url = f"{host}/waInstance{id_instance}/pinMessage/{api_token}"
        pin_payload = {"chatId": chat_id, "idMessage": id_mensagem, "pin": True, "pinType": "pinForEveryone"}
        pin_resp = requests.post(pin_url, json=pin_payload)
        
        if pin_resp.status_code == 200:
            print("Message pinned in the group")
        else:
            print(f"Could not pin the message. Error: {pin_resp.text}")
    else:
        print(f"Error: {resp.text}")

except Exception as e:
    print(f"Error: {e}")