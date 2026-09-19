"""Acesso à API Jolpica (compatível com Ergast)."""

from http_client import obter_json

BASE = "https://api.jolpi.ca/ergast/f1"


class SemDados(Exception):
    """A API respondeu, mas sem os dados pedidos."""


def proxima_corrida():
    """Devolve o dicionário da próxima corrida do calendário em curso."""
    dados = obter_json(f"{BASE}/current/next.json")
    corridas = dados["MRData"]["RaceTable"]["Races"]
    if not corridas:
        raise SemDados("A API não devolveu nenhuma próxima corrida.")
    return corridas[0]


def resultados_qualificacao(epoca, ronda):
    """Devolve os QualifyingResults, ou None se ainda não estiverem publicados.

    A distinção importa: None é uma situação normal (a qualificação acabou de
    terminar) e não deve ser tratada como erro.
    """
    dados = obter_json(f"{BASE}/{epoca}/{ronda}/qualifying.json")
    corridas = dados["MRData"]["RaceTable"]["Races"]
    if not corridas or "QualifyingResults" not in corridas[0]:
        return None
    return corridas[0]["QualifyingResults"]
