import os
from pathlib import Path
import tomllib as toml_loader
from typing import Any, Dict, Iterable, List

PathLike = str | os.PathLike[str]


class Config:
    def __init__(self, data: Dict[str, Any]) -> None:
        self._data = data

    @classmethod
    def from_file(cls, path: PathLike) -> "Config":
        """
        Load configuration data from a TOML file.

        Args:
            path (PathLike): The path to the TOML file.

        Returns:
            Config: An instance of the Config class populated with the data from the file.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        file_path = Path(path).expanduser().resolve()
        if not file_path.is_file():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        with file_path.open("rb") as fp:
            raw: Dict[str, Any] = toml_loader.load(fp)

        return cls(raw)

    def get(self, path: str | Iterable[str], default: Any = None) -> Any:
        keys: List[str] = (
            path.split(".") if isinstance(path, str) else list(path)
        )

        node: Any = self._data
        for k in keys:
            if isinstance(node, dict) and k in node:
                node = node[k]
            else:
                return default
        return node

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __iter__(self):
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.__class__.__name__}({self._data})"
