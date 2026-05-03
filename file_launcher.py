import os
import subprocess


PRESENTATION_EXTENSIONS = {".ppt", ".pptx"}

FILE_DIALOG_TYPES = [
    ("Presentations", "*.pptx *.ppt"),
    ("Documents", "*.docx *.doc *.pdf *.txt *.rtf *.odt"),
    ("Spreadsheets", "*.xlsx *.xls *.csv"),
    ("Images", "*.png *.jpg *.jpeg *.bmp *.gif"),
    ("All Files", "*.*"),
]


def open_document(file_path):
    if not file_path or not os.path.exists(file_path):
        raise RuntimeError("Selected file was not found.")

    extension = os.path.splitext(file_path)[1].lower()

    try:
        if extension in PRESENTATION_EXTENSIONS:
            subprocess.Popen(
                ["cmd", "/c", "start", "", "powerpnt", "/s", file_path],
                shell=False,
            )
            return "ppt_slideshow"

        os.startfile(file_path)
        return "document"
    except FileNotFoundError as exc:
        raise RuntimeError(
            "PowerPoint was not found. Install Microsoft Office or choose another file."
        ) from exc
    except OSError as exc:
        raise RuntimeError(f"Could not open the selected file: {exc}") from exc
