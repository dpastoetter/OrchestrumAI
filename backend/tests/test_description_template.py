from orchestrumai.description_template import render_description_template


def test_render_builtins() -> None:
    out = render_description_template("Report for {{date}} week {{week}}")
    assert "{{date}}" not in out
    assert "{{week}}" not in out
    assert "Report for" in out


def test_render_custom_vars() -> None:
    out = render_description_template("Hello {{name}}", vars={"name": "Ada"})
    assert out == "Hello Ada"
