"""Envia o calendário do fim de semana de GP para o grupo de WhatsApp.

Sai com 0 quando não há nada a enviar e com 1 em caso de erro, para que o
GitHub Actions marque a execução como falhada e notifique. Antes, qualquer
falha ficava escondida num job verde.
"""

import sys
import zoneinfo
from datetime import datetime, timezone

import f1_api
import whatsapp

LISBOA = zoneinfo.ZoneInfo("Europe/Lisbon")
JANELA_DIAS = 7
LINK_STREAM = "https://formula1streams.plus/"


def converter_hora(data_str, hora_str):
    """Converte data e hora UTC da API para hora de Lisboa."""
    dt_utc = datetime.strptime(
        f"{data_str}T{hora_str}", "%Y-%m-%dT%H:%M:%SZ"
    ).replace(tzinfo=timezone.utc)
    return dt_utc.astimezone(LISBOA).strftime("%d/%m (%H:%M)")


def linha_sessao(corrida, chave, etiqueta):
    """Linha formatada de uma sessão, ou vazia se o fim de semana não a tiver."""
    sessao = corrida.get(chave)
    if not sessao:
        return ""
    return f"*{etiqueta}:* {converter_hora(sessao['date'], sessao['time'])}\n"


def construir_mensagem(corrida):
    mensagem = f"*{corrida['raceName']}*\n\n"
    mensagem += linha_sessao(corrida, "FirstPractice", "Treino 1")

    # Num fim de semana sprint, as sessões de sprint ocupam o lugar do T2/T3.
    if "SprintQualifying" in corrida:
        mensagem += linha_sessao(corrida, "SprintQualifying", "Qualificação Sprint")
    else:
        mensagem += linha_sessao(corrida, "SecondPractice", "Treino 2")

    if "Sprint" in corrida:
        mensagem += linha_sessao(corrida, "Sprint", "Sprint")
    else:
        mensagem += linha_sessao(corrida, "ThirdPractice", "Treino 3")

    mensagem += linha_sessao(corrida, "Qualifying", "Qualificação")
    mensagem += f"*Corrida:* {converter_hora(corrida['date'], corrida['time'])}\n\n"
    mensagem += f"*Assiste em:* {LINK_STREAM}"
    return mensagem


def main():
    whatsapp.validar_config()

    corrida = f1_api.proxima_corrida()
    data_corrida = datetime.strptime(corrida["date"], "%Y-%m-%d").date()
    dias = (data_corrida - datetime.now(LISBOA).date()).days

    if not 0 <= dias <= JANELA_DIAS:
        print(
            f"Próxima corrida ({corrida['raceName']}) é daqui a {dias} dias. "
            "Nada a enviar."
        )
        return 0

    whatsapp.enviar_e_fixar(construir_mensagem(corrida))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as erro:
        print(f"ERRO: {erro}", file=sys.stderr)
        sys.exit(1)
