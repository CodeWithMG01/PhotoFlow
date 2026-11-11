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
from photoflow.face_filter import (
    filter_photos_by_faces,
    SUPPORTED_IMAGE_FORMATS,
)


class PhotoFlowApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("PhotoFlow - Converter & Face Filter")
        self.geometry("780x700")
        self.minsize(700, 640)

        # Converter state
        self.conv_source_folder = None
        self.conv_output_folder = None
        self.conv_custom_output = False

        # Face filter state
        self.face_source_folder = None
        self.face_output_folder = None
        self.face_custom_output = False
        self.person_a_path = None
        self.person_b_path = None

        self.events = queue.Queue()
        self.cancel_event = threading.Event()
        self.worker = None
        self.running = False
        self.active_task = None  # "converter" or "face_filter"

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.create_interface()
        self.after(100, self.process_events)

    def create_interface(self):

        # Main wrapper container
        wrapper = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        wrapper.pack(fill="both", expand=True, padx=20, pady=12)

        # Header
        ctk.CTkLabel(
            wrapper,
            text="PhotoFlow",
            font=("Arial", 26, "bold")
        ).pack(anchor="w")

        ctk.CTkLabel(
            wrapper,
            text="High-Fidelity Photo Processing & Smart Face Filtering",
            font=("Arial", 12),
            text_color="gray"
        ).pack(anchor="w", pady=(1, 10))

        # Tabview for switching between tools
        self.tabview = ctk.CTkTabview(wrapper)
        self.tabview.pack(fill="both", expand=True)

        tab_converter = self.tabview.add("HEIC Converter")
        tab_face_filter = self.tabview.add("Face Filter")

        self.setup_converter_tab(tab_converter)
        self.setup_face_filter_tab(tab_face_filter)

    # ==========================================
    # Tab 1: HEIC Converter
    # ==========================================
    def setup_converter_tab(self, tab):
        container = ctk.CTkFrame(tab, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=15, pady=8)

        # 1. Source folder
        ctk.CTkLabel(
            container,
            text="1. Select photo folder",
            font=("Arial", 14, "bold")
        ).pack(anchor="w", pady=(2, 4))

        conv_src_frame = ctk.CTkFrame(container)
        conv_src_frame.pack(fill="x", pady=(0, 8))

        self.conv_source_label = ctk.CTkLabel(
            conv_src_frame,
            text="No folder selected",
            text_color="gray",
            anchor="w"
        )
        self.conv_source_label.pack(side="left", padx=10, pady=6, fill="x", expand=True)

        self.conv_browse_src_btn = ctk.CTkButton(
            conv_src_frame,
            text="Browse",
            width=80,
            height=28,
            command=self.select_conv_source
        )
        self.conv_browse_src_btn.pack(side="right", padx=8, pady=4)

        # 2. Output location
        ctk.CTkLabel(
            container,
            text="2. Output location",
            font=("Arial", 14, "bold")
        ).pack(anchor="w", pady=(2, 4))

        conv_out_frame = ctk.CTkFrame(container)
        conv_out_frame.pack(fill="x", pady=(0, 8))

        self.conv_output_label = ctk.CTkLabel(
            conv_out_frame,
            text="Default: Converted_JPG (inside source folder)",
            text_color="gray",
            anchor="w"
        )
        self.conv_output_label.pack(side="left", padx=10, pady=6, fill="x", expand=True)

        self.conv_browse_out_btn = ctk.CTkButton(
            conv_out_frame,
            text="Browse",
            width=80,
            height=28,
            command=self.select_conv_output
        )
        self.conv_browse_out_btn.pack(side="right", padx=8, pady=4)

        # 3. Quality selection
        ctk.CTkLabel(
            container,
            text="3. JPG image quality (4:4:4 color preservation)",
            font=("Arial", 14, "bold")
        ).pack(anchor="w", pady=(2, 4))

        quality_frame = ctk.CTkFrame(container, fg_color="transparent")
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
        self.quality_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.quality_label = ctk.CTkLabel(
            quality_frame,
            text="95%",
            width=45,
            font=("Arial", 12, "bold")
        )
        self.quality_label.pack(side="right")

        # 4. Progress
        ctk.CTkLabel(
            container,
            text="4. Conversion progress",
            font=("Arial", 14, "bold")
        ).pack(anchor="w", pady=(2, 4))

        self.conv_progress = ctk.CTkProgressBar(container, height=10)
        self.conv_progress.pack(fill="x", pady=(2, 4))
        self.conv_progress.set(0)

        self.conv_status_label = ctk.CTkLabel(
            container,
            text="Ready to convert your photos",
            text_color="gray"
        )
        self.conv_status_label.pack(anchor="w", pady=(0, 8))

        # Action buttons
        conv_btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        conv_btn_frame.pack(fill="x", pady=(2, 8))

        self.conv_start_btn = ctk.CTkButton(
            conv_btn_frame,
            text="CONVERT PHOTOS",
            height=38,
            font=("Arial", 13, "bold"),
            command=self.start_conversion
        )
        self.conv_start_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.conv_cancel_btn = ctk.CTkButton(
            conv_btn_frame,
            text="CANCEL",
            height=38,
            width=90,
            fg_color="#555555",
            hover_color="#777777",
            command=self.cancel_task,
            state="disabled"
        )
        self.conv_cancel_btn.pack(side="right")

        ctk.CTkLabel(
            container,
            text="Original photos, EXIF metadata, Display P3 ICC profiles, and timestamps are fully preserved.",
            text_color="gray",
            font=("Arial", 10)
        ).pack(pady=(2, 0))

    # ==========================================
    # Tab 2: Face Filter
    # ==========================================
    def setup_face_filter_tab(self, tab):
        container = ctk.CTkFrame(tab, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=15, pady=8)

        # 1. Source photo folder
        ctk.CTkLabel(
            container,
            text="1. Select photo collection to scan",
            font=("Arial", 14, "bold")
        ).pack(anchor="w", pady=(2, 4))

        face_src_frame = ctk.CTkFrame(container)
        face_src_frame.pack(fill="x", pady=(0, 8))

        self.face_src_label = ctk.CTkLabel(
            face_src_frame,
            text="No folder selected",
            text_color="gray",
            anchor="w"
        )
        self.face_src_label.pack(side="left", padx=10, pady=6, fill="x", expand=True)

        self.face_browse_src_btn = ctk.CTkButton(
            face_src_frame,
            text="Browse",
            width=80,
            height=28,
            command=self.select_face_source
        )
        self.face_browse_src_btn.pack(side="right", padx=8, pady=4)

        # 2. Reference photos (Person A & Person B)
        ctk.CTkLabel(
            container,
            text="2. Select reference photos of faces to identify",
            font=("Arial", 14, "bold")
        ).pack(anchor="w", pady=(2, 4))

        ref_frame = ctk.CTkFrame(container)
        ref_frame.pack(fill="x", pady=(0, 8))

        # Person A
        p1_subframe = ctk.CTkFrame(ref_frame, fg_color="transparent")
        p1_subframe.pack(fill="x", padx=8, pady=4)

        ctk.CTkLabel(p1_subframe, text="Person 1:", width=70, font=("Arial", 12, "bold"), anchor="w").pack(side="left")
        self.person_a_label = ctk.CTkLabel(p1_subframe, text="No reference photo selected (Required)", text_color="gray", anchor="w")
        self.person_a_label.pack(side="left", padx=6, fill="x", expand=True)

        self.person_a_btn = ctk.CTkButton(p1_subframe, text="Choose", width=75, height=26, command=self.select_person_a)
        self.person_a_btn.pack(side="right")

        # Person B
        p2_subframe = ctk.CTkFrame(ref_frame, fg_color="transparent")
        p2_subframe.pack(fill="x", padx=8, pady=(0, 6))

        ctk.CTkLabel(p2_subframe, text="Person 2:", width=70, font=("Arial", 12, "bold"), anchor="w").pack(side="left")
        self.person_b_label = ctk.CTkLabel(p2_subframe, text="No reference photo selected (Optional)", text_color="gray", anchor="w")
        self.person_b_label.pack(side="left", padx=6, fill="x", expand=True)

        self.person_b_btn = ctk.CTkButton(p2_subframe, text="Choose", width=75, height=26, command=self.select_person_b)
        self.person_b_btn.pack(side="right")

        # 3. Output destination & mode
        ctk.CTkLabel(
            container,
            text="3. Output destination & action",
            font=("Arial", 14, "bold")
        ).pack(anchor="w", pady=(2, 4))

        face_out_frame = ctk.CTkFrame(container)
        face_out_frame.pack(fill="x", pady=(0, 6))

        self.face_out_label = ctk.CTkLabel(
            face_out_frame,
            text="Default: Filtered_Photos (inside source folder)",
            text_color="gray",
            anchor="w"
        )
        self.face_out_label.pack(side="left", padx=10, pady=6, fill="x", expand=True)

        self.face_browse_out_btn = ctk.CTkButton(
            face_out_frame,
            text="Browse",
            width=80,
            height=28,
            command=self.select_face_output
        )
        self.face_browse_out_btn.pack(side="right", padx=8, pady=4)

        # Action mode (copy vs separate)
        mode_frame = ctk.CTkFrame(container, fg_color="transparent")
        mode_frame.pack(fill="x", pady=(0, 6))

        self.face_action_var = ctk.StringVar(value="copy")

        r1 = ctk.CTkRadioButton(
            mode_frame,
            text="Copy matched photos (Safest - originals untouched)",
            variable=self.face_action_var,
            value="copy"
        )
        r1.pack(side="left", padx=(0, 15))

        r2 = ctk.CTkRadioButton(
            mode_frame,
            text="Separate (Matched -> Matched_Photos, Others -> Other_Photos)",
            variable=self.face_action_var,
            value="separate"
        )
        r2.pack(side="left")

        # 4. Progress
        ctk.CTkLabel(
            container,
            text="4. Filter progress",
            font=("Arial", 14, "bold")
        ).pack(anchor="w", pady=(2, 4))

        self.face_progress = ctk.CTkProgressBar(container, height=10)
        self.face_progress.pack(fill="x", pady=(2, 4))
        self.face_progress.set(0)

        self.face_status_label = ctk.CTkLabel(
            container,
            text="Ready to filter photos by face",
            text_color="gray"
        )
        self.face_status_label.pack(anchor="w", pady=(0, 8))

        # Action buttons
        face_btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        face_btn_frame.pack(fill="x", pady=(2, 6))

        self.face_start_btn = ctk.CTkButton(
            face_btn_frame,
            text="FILTER PHOTOS BY FACE",
            height=38,
            font=("Arial", 13, "bold"),
            command=self.start_face_filtering
        )
        self.face_start_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.face_cancel_btn = ctk.CTkButton(
            face_btn_frame,
            text="CANCEL",
            height=38,
            width=90,
            fg_color="#555555",
            hover_color="#777777",
            command=self.cancel_task,
            state="disabled"
        )
        self.face_cancel_btn.pack(side="right")

        ctk.CTkLabel(
            container,
            text="Matches Person 1 alone, Person 2 alone, both together, or either in group photos.",
            text_color="gray",
            font=("Arial", 10)
        ).pack(pady=(2, 0))

    # ==========================================
    # Converter Callbacks
    # ==========================================
    def update_quality(self, value):
        self.quality_label.configure(text=f"{int(value)}%")

    def select_conv_source(self):
        if self.running:
            return
        folder = filedialog.askdirectory(title="Select folder containing HEIC/HEIF photos")
        if not folder:
            return
        self.conv_source_folder = Path(folder)
        if not self.conv_custom_output:
            self.conv_output_folder = self.conv_source_folder / "Converted_JPG"
            self.conv_output_label.configure(text=str(self.conv_output_folder))
        self.conv_source_label.configure(text=str(self.conv_source_folder))
        self.conv_status_label.configure(text="Folder selected. Ready to convert.")

    def select_conv_output(self):
        if self.running:
            return
        folder = filedialog.askdirectory(title="Select output folder for converted JPGs")
        if not folder:
            return
        self.conv_output_folder = Path(folder)
        self.conv_custom_output = True
        self.conv_output_label.configure(text=str(self.conv_output_folder))

    def start_conversion(self):
        if self.running:
            return
        if not self.conv_source_folder:
            messagebox.showwarning("Select a folder", "Please select your photo folder first.")
            return
        if not self.conv_output_folder:
            self.conv_output_folder = self.conv_source_folder / "Converted_JPG"

        if self.conv_source_folder == self.conv_output_folder or self.conv_output_folder in self.conv_source_folder.parents:
            messagebox.showerror("Invalid output folder", "Output folder cannot be the source folder or a parent directory.")
            return

        self.running = True
        self.active_task = "converter"
        self.cancel_event.clear()

        self.conv_start_btn.configure(state="disabled")
        self.conv_browse_src_btn.configure(state="disabled")
        self.conv_browse_out_btn.configure(state="disabled")
        self.conv_cancel_btn.configure(state="normal")

        self.conv_progress.set(0)
        self.conv_status_label.configure(text="Scanning photos...")

        quality = int(self.quality_slider.get())

        self.worker = threading.Thread(
            target=self.run_conversion_worker,
            args=(quality,),
            daemon=True
        )
        self.worker.start()

    def run_conversion_worker(self, quality):
        try:
            results = convert_folder(
                self.conv_source_folder,
                self.conv_output_folder,
                quality=quality,
                progress_callback=lambda cur, tot: self.events.put(("conv_progress", cur, tot)),
                cancel_event=self.cancel_event
            )
            self.events.put(("conv_finished", results))
        except Exception as error:
            self.events.put(("error", str(error)))

    # ==========================================
    # Face Filter Callbacks
    # ==========================================
    def select_face_source(self):
        if self.running:
            return
        folder = filedialog.askdirectory(title="Select photo collection folder to scan")
        if not folder:
            return
        self.face_source_folder = Path(folder)
        if not self.face_custom_output:
            self.face_output_folder = self.face_source_folder / "Filtered_Photos"
            self.face_out_label.configure(text=str(self.face_output_folder))
        self.face_src_label.configure(text=str(self.face_source_folder))
        self.face_status_label.configure(text="Collection selected. Choose reference faces.")

    def select_face_output(self):
        if self.running:
            return
        folder = filedialog.askdirectory(title="Select output folder for filtered photos")
        if not folder:
            return
        self.face_output_folder = Path(folder)
        self.face_custom_output = True
        self.face_out_label.configure(text=str(self.face_output_folder))

    def select_person_a(self):
        if self.running:
            return
        file_path = filedialog.askopenfilename(
            title="Select clear reference photo of Person 1",
            filetypes=[("Image files", "*.jpg;*.jpeg;*.heic;*.heif;*.hif;*.png;*.webp;*.bmp")]
        )
        if file_path:
            self.person_a_path = Path(file_path)
            self.person_a_label.configure(text=self.person_a_path.name, text_color="white")

    def select_person_b(self):
        if self.running:
            return
        file_path = filedialog.askopenfilename(
            title="Select clear reference photo of Person 2",
            filetypes=[("Image files", "*.jpg;*.jpeg;*.heic;*.heif;*.hif;*.png;*.webp;*.bmp")]
        )
        if file_path:
            self.person_b_path = Path(file_path)
            self.person_b_label.configure(text=self.person_b_path.name, text_color="white")

    def start_face_filtering(self):
        if self.running:
            return

        if not self.face_source_folder:
            messagebox.showwarning("Select photo folder", "Please select your photo collection folder first.")
            return

        if not self.person_a_path or not self.person_a_path.is_file():
            messagebox.showwarning("Reference photo needed", "Please choose at least a reference photo for Person 1.")
            return

        if not self.face_output_folder:
            self.face_output_folder = self.face_source_folder / "Filtered_Photos"

        self.running = True
        self.active_task = "face_filter"
        self.cancel_event.clear()

        self.face_start_btn.configure(state="disabled")
        self.face_browse_src_btn.configure(state="disabled")
        self.face_browse_out_btn.configure(state="disabled")
        self.person_a_btn.configure(state="disabled")
        self.person_b_btn.configure(state="disabled")
        self.face_cancel_btn.configure(state="normal")

        self.face_progress.set(0)
        self.face_status_label.configure(text="Initializing face recognition engine...")

        action = self.face_action_var.get()

        self.worker = threading.Thread(
            target=self.run_face_worker,
            args=(action,),
            daemon=True
        )
        self.worker.start()

    def run_face_worker(self, action):
        try:
            results = filter_photos_by_faces(
                source_folder=self.face_source_folder,
                output_folder=self.face_output_folder,
                person_a_ref=self.person_a_path,
                person_b_ref=self.person_b_path,
                action=action,
                progress_callback=lambda cur, tot, txt: self.events.put(("face_progress", cur, tot, txt)),
                cancel_event=self.cancel_event
            )
            self.events.put(("face_finished", results))
        except Exception as error:
            self.events.put(("error", str(error)))

    # ==========================================
    # Global Task Management & Event Loop
    # ==========================================
    def cancel_task(self):
        if self.running:
            self.cancel_event.set()
            if self.active_task == "converter":
                self.conv_cancel_btn.configure(state="disabled")
                self.conv_status_label.configure(text="Cancelling conversion...")
            elif self.active_task == "face_filter":
                self.face_cancel_btn.configure(state="disabled")
                self.face_status_label.configure(text="Cancelling face filtering...")

    def process_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                ev_type = event[0]

                if ev_type == "conv_progress":
                    current, total = event[1], event[2]
                    self.conv_progress.set(current / total if total else 0)
                    self.conv_status_label.configure(text=f"Converting {current:,} of {total:,} photos...")

                elif ev_type == "conv_finished":
                    self.show_conv_results(event[1])

                elif ev_type == "face_progress":
                    current, total, text = event[1], event[2], event[3]
                    self.face_progress.set(current / total if total else 0)
                    self.face_status_label.configure(text=text)

                elif ev_type == "face_finished":
                    self.show_face_results(event[1])

                elif ev_type == "error":
                    self.finish_all_ui()
                    messagebox.showerror("Error", event[1])

        except queue.Empty:
            pass

        self.after(100, self.process_events)

    def finish_all_ui(self):
        self.running = False
        self.active_task = None

        # Reset converter UI
        self.conv_start_btn.configure(state="normal")
        self.conv_browse_src_btn.configure(state="normal")
        self.conv_browse_out_btn.configure(state="normal")
        self.conv_cancel_btn.configure(state="disabled")

        # Reset face filter UI
        self.face_start_btn.configure(state="normal")
        self.face_browse_src_btn.configure(state="normal")
        self.face_browse_out_btn.configure(state="normal")
        self.person_a_btn.configure(state="normal")
        self.person_b_btn.configure(state="normal")
        self.face_cancel_btn.configure(state="disabled")

    def show_conv_results(self, results):
        self.finish_all_ui()
        total, converted, failed, cancelled = results["total"], results["converted"], results["failed"], results["cancelled"]

        if total:
            self.conv_progress.set((converted + failed) / total)

        status_text = "Conversion cancelled." if cancelled else "Conversion completed successfully!"
        self.conv_status_label.configure(text=status_text)

        summary = (
            f"Photos found: {total:,}\n"
            f"Successfully converted: {converted:,}\n"
            f"Failed: {failed:,}\n"
            f"Cancelled: {'Yes' if cancelled else 'No'}\n\n"
            f"Output folder:\n{self.conv_output_folder}"
        )
        if results["errors"]:
            summary += "\n\nFirst errors:\n" + "\n".join(results["errors"][:5])

        if not cancelled and failed == 0:
            messagebox.showinfo("PhotoFlow - Complete", summary)
        else:
            messagebox.showwarning("PhotoFlow - Results", summary)

    def show_face_results(self, results):
        self.finish_all_ui()
        total = results["total"]
        matched = results["matched"]
        unmatched = results["unmatched"]
        cancelled = results["cancelled"]

        if total:
            self.face_progress.set((matched + unmatched) / total)

        status_text = "Filtering cancelled." if cancelled else "Face filtering complete!"
        self.face_status_label.configure(text=status_text)

        summary = (
            f"Total photos scanned: {total:,}\n"
            f"Matched photos kept: {matched:,}\n"
            f"  • Person 1 photos: {results['person_a_count']:,}\n"
            f"  • Person 2 photos: {results['person_b_count']:,}\n"
            f"  • Photos with both: {results['both_count']:,}\n"
            f"Non-matching photos: {unmatched:,}\n"
            f"Cancelled: {'Yes' if cancelled else 'No'}\n\n"
            f"Output destination:\n{self.face_output_folder}"
        )
        if results["errors"]:
            summary += "\n\nErrors encountered:\n" + "\n".join(results["errors"][:5])

        messagebox.showinfo("PhotoFlow - Face Filter Complete", summary)


if __name__ == "__main__":
    app = PhotoFlowApp()
    app.mainloop()
