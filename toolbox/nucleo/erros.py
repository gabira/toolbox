"""Exceções compartilhadas pelos serviços dos apps (sem dependência de Qt)."""


class Cancelado(Exception):
    """O usuário cancelou a operação."""


class ErroUsuario(Exception):
    """Falha com mensagem pronta para mostrar na interface."""
