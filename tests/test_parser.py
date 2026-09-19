"""Testes do parser do live_bot contra uma captura real da F1.

O formato de f1_live.txt é definido pela F1 e pelo FastF1, não por este
projecto: pode mudar sem aviso e, quando mudou, o bot deixou de enviar
alertas sem dar sinal nenhum. É esse o risco que estes testes cobrem.

Correr com:  python3 tests/test_parser.py
"""

import contextlib
import io
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import live_bot  # noqa: E402

# Antes de tudo o resto: importar whatsapp carrega o .env do projecto, por
# isso qualquer chamada a enviar() mandaria uma mensagem verdadeira para o
# grupo. Aqui só se acumula o que teria sido enviado.
ENVIADOS = []
live_bot.whatsapp.enviar = ENVIADOS.append

FIXTURE = Path(__file__).parent / "f1_live_sample.txt"


def linhas_fixture():
    return FIXTURE.read_text(encoding="utf-8").splitlines()


def registo(topico_procurado):
    for linha in linhas_fixture():
        topico, dados = live_bot.analisar_linha(linha)
        if topico == topico_procurado:
            return dados
    raise AssertionError(f"{topico_procurado} não está na fixture")


def incremental(topico, dados):
    """Reproduz uma actualização ao vivo: o FastF1 escreve o payload como
    dict, ao contrário do snapshot inicial, que o escreve como string JSON."""
    return str([topico, dados, "2026-09-13T13:00:00.000Z"])


def teste_toda_a_captura_e_legivel():
    topicos = [live_bot.analisar_linha(l)[0] for l in linhas_fixture()]
    assert None not in topicos, "há linhas reais que o parser não lê"
    assert {"TrackStatus", "RaceControlMessages"} <= set(topicos)


def teste_snapshot_nao_alerta_retroactivamente():
    """Ligar a meio da sessão não pode despejar o histórico no grupo."""
    ENVIADOS.clear()
    live_bot.tratar_track_status(registo("TrackStatus"), None, True)
    live_bot.tratar_race_control(registo("RaceControlMessages"), set(), True)
    assert ENVIADOS == [], ENVIADOS


def teste_estados_de_pista():
    ENVIADOS.clear()
    estado = "1"
    for codigo in ("4", "4", "2", "6", "5", "1"):
        topico, dados = live_bot.analisar_linha(
            incremental("TrackStatus", {"Status": codigo})
        )
        assert topico == "TrackStatus"
        estado = live_bot.tratar_track_status(dados, estado)

    # O 4 repetido não realerta e o amarelo (2) é ignorado de propósito.
    assert ENVIADOS == [
        "*SAFETY CAR NA PISTA!*",
        "*VIRTUAL SAFETY CAR!*",
        "*BANDEIRA VERMELHA!* Sessão interrompida.",
        "*PISTA LIMPA!* Corrida retomada.",
    ], ENVIADOS


def teste_race_control_filtra_o_que_interessa():
    ENVIADOS.clear()
    vistas = set()
    mensagens = registo("RaceControlMessages")["Messages"]
    # Nas actualizações ao vivo, Messages vem como dict indexado, não lista.
    topico, dados = live_bot.analisar_linha(
        incremental("RaceControlMessages",
                    {"Messages": {str(i): m for i, m in enumerate(mensagens)}})
    )
    assert topico == "RaceControlMessages"
    live_bot.tratar_race_control(dados, vistas)
    live_bot.tratar_race_control(dados, vistas)  # repetido não realerta

    assert len(ENVIADOS) == 2, ENVIADOS
    assert ENVIADOS[0].startswith("*Investigação:*")
    assert ENVIADOS[1].startswith("*Penalização:*")
    # "REVIEWED NO FURTHER INVESTIGATION" contém INVESTIGATION mas não alerta.
    assert not any("NO FURTHER" in m for m in ENVIADOS), ENVIADOS


def teste_linhas_invalidas_nao_rebentam():
    for lixo in ("", "   ", "lixo\n", "[incompleto",
                 "['Topico', 'isto-nao-e-json', '']", "['Topico', 42, '']"):
        assert live_bot.analisar_linha(lixo) == (None, None), repr(lixo)


if __name__ == "__main__":
    testes = [v for k, v in sorted(globals().items()) if k.startswith("teste_")]
    falhas = 0
    for teste in testes:
        try:
            # Os alertas imprimem para stdout; aqui só interessa o veredicto.
            with contextlib.redirect_stdout(io.StringIO()):
                teste()
            print(f"  OK    {teste.__name__}")
        except AssertionError as erro:
            falhas += 1
            print(f"  FALHA {teste.__name__}: {erro}")
    print(f"\n{len(testes) - falhas}/{len(testes)} testes passaram")
    sys.exit(1 if falhas else 0)
