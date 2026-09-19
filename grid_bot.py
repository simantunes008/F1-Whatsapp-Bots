"""Envia a grelha de partida assim que os resultados da qualificação saem.

Corre de hora a hora de sexta a domingo (ver .github/workflows/grid_bot.yml)
e envia na primeira execução em que a API já tenha os resultados. Antes havia
uma única tentativa ao sábado às 17:00 UTC: se os resultados ainda não
estivessem publicados, a grelha desse fim de semana nunca era enviada, e em
fins de semana sprint (qualificação à sexta) nunca chegava a correr no dia
certo.

A janela válida é entre o início da qualificação e o início da corrida, em
UTC. Comparar a data UTC da API com a data em Lisboa falhava em sessões
nocturnas, em que as duas datas divergem.

O ficheiro de estado evita repetir o envio nas execuções seguintes da mesma
ronda. Se o estado se perder (cache do Actions expirada), o pior caso é uma
mensagem duplicada, não uma mensagem em falta.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import f1_api
import whatsapp

POSICOES = 10
FICHEIRO_ESTADO = Path(os.getenv("GRID_STATE_FILE", ".state/grid_enviados.json"))
RONDAS_GUARDADAS = 5


def _ler_estado():
    if not FICHEIRO_ESTADO.exists():
        return []
    try:
        enviados = json.loads(FICHEIRO_ESTADO.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as erro:
        print(f"Aviso: estado ilegível ({erro}). A tratar como vazio.")
        return []
    return enviados if isinstance(enviados, list) else []


def ja_enviado(chave):
    return chave in _ler_estado()


def marcar_enviado(chave):
    """Grava depois do envio: arriscar um duplicado é melhor do que marcar
    como enviada uma grelha que afinal não chegou ao grupo."""
    enviados = [*_ler_estado(), chave][-RONDAS_GUARDADAS:]
    FICHEIRO_ESTADO.parent.mkdir(parents=True, exist_ok=True)
    FICHEIRO_ESTADO.write_text(json.dumps(enviados), encoding="utf-8")


def instante_utc(sessao, hora_omissao):
    """Converte {'date', 'time'} da API num datetime UTC.

    Nem todas as sessões trazem 'time'. A omissão escolhida por quem chama
    alarga a janela em vez de a fechar: é preferível tentar a mais e falhar
    no passo seguinte do que saltar um envio.
    """
    hora = sessao.get("time") or hora_omissao
    return datetime.strptime(
        f"{sessao['date']}T{hora}", "%Y-%m-%dT%H:%M:%SZ"
    ).replace(tzinfo=timezone.utc)


def construir_mensagem(nome_corrida, resultados):
    mensagem = f"*Grelha de Partida - {nome_corrida}*\n\n"
    for resultado in resultados[:POSICOES]:
        piloto = (
            f"{resultado['Driver']['givenName']} "
            f"{resultado['Driver']['familyName']}"
        )
        mensagem += (
            f"{resultado['position']}. {piloto} "
            f"({resultado['Constructor']['name']})\n"
        )
    return mensagem


def main():
    whatsapp.validar_config()

    corrida = f1_api.proxima_corrida()
    nome = corrida["raceName"]

    if "Qualifying" not in corrida:
        print(f"{nome} não tem qualificação estruturada na API. Nada a fazer.")
        return 0

    inicio_quali = instante_utc(corrida["Qualifying"], "00:00:00Z")
    inicio_corrida = instante_utc(corrida, "23:59:59Z")
    agora = datetime.now(timezone.utc)

    if agora < inicio_quali:
        print(f"A qualificação de {nome} só começa às {inicio_quali:%d/%m %H:%M} UTC.")
        return 0

    if agora >= inicio_corrida:
        print(f"A corrida {nome} já começou. Fora da janela de envio.")
        return 0

    chave = f"{corrida['season']}-{corrida['round']}"
    if ja_enviado(chave):
        print(f"A grelha de {nome} ({chave}) já foi enviada. Nada a fazer.")
        return 0

    resultados = f1_api.resultados_qualificacao(corrida["season"], corrida["round"])
    if not resultados:
        print(
            "Resultados ainda não publicados pela API. "
            "Nova tentativa na próxima execução."
        )
        return 0

    whatsapp.enviar_e_fixar(construir_mensagem(nome, resultados))
    marcar_enviado(chave)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as erro:
        print(f"ERRO: {erro}", file=sys.stderr)
        sys.exit(1)
