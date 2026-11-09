import threading
import queue
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from photoflow.converter import (
    convert_folder,
    find_heic_files,
    PHOTO_EXTENSIONS,
    SUPPORTED_FORMATS,
)


class PhotoFlowApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("PhotoFlow - HEIC Converter")
        self.geometry("740x620")
        self.minsize(650, 595)

        self.source_folder = None
        self.output_folder = None
        self.custom_output = False

        self.events = queue.Queue()
        self.cancel_event = threading.Event()
        self.worker = None
        self.running = False

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.create_interface()
        self.after(100, self.process_events)

    def create_interface(self):

        # Main non-scrollable container
        container = ctk.CTkFrame(
            self,
            corner_radius=0,
            fg_color="transparent"
        )
        container.pack(
            fill="both",
            expand=True,
            padx=25,
            pady=15
        )

        # Application title
        ctk.CTkLabel(
            container,
            text="PhotoFlow",
            font=("Arial", 26, "bold")
        ).pack(anchor="w")

        ctk.CTkLabel(
            container,
            text="High-Fidelity HEIC / HEIF / HIF to JPG Converter",
            font=("Arial", 12),
            text_color="gray"
        ).pack(anchor="w", pady=(1, 10))

        # 1. Source folder
        ctk.CTkLabel(
            container,
            text="1. Select photo folder",
            font=("Arial", 14, "bold")
        ).pack(anchor="w", pady=(2, 4))

        source_frame = ctk.CTkFrame(container)
        source_frame.pack(fill="x", pady=(0, 8))

        self.source_label = ctk.CTkLabel(
            source_frame,
            text="No folder selected",
            text_color="gray",
            anchor="w"
        )
        self.source_label.pack(
            side="left",
            padx=12,
            pady=8,
            fill="x",
            expand=True
        )

        self.browse_source_button = ctk.CTkButton(
            source_frame,
            text="Browse",
            width=85,
            height=30,
            command=self.select_source
        )
        self.browse_source_button.pack(
            side="right",
            padx=8,
            pady=6
        )

        # 2. Output location
        ctk.CTkLabel(
            container,
            text="2. Output location",
            font=("Arial", 14, "bold")
        ).pack(anchor="w", pady=(2, 4))

        output_frame = ctk.CTkFrame(container)
        output_frame.pack(fill="x", pady=(0, 8))

        self.output_label = ctk.CTkLabel(
            output_frame,
            text="Default: Converted_JPG (inside source folder)",
            text_color="gray",
            anchor="w"
        )
        self.output_label.pack(
            side="left",
            padx=12,
            pady=8,
            fill="x",
            expand=True
        )

        self.browse_output_button = ctk.CTkButton(
            output_frame,
            text="Browse",
            width=85,
            height=30,
            command=self.select_output
        )
        self.browse_output_button.pack(
            side="right",
            padx=8,
            pady=6
        )

        # 3. Quality selection
        ctk.CTkLabel(
            container,
            text="3. JPG image quality (4:4:4 color preservation)",
            font=("Arial", 14, "bold")
        ).pack(anchor="w", pady=(2, 4))

        quality_frame = ctk.CTkFrame(
            container,
            fg_color="transparent"
        )
        quality_frame.pack(fill="x", pady=(0, 8))

        self.quality_slider = ctk.CTkSlider(
            quality_frame,
            from_=50,
            to=100,
            number_of_steps=50,
            height=18,
            command=self.update_quality
        )
        self.quality_slider.set(95)
        self.quality_slider.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 12)
        )

        self.quality_label = ctk.CTkLabel(
            quality_frame,
            text="95%",
            width=48,
            font=("Arial", 13, "bold")
        )
        self.quality_label.pack(side="right")

        # 4. Progress
        ctk.CTkLabel(
            container,
            text="4. Conversion progress",
            font=("Arial", 14, "bold")
        ).pack(anchor="w", pady=(2, 4))

        self.progress = ctk.CTkProgressBar(container, height=12)
        self.progress.pack(fill="x", pady=(2, 4))
        self.progress.set(0)

        self.status_label = ctk.CTkLabel(
            container,
            text="Ready to convert your photos",
            text_color="gray"
        )
        self.status_label.pack(anchor="w", pady=(0, 8))

        # Action buttons
        button_frame = ctk.CTkFrame(
            container,
            fg_color="transparent"
        )
        button_frame.pack(fill="x", pady=(4, 8))

        self.convert_button = ctk.CTkButton(
            button_frame,
            text="CONVERT PHOTOS",
            height=40,
            font=("Arial", 13, "bold"),
            command=self.start_conversion
        )
        self.convert_button.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 8)
        )

        self.cancel_button = ctk.CTkButton(
            button_frame,
            text="CANCEL",
            height=40,
            width=100,
            fg_color="#555555",
            hover_color="#777777",
            command=self.cancel_conversion,
            state="disabled"
        )
        self.cancel_button.pack(side="right")

        # Footer note
        ctk.CTkLabel(
            container,
            text="Original photos, EXIF metadata, ICC color profiles and timestamps are fully preserved.",
            text_color="gray",
            font=("Arial", 10)
        ).pack(pady=(2, 0))

    def update_quality(self, value):
        self.quality_label.configure(
            text=f"{int(value)}%"
        )

    def select_source(self):
        if self.running:
            return

        folder = filedialog.askdirectory(
            title="Select folder containing HEIC/HEIF photos"
        )

        if not folder:
            return

        self.source_folder = Path(folder)

        if not self.custom_output:
            self.output_folder = self.source_folder / "Converted_JPG"
            self.output_label.configure(
                text=str(self.output_folder)
            )

        self.source_label.configure(
            text=str(self.source_folder)
        )

        self.status_label.configure(
            text="Folder selected. Ready to convert."
        )

    def select_output(self):
        if self.running:
            return

        folder = filedialog.askdirectory(
            title="Select output folder for converted JPGs"
        )

        if not folder:
            return

        self.output_folder = Path(folder)
        self.custom_output = True
        self.output_label.configure(
            text=str(self.output_folder)
        )

    def start_conversion(self):
        if self.running:
            return

        if not self.source_folder:
            messagebox.showwarning(
                "Select a folder",
                "Please select your photo folder first."
            )
            return

        if not self.output_folder:
            self.output_folder = self.source_folder / "Converted_JPG"

        if self.source_folder == self.output_folder or self.output_folder in self.source_folder.parents:
            messagebox.showerror(
                "Invalid output folder",
                "Output folder cannot be the source folder or a parent directory."
            )
            return

        self.running = True
        self.cancel_event.clear()

        self.convert_button.configure(state="disabled")
        self.browse_source_button.configure(state="disabled")
        self.browse_output_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")

        self.progress.set(0)
        self.status_label.configure(text="Scanning photos...")

        quality = int(self.quality_slider.get())

        self.worker = threading.Thread(
            target=self.run_conversion,
            args=(quality,),
            daemon=True
        )
        self.worker.start()

    def run_conversion(self, quality):
        try:
            results = convert_folder(
                self.source_folder,
                self.output_folder,
                quality=quality,
                progress_callback=self.report_progress,
                cancel_event=self.cancel_event
            )
            self.events.put(("finished", results))
        except Exception as error:
            self.events.put(("error", str(error)))

    def report_progress(self, current, total):
        self.events.put(("progress", current, total))

    def cancel_conversion(self):
        if self.running:
            self.cancel_event.set()
            self.cancel_button.configure(state="disabled")
            self.status_label.configure(
                text="Cancelling conversion..."
            )

    def process_events(self):
        try:
            while True:
                event = self.events.get_nowait()

                if event[0] == "progress":
                    current, total = event[1], event[2]
                    self.progress.set(
                        current / total if total else 0
                    )
                    self.status_label.configure(
                        text=f"Converting {current:,} of {total:,} photos..."
                    )

                elif event[0] == "finished":
                    self.show_results(event[1])

                elif event[0] == "error":
                    self.finish_ui()
                    messagebox.showerror(
                        "Conversion error",
                        event[1]
                    )

        except queue.Empty:
            pass

        self.after(100, self.process_events)

    def finish_ui(self):
        self.running = False
        self.convert_button.configure(state="normal")
        self.browse_source_button.configure(state="normal")
        self.browse_output_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")

    def show_results(self, results):
        self.finish_ui()

        total = results["total"]
        converted = results["converted"]
        failed = results["failed"]
        cancelled = results["cancelled"]

        if total:
            self.progress.set(
                (converted + failed) / total
            )

        if cancelled:
            self.status_label.configure(
                text="Conversion cancelled."
            )
        else:
            self.status_label.configure(
                text="Conversion completed successfully!"
            )

        summary = (
            f"Photos found: {total:,}\n"
            f"Successfully converted: {converted:,}\n"
            f"Failed: {failed:,}\n"
            f"Cancelled: {'Yes' if cancelled else 'No'}\n\n"
            f"Output folder:\n{self.output_folder}"
        )

        if results["errors"]:
            summary += "\n\nFirst errors:\n"
            summary += "\n".join(results["errors"][:5])

        if not cancelled and failed == 0:
            messagebox.showinfo("PhotoFlow - Complete", summary)
        else:
            messagebox.showwarning("PhotoFlow - Results", summary)


if __name__ == "__main__":
    app = PhotoFlowApp()
    app.mainloop()
