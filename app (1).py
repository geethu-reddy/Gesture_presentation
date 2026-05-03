import os
import queue
import threading
from tkinter import filedialog, messagebox

try:
    import customtkinter as ctk
except ImportError as exc:
    raise SystemExit(
        "Missing dependency: customtkinter. Install it with: pip install customtkinter"
    ) from exc

from file_launcher import FILE_DIALOG_TYPES, open_document
from gesture_controller import GestureController


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

APP_BG = "#1B1D31"
SIDEBAR_BG = "#272A46"
CARD_BG = "#2D3150"
CARD_BG_ALT = "#292D49"
TEXT_PRIMARY = "#F4F7FF"
TEXT_SECONDARY = "#8E97C1"
BLUE_CARD = "#2E7BE6"
GREEN_CARD = "#45A84A"
EXIT_RED = "#E06974"


class GesturePresenterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("GesturePresenter")
        self.geometry("1280x760")
        self.minsize(1120, 680)
        self.configure(fg_color=APP_BG)

        self.file_path = None
        self.controller = None
        self.gesture_thread = None
        self.status_queue = queue.Queue()

        self._build_ui()
        self.after(120, self._poll_status_queue)

    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=250, fg_color=SIDEBAR_BG, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        self.main = ctk.CTkFrame(self, fg_color=APP_BG, corner_radius=0)
        self.main.grid(row=0, column=1, sticky="nsew")

        self._build_sidebar()
        self._build_main()

    def _build_sidebar(self):
        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=22, pady=(34, 22))

        logo_badge = ctk.CTkFrame(
            brand,
            width=66,
            height=66,
            corner_radius=33,
            fg_color=CARD_BG,
        )
        logo_badge.pack(anchor="w")
        logo_badge.pack_propagate(False)

        ctk.CTkLabel(
            logo_badge,
            text="GP",
            font=("Segoe UI Semibold", 24),
            text_color=TEXT_PRIMARY,
        ).pack(expand=True)

        ctk.CTkLabel(
            brand,
            text="GesturePresenter",
            font=("Segoe UI Semibold", 26),
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w", pady=(14, 4))

        ctk.CTkLabel(
            brand,
            text="Control slides with your hands",
            font=("Segoe UI", 16),
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w")

        nav_items = [
            ("  Home", self._home_click),
            ("  Upload File", self.pick_file),
            ("  Start Presenting", self.start_presenting),
            ("  Help", self.show_help),
        ]

        for text, command in nav_items:
            ctk.CTkButton(
                self.sidebar,
                text=text,
                command=command,
                anchor="w",
                height=42,
                corner_radius=10,
                fg_color="transparent",
                hover_color=CARD_BG,
                text_color=TEXT_PRIMARY,
                font=("Segoe UI", 18),
            ).pack(fill="x", padx=16, pady=5)

        ctk.CTkButton(
            self.sidebar,
            text="  Exit",
            command=self.on_close,
            anchor="w",
            height=32,
            corner_radius=10,
            fg_color="transparent",
            hover_color="#3C2531",
            text_color=EXIT_RED,
            font=("Segoe UI", 18),
        ).pack(fill="x", padx=16, pady=(34, 0))

    def _build_main(self):
        container = ctk.CTkFrame(self.main, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=40, pady=28)

        ctk.CTkLabel(
            container,
            text="Welcome",
            font=("Segoe UI Semibold", 30),
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w")

        ctk.CTkLabel(
            container,
            text="Control your presentations with hand gestures - no mouse, no keyboard.",
            font=("Segoe UI", 19),
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w", pady=(4, 22))

        current_file_card = ctk.CTkFrame(container, fg_color=CARD_BG, corner_radius=16)
        current_file_card.pack(fill="x", pady=(0, 26))

        ctk.CTkLabel(
            current_file_card,
            text="Current File",
            font=("Segoe UI Semibold", 18),
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w", padx=26, pady=(16, 4))

        self.file_label = ctk.CTkLabel(
            current_file_card,
            text="No file selected",
            font=("Segoe UI Semibold", 24),
            text_color=TEXT_PRIMARY,
        )
        self.file_label.pack(anchor="w", padx=26, pady=(0, 16))

        ctk.CTkLabel(
            container,
            text="Quick Actions",
            font=("Segoe UI Semibold", 30),
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, 12))

        action_row = ctk.CTkFrame(container, fg_color="transparent")
        action_row.pack(fill="x", pady=(0, 26))
        action_row.grid_columnconfigure((0, 1), weight=1)

        self.upload_button = ctk.CTkButton(
            action_row,
            text="Upload File",
            command=self.pick_file,
            height=68,
            corner_radius=16,
            fg_color=BLUE_CARD,
            hover_color="#2A71D4",
            text_color=TEXT_PRIMARY,
            font=("Segoe UI Semibold", 22),
        )
        self.upload_button.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.start_button = ctk.CTkButton(
            action_row,
            text="Start",
            command=self.start_presenting,
            height=68,
            corner_radius=16,
            fg_color=GREEN_CARD,
            hover_color="#3E9842",
            text_color=TEXT_PRIMARY,
            font=("Segoe UI Semibold", 22),
        )
        self.start_button.grid(row=0, column=1, sticky="ew", padx=(10, 0))

        ctk.CTkLabel(
            container,
            text="Gesture Guide",
            font=("Segoe UI Semibold", 30),
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, 10))

        guide_wrap = ctk.CTkFrame(container, fg_color=CARD_BG_ALT, corner_radius=16)
        guide_wrap.pack(fill="both", expand=True)

        guide_header = ctk.CTkFrame(guide_wrap, fg_color="transparent")
        guide_header.pack(fill="x", padx=24, pady=(14, 4))
        ctk.CTkLabel(
            guide_header,
            text="Gesture",
            width=260,
            anchor="w",
            font=("Segoe UI Semibold", 16),
            text_color=TEXT_SECONDARY,
        ).pack(side="left")
        ctk.CTkLabel(
            guide_header,
            text="Action",
            anchor="w",
            font=("Segoe UI Semibold", 16),
            text_color=TEXT_SECONDARY,
        ).pack(side="left")

        guide_body = ctk.CTkScrollableFrame(guide_wrap, fg_color="transparent")
        guide_body.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        guide_items = [
            ("All Fingers Closed", "Start presentation"),
            ("All Fingers Open", "End presentation"),
            ("Pinky Only", "Next slide"),
            ("Thumb Only", "Previous slide"),
            ("Index Only", "Laser pointer"),
        ]

        for gesture_name, action in guide_items:
            row = ctk.CTkFrame(guide_body, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=6)

            ctk.CTkLabel(
                row,
                text=gesture_name,
                width=260,
                anchor="w",
                font=("Segoe UI Semibold", 18),
                text_color=TEXT_PRIMARY,
            ).pack(side="left")

            ctk.CTkLabel(
                row,
                text="->",
                width=34,
                font=("Segoe UI", 16),
                text_color=TEXT_SECONDARY,
            ).pack(side="left")

            ctk.CTkLabel(
                row,
                text=action,
                anchor="w",
                font=("Segoe UI", 18),
                text_color=TEXT_SECONDARY,
            ).pack(side="left")

        self.status_label = ctk.CTkLabel(
            container,
            text="Status: waiting for a file",
            font=("Consolas", 18),
            text_color=TEXT_SECONDARY,
        )
        self.status_label.pack(anchor="w", pady=(12, 0))

    def _home_click(self):
        self.status_label.configure(text="Status: home")

    def pick_file(self):
        selected = filedialog.askopenfilename(filetypes=FILE_DIALOG_TYPES)
        if not selected:
            return

        self.file_path = selected
        self.file_label.configure(text=os.path.basename(selected))
        self.status_label.configure(text="Status: file selected, ready to start")

    def start_presenting(self):
        if not self.file_path:
            messagebox.showwarning("No File", "Please choose a file first.")
            return

        if self.controller and self.controller.is_running:
            messagebox.showinfo("Already Running", "Gesture control is already active.")
            return

        try:
            launch_mode = open_document(self.file_path)
        except RuntimeError as exc:
            messagebox.showerror("Open Failed", str(exc))
            return

        self.controller = GestureController(
            status_callback=self._queue_status,
            launch_mode=launch_mode,
        )
        self.gesture_thread = threading.Thread(target=self.controller.run, daemon=True)
        self.gesture_thread.start()
        self.status_label.configure(text="Status: file opened. Show fist to start.")

    def _queue_status(self, message):
        self.status_queue.put(message)

    def _poll_status_queue(self):
        while not self.status_queue.empty():
            status = self.status_queue.get_nowait()
            self.status_label.configure(text=f"Status: {status}")
        self.after(120, self._poll_status_queue)

    def show_help(self):
        messagebox.showinfo(
            "Help",
            "1. Upload PPT, Word, PDF, text, image, or spreadsheet file.\n"
            "2. Click Start to open it.\n"
            "3. Show fist gesture to begin control.\n"
            "4. Pinky = next, thumb = previous, index = pointer, open hand = stop.\n\n"
            "Camera preview appears in a small corner window while control is running.\n"
            "If camera does not open, close Zoom/Meet/Teams and retry.",
        )

    def on_close(self):
        if self.controller:
            self.controller.stop()
        self.destroy()


if __name__ == "__main__":
    app = GesturePresenterApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()