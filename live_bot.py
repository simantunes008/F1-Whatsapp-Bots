"""Alertas em directo durante uma sessão de F1.

Duas metades: uma thread daemon corre o SignalRClient do FastF1, que escreve
as mensagens cruas em f1_live.txt; a thread principal segue o ficheiro e
envia os alertas. O ficheiro é o único canal entre as duas.

Requer subscrição F1TV: o FastF1 autentica-se no arranque (fluxo no browser
na primeira vez, token em cache local depois disso).

Formato do ficheiro: o FastF1 escreve str([topico, dados, timestamp]), um
literal Python e não JSON. Nos snapshots iniciais 'dados' vem como string
JSON; nas actualizações incrementais vem já como dict. É por isso que a
leitura passa por ast.literal_eval e não por json.loads sobre a linha toda.
"""

import ast
import json
import os
import sys
import threading
import time
from pathlib import Path

from fastf1.livetiming.client import SignalRClient

import whatsapp

FICHEIRO_DADOS = Path("f1_live.txt")
FICHEIRO_ANTERIOR = Path("f1_live.prev.txt")

# Códigos de TrackStatus da F1. O amarelo (2) fica deliberadamente de fora:
# em corrida é frequente demais e encheria o grupo. O fim de VSC (7) também,
# porque vem sempre seguido de AllClear (1).
ESTADOS_PISTA = {
    "1": "*PISTA LIMPA!* Corrida retomada.",
    "4": "*SAFETY CAR NA PISTA!*",
    "5": "*BANDEIRA VERMELHA!* Sessão interrompida.",
    "6": "*VIRTUAL SAFETY CAR!*",
}

FILTROS_RACE_CONTROL = (
    ("INVESTIGATION", "Investigação"),
    ("PENALTY", "Penalização"),
)

# "REVIEWED NO FURTHER INVESTIGATION" contém "INVESTIGATION" mas significa
# exactamente o contrário: o caso foi visto e arquivado sem consequências.
EXCLUSOES_RACE_CONTROL = ("NO FURTHER INVESTIGATION",)

INTERVALO_LEITURA = 1
ESPERA_RELIGAR = 15
ARRANQUE_TIMEOUT = 120
# O SignalRClient desliga-se sozinho ao fim de `timeout` segundos sem dados.
# O valor por omissão (60s) mata a ligação enquanto se espera pelo início da
# sessão, por isso é alargado aqui.
TIMEOUT_CLIENTE = int(os.getenv("FASTF1_TIMEOUT", "600"))
AVISO_SEM_DADOS = 300


def preparar_ficheiros():
    """Guarda uma captura anterior de lado antes de começar.

    O cliente escreve em modo append (ver iniciar_cliente), por isso sem isto
    as sessões acumulavam-se todas no mesmo ficheiro: cresceria sem limite e
    deixaria de servir para carregar no LiveTimingData do FastF1, que espera
    uma sessão de cada vez.

    Move em vez de apagar porque a captura anterior é o único dado real
    disponível para validar alterações ao parser — foi dela que saiu a
    fixture em tests/f1_live_sample.txt. Guarda só uma geração.
    """
    if FICHEIRO_DADOS.exists():
        FICHEIRO_DADOS.replace(FICHEIRO_ANTERIOR)
        print(f"Captura anterior guardada em {FICHEIRO_ANTERIOR}.")


def enviar_alerta(mensagem):
    """Um alerta falhado não pode derrubar o monitor a meio da corrida."""
    print(f"ALERTA: {mensagem}")
    try:
        whatsapp.enviar(mensagem)
    except Exception as erro:
        print(f"ERRO ao enviar alerta: {erro}", file=sys.stderr)


def analisar_linha(linha):
    """Devolve (topico, dados) de uma linha crua, ou (None, None) se não der."""
    linha = linha.strip()
    if not linha.startswith("["):
        return None, None

    try:
        registo = ast.literal_eval(linha)
    except (ValueError, SyntaxError, MemoryError, RecursionError):
        return None, None

    if not isinstance(registo, list) or len(registo) < 2:
        return None, None

    topico, dados = registo[0], registo[1]
    if isinstance(dados, str):
        try:
            dados = json.loads(dados)
        except json.JSONDecodeError:
            return None, None

    if not isinstance(dados, dict):
        return None, None
    return topico, dados


def tratar_track_status(dados, estado_anterior, silencioso=False):
    """Envia alerta quando o estado da pista muda. Devolve o novo estado."""
    estado = dados.get("Status")
    if estado is None or estado == estado_anterior:
        return estado_anterior

    if not silencioso:
        alerta = ESTADOS_PISTA.get(str(estado))
        if alerta:
            enviar_alerta(alerta)
    return estado


