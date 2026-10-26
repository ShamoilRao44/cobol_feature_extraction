import os


def list_files(folder: str) -> list[str]:
    """Return sorted relative paths for files beneath a folder."""
    if not os.path.isdir(folder):
        raise ValueError(f"Folder not found: {folder}")

    paths = []
    for root, directories, filenames in os.walk(folder):
        directories[:] = [
            directory
            for directory in directories
            if directory not in {".git", ".svn", "node_modules", "__pycache__"}
        ]
        for filename in filenames:
            path = os.path.relpath(os.path.join(root, filename), folder)
            paths.append(path.replace(os.sep, "/"))

    return sorted(paths)
