import pytest

from stages.stage1_inventory.scanner import list_files


def test_nested_files_are_relative_with_forward_slashes(tmp_path):
    (tmp_path / "first.txt").write_text("first")
    nested_file = tmp_path / "nested" / "deeper" / "second.txt"
    nested_file.parent.mkdir(parents=True)
    nested_file.write_text("second")

    assert list_files(str(tmp_path)) == ["first.txt", "nested/deeper/second.txt"]


def test_files_inside_git_directory_are_skipped(tmp_path):
    (tmp_path / "visible.txt").write_text("visible")
    git_file = tmp_path / ".git" / "hidden.txt"
    git_file.parent.mkdir()
    git_file.write_text("hidden")

    assert list_files(str(tmp_path)) == ["visible.txt"]


def test_missing_folder_raises_value_error(tmp_path):
    missing_folder = tmp_path / "missing"

    with pytest.raises(ValueError, match=f"Folder not found: {missing_folder}"):
        list_files(str(missing_folder))


def test_result_is_sorted(tmp_path):
    for name in ["z.txt", "a.txt", "m.txt"]:
        (tmp_path / name).write_text(name)

    assert list_files(str(tmp_path)) == ["a.txt", "m.txt", "z.txt"]