def tratar_race_control(dados, vistas, silencioso=False):
    mensagens = dados.get("Messages", [])
    # No snapshot inicial 'Messages' é uma lista; nas actualizações
    # incrementais vem como dict indexado por posição.
    if isinstance(mensagens, dict):
        mensagens = list(mensagens.values())

    for mensagem in mensagens:
        if not isinstance(mensagem, dict):
            continue
        texto = (mensagem.get("Message") or "").strip()
        if not texto or texto in vistas:
            continue

        # No snapshot inicial basta registar: alertar seria repetir o que já
        # aconteceu antes de o bot se ligar.
        if silencioso:
            vistas.add(texto)
            continue

        maiusculas = texto.upper()
        if any(excl in maiusculas for excl in EXCLUSOES_RACE_CONTROL):
            vistas.add(texto)
            continue

        for padrao, etiqueta in FILTROS_RACE_CONTROL:
            if padrao in maiusculas:
                enviar_alerta(f"*{etiqueta}:* {texto}")
                vistas.add(texto)
                break


def iniciar_cliente():
    """Mantém a ligação viva: o SignalRClient do FastF1 não se religa sozinho.

    Abre em modo 'a' para que uma religação não trunque o que já foi escrito
    e desalinhe o monitor.
    """
    tentativa = 0
    while True:
        tentativa += 1
        print(f"A ligar aos servidores da F1 (tentativa {tentativa})...")
        try:
            SignalRClient(
                str(FICHEIRO_DADOS), filemode="a", timeout=TIMEOUT_CLIENTE
            ).start()
            print("Ligação terminada pelo servidor.", file=sys.stderr)
        except Exception as erro:
            print(f"ERRO no cliente FastF1: {erro}", file=sys.stderr)
        print(f"A religar dentro de {ESPERA_RELIGAR}s...")
        time.sleep(ESPERA_RELIGAR)


def esperar_ficheiro(thread_cliente):
    limite = time.time() + ARRANQUE_TIMEOUT
    while not FICHEIRO_DADOS.exists():
        if not thread_cliente.is_alive():
            raise RuntimeError(
                "O cliente FastF1 terminou no arranque. Verifica a "
                "autenticação F1TV."
            )
        if time.time() > limite:
            raise RuntimeError(
                f"{FICHEIRO_DADOS} não apareceu em {ARRANQUE_TIMEOUT}s."
            )
        time.sleep(1)


def seguir_ficheiro(thread_cliente):
    """Segue o ficheiro linha a linha e dispara os alertas."""
    estado_pista = None
    vistas = set()
    topicos_vistos = set()
    parcial = ""
    ultimo_dado = time.time()
    ultimo_aviso = 0.0

    with FICHEIRO_DADOS.open("r", encoding="utf-8") as ficheiro:
        ficheiro.seek(0, os.SEEK_END)

        while True:
            pedaco = ficheiro.readline()

            if not pedaco:
                if not thread_cliente.is_alive():
                    print(
                        "A thread do cliente FastF1 morreu. A terminar.",
                        file=sys.stderr,
                    )
                    return 1

                agora = time.time()
                if (agora - ultimo_dado > AVISO_SEM_DADOS
                        and agora - ultimo_aviso > AVISO_SEM_DADOS):
                    minutos = int((agora - ultimo_dado) // 60)
                    print(
                        f"Aviso: sem dados novos há {minutos} minutos. "
                        "A sessão pode ter terminado ou a ligação caiu.",
                        file=sys.stderr,
                    )
                    ultimo_aviso = agora

                time.sleep(INTERVALO_LEITURA)
                continue

            # readline() pode devolver uma linha ainda a ser escrita.
            parcial += pedaco
            if not parcial.endswith("\n"):
                continue
            linha, parcial = parcial, ""

            ultimo_dado = time.time()

            topico, dados = analisar_linha(linha)
            if topico is None:
                continue

            # O primeiro registo de cada tópico é o snapshot com o histórico
            # da sessão até ao momento da ligação. Serve para inicializar o
            # estado, não para alertar retroactivamente.
            snapshot = topico not in topicos_vistos
            topicos_vistos.add(topico)

            if topico == "TrackStatus":
                estado_pista = tratar_track_status(dados, estado_pista, snapshot)
            elif topico == "RaceControlMessages":
                tratar_race_control(dados, vistas, snapshot)


def main():
    whatsapp.validar_config()
    preparar_ficheiros()

    thread_cliente = threading.Thread(target=iniciar_cliente, daemon=True)
    thread_cliente.start()

    print("A aguardar dados do FastF1...")
    esperar_ficheiro(thread_cliente)

    print("A monitorizar a sessão. Ctrl+C para terminar.")
    return seguir_ficheiro(thread_cliente)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nTerminado.")
        sys.exit(0)
    except Exception as erro:
        print(f"ERRO: {erro}", file=sys.stderr)
        sys.exit(1)
