from stages.stage1_inventory.reader import read_file


def test_utf8_lf_file(tmp_path):
    """Recognize UTF-8 text with LF endings."""
    path = tmp_path / "utf8.txt"
    path.write_bytes("first\nsecond\n".encode("utf-8"))

    result = read_file(str(path))

    assert result.kind == "text"
    assert result.encoding == "utf-8"
    assert result.line_ending == "LF"


def test_crlf_and_mixed_line_endings(tmp_path):
    """Distinguish CRLF and mixed line endings."""
    crlf_path = tmp_path / "crlf.txt"
    mixed_path = tmp_path / "mixed.txt"
    crlf_path.write_bytes(b"first\r\nsecond\r\n")
    mixed_path.write_bytes(b"first\r\nsecond\n")

    assert read_file(str(crlf_path)).line_ending == "CRLF"
    assert read_file(str(mixed_path)).line_ending == "mixed"


def test_nul_byte_is_binary(tmp_path):
    """Classify data containing a NUL byte as binary."""
    path = tmp_path / "binary.bin"
    path.write_bytes(b"text\x00more")

    result = read_file(str(path))

    assert result.kind == "binary"
    assert result.raw_lines == []
    assert result.code_lines == []


def test_ebcdic_fixed_records(tmp_path):
    """Decode EBCDIC records of 80 characters."""
    path = tmp_path / "records.dat"
    original_lines = [
        "000100 IDENTIFICATION DIVISION.",
        "000200 PROGRAM-ID. TESTPGM.",
        "000300 STOP RUN.",
    ]
    data = "".join(line.ljust(80) for line in original_lines).encode("cp037")
    path.write_bytes(data)

    result = read_file(str(path))

    assert result.encoding == "cp037"
    assert len(result.raw_lines) == 3
    assert result.line_ending == "none"
    assert result.raw_lines[0].startswith(original_lines[0])


def test_fixed_format_sequence_numbers_and_comments(tmp_path):
    """Remove fixed-format comments and sequence areas."""
    path = tmp_path / "fixed.cbl"
    lines = [
        "000100 IDENTIFICATION DIVISION.                                         00010000",
        "000200* THIS IS A COMMENT                                               00020000",
        "000300 PROGRAM-ID. TESTPGM.                                             00030000",
        "000400     STOP RUN.                                                    00040000",
    ]
    path.write_bytes("\n".join(lines).encode("utf-8"))

    result = read_file(str(path))

    assert result.source_format == "fixed"
    assert len(result.code_lines) == 3
    assert [line_number for line_number, _ in result.code_lines] == [1, 3, 4]
    assert result.code_lines[0][1].startswith("IDENTIFICATION DIVISION.")
    assert all("00010000" not in line for _, line in result.code_lines)


def test_fixed_format_without_sequence_numbers(tmp_path):
    """Remove fixed-format leading and trailing columns."""
    path = tmp_path / "fixed.txt"
    lines = [
        "       IDENTIFICATION DIVISION.",
        "       PROGRAM-ID. TESTPGM.",
        "       STOP RUN.",
    ]
    path.write_bytes("\n".join(lines).encode("utf-8"))

    result = read_file(str(path))

    assert result.source_format == "fixed"
    assert [line for _, line in result.code_lines] == [
        "IDENTIFICATION DIVISION.",
        "PROGRAM-ID. TESTPGM.",
        "STOP RUN.",
    ]


def test_jcl_uses_free_format_and_skips_comment(tmp_path):
    """Keep JCL statements and skip its comment line."""
    path = tmp_path / "job.txt"
    path.write_bytes(
        b"//JOB1 JOB (ACCT),'TEST'\n//* COMMENT\n//STEP1 EXEC PGM=MYPROG"
    )

    result = read_file(str(path))

    assert result.source_format == "free"
    assert [line_number for line_number, _ in result.code_lines] == [1, 3]


def test_free_format_comments_are_removed(tmp_path):
    """Remove free-format comment lines and trailing comments."""
    path = tmp_path / "free.cbl"
    path.write_bytes(b"*> comment\nDISPLAY 'HELLO'   *> note\nSTOP RUN.")

    result = read_file(str(path))

    assert result.source_format == "free"
    assert [line for _, line in result.code_lines] == ["DISPLAY 'HELLO'", "STOP RUN."]


def test_markdown_prose_uses_free_format(tmp_path):
    """Treat prose lines as free-format text."""
    path = tmp_path / "notes.md"
    path.write_bytes(b"This is a paragraph.\nIt contains useful notes.")

    assert read_file(str(path)).source_format == "free"


def test_empty_file_has_no_lines(tmp_path):
    """Return an empty text result for an empty file."""
    path = tmp_path / "empty.txt"
    path.write_bytes(b"")

    result = read_file(str(path))

    assert result.kind == "text"
    assert result.raw_lines == []
    assert result.code_lines == []
