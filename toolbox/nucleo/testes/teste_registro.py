import json

from toolbox.nucleo.registro import descobrir_apps


def _criar_app(pasta, id_app, **manifesto):
    (pasta / id_app).mkdir()
    (pasta / id_app / "manifesto.json").write_text(json.dumps(manifesto), encoding="utf-8")


def teste_descobre_apps_ordenados(tmp_path):
    _criar_app(tmp_path, "b_app", nome="Beta", ordem=2, tipos_aceitos=["image/*"])
    _criar_app(tmp_path, "a_app", nome="Alfa", ordem=1)
    (tmp_path / "pasta_sem_manifesto").mkdir()

    apps = descobrir_apps(tmp_path)

    assert [app.id for app in apps] == ["a_app", "b_app"]
    assert apps[0].tipos_aceitos == ["*"]
    assert apps[1].tipos_aceitos == ["image/*"]
    assert apps[1].tela == tmp_path / "b_app" / "Tela.qml"
