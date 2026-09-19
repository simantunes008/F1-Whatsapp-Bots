"""Pedidos HTTP com timeout e retries, partilhados por todos os bots.

Um 500 transitório da Jolpica ou da Green API deixava de perder a mensagem
da semana: os bots agendados só correm em janelas curtas e não há segunda
oportunidade dentro da mesma execução.
"""

import time

import requests

TIMEOUT = 10
TENTATIVAS = 3
ESPERA_BASE = 3


class ErroHTTP(Exception):
    """O pedido falhou depois de esgotadas as tentativas."""


def pedir(metodo, url, **kwargs):
    """Faz um pedido HTTP, repetindo em erros de rede e respostas 5xx.

    As respostas 4xx são devolvidas sem repetição: são erros de configuração
    (token inválido, chat inexistente) que não melhoram com nova tentativa.
    """
    kwargs.setdefault("timeout", TIMEOUT)
    ultimo_erro = None

    for tentativa in range(1, TENTATIVAS + 1):
        try:
            resposta = requests.request(metodo, url, **kwargs)
            if resposta.status_code >= 500:
                raise requests.HTTPError(
                    f"HTTP {resposta.status_code}: {resposta.text[:200]}"
                )
            return resposta
        except requests.RequestException as erro:
            ultimo_erro = erro
            if tentativa < TENTATIVAS:
                espera = ESPERA_BASE * tentativa
                print(
                    f"Tentativa {tentativa}/{TENTATIVAS} falhou ({erro}). "
                    f"A repetir em {espera}s..."
                )
                time.sleep(espera)

    raise ErroHTTP(
        f"{metodo} {url} falhou após {TENTATIVAS} tentativas: {ultimo_erro}"
    )


def obter_json(url, **kwargs):
    """GET que devolve JSON já descodificado."""
    resposta = pedir("GET", url, **kwargs)
    resposta.raise_for_status()
    return resposta.json()
