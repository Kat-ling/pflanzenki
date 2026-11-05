"""Kept for existing commands; the update logic lives in app.importer.update."""
from app.importer.update import import_notion_zip, main, select_catalog_csv

__all__ = ["import_notion_zip", "main", "select_catalog_csv"]

if __name__ == "__main__":
    raise SystemExit(main())
