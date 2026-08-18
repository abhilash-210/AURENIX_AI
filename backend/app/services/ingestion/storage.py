"""
Local disk file storage manager for document ingestion.
"""

from __future__ import annotations

import os
from pathlib import Path
import uuid

from app.config import get_settings
from app.services.ingestion.validators import sanitize_filename


class FileStorageManager:
    """
    Manages local file storage for uploaded documents.
    """

    def __init__(self, base_dir: str | None = None) -> None:
        settings = get_settings()
        self._base_dir = Path(base_dir or settings.upload_dir)

    def save_file(
        self,
        content: bytes,
        original_filename: str,
        document_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> str:
        """
        Save binary file content safely to workspace-isolated disk location.

        Returns:
            Absolute or relative storage path string.
        """
        clean_name = sanitize_filename(original_filename)
        dest_dir = self._base_dir / str(workspace_id)
        dest_dir.mkdir(parents=True, exist_ok=True)

        file_filename = f"{document_id}_{clean_name}"
        dest_path = dest_dir / file_filename

        with open(dest_path, "wb") as f:
            f.write(content)

        return str(dest_path)

    def delete_file(self, storage_path: str) -> bool:
        """Delete file at storage_path if it exists."""
        try:
            p = Path(storage_path)
            if p.exists() and p.is_file():
                p.unlink()
                return True
        except Exception:
            pass
        return False
