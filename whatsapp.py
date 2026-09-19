"""Cliente da Green API: envio e fixação de mensagens no grupo.

Antes este bloco estava copiado nos três bots. Qualquer mudança ao host, às
credenciais ou à sequência enviar/fixar passa a ser feita só aqui.
"""

import os

from dotenv import load_dotenv

from http_client import ErroHTTP, pedir

load_dotenv()

ID_INSTANCE = os.getenv("ID_INSTANCE")
API_TOKEN = os.getenv("API_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# O prefixo do host é específico da instância Green API, não é um endpoint
# genérico. GREEN_API_HOST permite trocar de instância sem mexer no código.
HOST = os.getenv("GREEN_API_HOST", "https://7107.api.greenapi.com")


class ErroWhatsApp(Exception):
    """A Green API recusou o pedido ou falta configuração."""


def validar_config():
    """Falha cedo e com nome, em vez de um 401 opaco a meio do envio."""
    em_falta = [
        nome
        for nome, valor in (
            ("ID_INSTANCE", ID_INSTANCE),
            ("API_TOKEN", API_TOKEN),
            ("CHAT_ID", CHAT_ID),
        )
        if not valor
    ]
    if em_falta:
        raise ErroWhatsApp(
            f"Variáveis de ambiente em falta: {', '.join(em_falta)}"
        )


def _url(metodo_api):
    return f"{HOST}/waInstance{ID_INSTANCE}/{metodo_api}/{API_TOKEN}"


def enviar(mensagem):
    """Envia a mensagem e devolve o idMessage.

    Levanta ErroWhatsApp se o envio não for confirmado: quem chama decide se
    isso termina o programa ou é apenas registado.
    """
    validar_config()
    resposta = pedir(
        "POST", _url("sendMessage"), json={"chatId": CHAT_ID, "message": mensagem}
    )

    if resposta.status_code != 200:
        raise ErroWhatsApp(
            f"Envio recusado (HTTP {resposta.status_code}): {resposta.text[:200]}"
        )

    id_mensagem = resposta.json().get("idMessage")
    if not id_mensagem:
        raise ErroWhatsApp(f"Resposta sem idMessage: {resposta.text[:200]}")

    return id_mensagem


def fixar(id_mensagem):
    """Fixa a mensagem para todos. Uma falha aqui é avisada, não propagada:
    a mensagem já chegou ao grupo, que é o que interessa."""
    try:
        resposta = pedir(
            "POST",
            _url("pinMessage"),
            json={
                "chatId": CHAT_ID,
                "idMessage": id_mensagem,
                "pin": True,
                "pinType": "pinForEveryone",
            },
        )
    except ErroHTTP as erro:
        print(f"Aviso: não foi possível fixar a mensagem: {erro}")
        return False

    if resposta.status_code != 200:
        print(f"Aviso: não foi possível fixar a mensagem: {resposta.text[:200]}")
        return False

    print("Mensagem fixada no grupo.")
    return True


def enviar_e_fixar(mensagem):
    """Envia e fixa. Devolve o idMessage."""
    id_mensagem = enviar(mensagem)
    print("Mensagem enviada.")
    fixar(id_mensagem)
    return id_mensagem
