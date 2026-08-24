import pytest

from tools import tracer


def collect_words(text):
    return set(text.split())


def test_prints_sorted_deduplicated_classes(monkeypatch, capsys, tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("zeta alpha alpha")
    monkeypatch.setattr("sys.argv", ["demo", str(f)])
    tracer.run(name="demo", doc="demo help", extract=collect_words)
    assert capsys.readouterr().out.splitlines() == ["alpha", "zeta"]


@pytest.mark.parametrize("flag", ["--help", "-h"])
def test_help_flag_prints_doc_and_exits_zero(monkeypatch, capsys, flag):
    monkeypatch.setattr("sys.argv", ["demo", flag])
    with pytest.raises(SystemExit) as exc:
        tracer.run(name="demo", doc="  demo help  ", extract=collect_words)
    assert exc.value.code == 0
    assert capsys.readouterr().out == "demo help\n"


def test_no_arguments_prints_usage_and_exits_one(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["demo"])
    with pytest.raises(SystemExit) as exc:
        tracer.run(name="demo", doc="demo help", extract=collect_words)
    assert exc.value.code == 1
    assert capsys.readouterr().err == "Usage: demo <file>...\n"


def test_missing_file_is_reported_and_others_still_processed(monkeypatch, capsys, tmp_path):
    good = tmp_path / "good.txt"
    good.write_text("real")
    missing = tmp_path / "nope.txt"
    monkeypatch.setattr("sys.argv", ["demo", str(missing), str(good)])
    with pytest.raises(SystemExit) as exc:
        tracer.run(name="demo", doc="demo help", extract=collect_words)
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert captured.out.splitlines() == ["real"]
    assert captured.err == f"demo: {missing}: No such file\n"


def test_directory_is_reported(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr("sys.argv", ["demo", str(tmp_path)])
    with pytest.raises(SystemExit) as exc:
        tracer.run(name="demo", doc="demo help", extract=collect_words)
    assert exc.value.code == 1
    assert capsys.readouterr().err == f"demo: {tmp_path}: Is a directory\n"


def test_non_utf8_file_is_reported(monkeypatch, capsys, tmp_path):
    blob = tmp_path / "blob.txt"
    blob.write_bytes(b"\xff\xfereal")
    monkeypatch.setattr("sys.argv", ["demo", str(blob)])
    with pytest.raises(SystemExit) as exc:
        tracer.run(name="demo", doc="demo help", extract=collect_words)
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert err == f"demo: {blob}: Not valid UTF-8 text (binary file?)\n"


def test_errno_less_oserror_is_reported_by_message(monkeypatch, capsys, tmp_path):
    target = tmp_path / "blocked.txt"
    target.write_text("real")

    def boom(*args, **kwargs):
        raise OSError("simulated read failure")

    monkeypatch.setattr("builtins.open", boom)
    monkeypatch.setattr("sys.argv", ["demo", str(target)])
    with pytest.raises(SystemExit) as exc:
        tracer.run(name="demo", doc="demo help", extract=collect_words)
    assert exc.value.code == 1
    assert capsys.readouterr().err == f"demo: {target}: simulated read failure\n"


def test_binary_mode_hands_the_extractor_bytes(monkeypatch, capsys, tmp_path):
    f = tmp_path / "a.bin"
    f.write_bytes(b"\xff\xfe")
    seen = []

    def record(source):
        seen.append(source)
        return {"read"}

    monkeypatch.setattr("sys.argv", ["demo", str(f)])
    tracer.run(name="demo", doc="demo help", extract=record, binary=True)
    assert seen == [b"\xff\xfe"]
    assert capsys.readouterr().out.splitlines() == ["read"]
