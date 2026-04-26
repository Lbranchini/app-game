"""Testes do carregamento de dados."""

from __future__ import annotations

from agora.schemas import Alvo, Essencia, Personagem, TipoEfeito, TipoHabilidade


def test_carrega_aquiles(aquiles: Personagem) -> None:
    assert aquiles.id == "aquiles"
    assert aquiles.hp_base == 110
    assert len(aquiles.habilidades) == 3

    lanca = aquiles.habilidades[0]
    assert lanca.id == "lanca"
    assert lanca.tipo == TipoHabilidade.INSTANTANEA
    assert lanca.alvo == Alvo.INIMIGO_UNICO
    assert lanca.custo == {Essencia.VIGOR: 1}
    assert lanca.efeitos[0].tipo == TipoEfeito.DANO
    assert lanca.efeitos[0].valor == 20


def test_carrega_atena_egide_em_todos_aliados(atena: Personagem) -> None:
    egide = next(s for s in atena.habilidades if s.id == "egide")
    assert egide.alvo == Alvo.TODOS_ALIADOS
    assert egide.efeitos[0].tipo == TipoEfeito.ESCUDO_DESTRUTIVEL
    assert egide.efeitos[0].valor == 25


def test_anubis_aplica_veneno(anubis: Personagem) -> None:
    bandagens = anubis.habilidades[0]
    veneno = next(e for e in bandagens.efeitos if e.tipo == TipoEfeito.STATUS)
    assert veneno.status == "veneno"
    assert veneno.duracao == 2
    assert veneno.valor == 10
