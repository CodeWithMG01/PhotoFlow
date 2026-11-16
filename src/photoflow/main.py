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
    clean_trip_photos,
    SUPPORTED_IMAGE_FORMATS,
)
from photoflow.organizer import (
    organize_photos_by_date,
    FOLDER_STRUCTURES,
    SUPPORTED_MEDIA_EXTENSIONS,
)
from photoflow.video_converter import (
    convert_video_folder,
    find_mov_files,
    SUPPORTED_VIDEO_INPUTS,
)


class PhotoFlowApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("PhotoFlow - Media Converter, Trip Cleaner & Organizer")
        self.geometry("820x760")
        self.minsize(740, 700)

        # 1. Image converter state
        self.conv_source_folder = None
        self.conv_output_folder = None
        self.conv_custom_output = False

        # 2. Video converter state
        self.vid_source_folder = None
        self.vid_output_folder = None
        self.vid_custom_output = False

        # 3. Face filter state
        self.face_source_folder = None
        self.face_output_folder = None
        self.face_custom_output = False
        self.person_a_path = None
        self.person_b_path = None

        # 4. Date organizer state
        self.org_source_folder = None
        self.org_output_folder = None
        self.org_custom_output = False

        self.events = queue.Queue()
        self.cancel_event = threading.Event()
        self.worker = None
        self.running = False
        self.active_task = None

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.create_interface()
        self.after(100, self.process_events)

    def create_interface(self):
        wrapper = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        wrapper.pack(fill="both", expand=True, padx=20, pady=10)

        # Header
        ctk.CTkLabel(
            wrapper,
            text="PhotoFlow",
            font=("Arial", 26, "bold")
        ).pack(anchor="w")

        ctk.CTkLabel(
            wrapper,
            text="High-Fidelity Image & Video Conversion, Trip Photo Cleaner & Date Organization",
            font=("Arial", 12),
            text_color="gray"
        ).pack(anchor="w", pady=(1, 8))

        # Tabview
        self.tabview = ctk.CTkTabview(wrapper)
        self.tabview.pack(fill="both", expand=True)

        tab_converter = self.tabview.add("HEIC Converter")
        tab_video = self.tabview.add("Video Converter (.mov)")
        tab_face_filter = self.tabview.add("Face Filter & Trip Cleaner")
        tab_organizer = self.tabview.add("Date Organizer")

        self.setup_converter_tab(tab_converter)
        self.setup_video_converter_tab(tab_video)
        self.setup_face_filter_tab(tab_face_filter)
        self.setup_organizer_tab(tab_organizer)

    # ==========================================
    # Tab 1: HEIC Converter
    # ==========================================
    def setup_converter_tab(self, tab):
        container = ctk.CTkFrame(tab, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=15, pady=8)

        ctk.CTkLabel(container, text="1. Select photo folder", font=("Arial", 14, "bold")).pack(anchor="w", pady=(2, 4))
        conv_src_frame = ctk.CTkFrame(container)
        conv_src_frame.pack(fill="x", pady=(0, 8))

        self.conv_source_label = ctk.CTkLabel(conv_src_frame, text="No folder selected", text_color="gray", anchor="w")
        self.conv_source_label.pack(side="left", padx=10, pady=6, fill="x", expand=True)

        self.conv_browse_src_btn = ctk.CTkButton(conv_src_frame, text="Browse", width=80, height=28, command=self.select_conv_source)
        self.conv_browse_src_btn.pack(side="right", padx=8, pady=4)

        ctk.CTkLabel(container, text="2. Output location", font=("Arial", 14, "bold")).pack(anchor="w", pady=(2, 4))
        conv_out_frame = ctk.CTkFrame(container)
        conv_out_frame.pack(fill="x", pady=(0, 8))

        self.conv_output_label = ctk.CTkLabel(conv_out_frame, text="Default: Converted_JPG (inside source folder)", text_color="gray", anchor="w")
        self.conv_output_label.pack(side="left", padx=10, pady=6, fill="x", expand=True)

        self.conv_browse_out_btn = ctk.CTkButton(conv_out_frame, text="Browse", width=80, height=28, command=self.select_conv_output)
        self.conv_browse_out_btn.pack(side="right", padx=8, pady=4)

        ctk.CTkLabel(container, text="3. JPG image quality (4:4:4 color preservation)", font=("Arial", 14, "bold")).pack(anchor="w", pady=(2, 4))
        quality_frame = ctk.CTkFrame(container, fg_color="transparent")
        quality_frame.pack(fill="x", pady=(0, 8))

        self.quality_slider = ctk.CTkSlider(quality_frame, from_=50, to=100, number_of_steps=50, height=18, command=self.update_quality)
        self.quality_slider.set(95)
        self.quality_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.quality_label = ctk.CTkLabel(quality_frame, text="95%", width=45, font=("Arial", 12, "bold"))
        self.quality_label.pack(side="right")

        ctk.CTkLabel(container, text="4. Conversion progress", font=("Arial", 14, "bold")).pack(anchor="w", pady=(2, 4))
        self.conv_progress = ctk.CTkProgressBar(container, height=10)
        self.conv_progress.pack(fill="x", pady=(2, 4))
        self.conv_progress.set(0)

        self.conv_status_label = ctk.CTkLabel(container, text="Ready to convert your photos", text_color="gray")
        self.conv_status_label.pack(anchor="w", pady=(0, 8))

        conv_btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        conv_btn_frame.pack(fill="x", pady=(2, 8))

        self.conv_start_btn = ctk.CTkButton(conv_btn_frame, text="CONVERT PHOTOS", height=38, font=("Arial", 13, "bold"), command=self.start_conversion)
        self.conv_start_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.conv_cancel_btn = ctk.CTkButton(conv_btn_frame, text="CANCEL", height=38, width=90, fg_color="#555555", hover_color="#777777", command=self.cancel_task, state="disabled")
        self.conv_cancel_btn.pack(side="right")

        ctk.CTkLabel(container, text="Original photos, EXIF metadata, Display P3 ICC profiles, and timestamps are fully preserved.", text_color="gray", font=("Arial", 10)).pack(pady=(2, 0))

    # ==========================================
    # Tab 2: Video Converter (.mov -> .mp4)
    # ==========================================
    def setup_video_converter_tab(self, tab):
        container = ctk.CTkFrame(tab, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=15, pady=8)

        ctk.CTkLabel(container, text="1. Select folder containing .mov videos", font=("Arial", 14, "bold")).pack(anchor="w", pady=(2, 4))
        vid_src_frame = ctk.CTkFrame(container)
        vid_src_frame.pack(fill="x", pady=(0, 8))

        self.vid_src_label = ctk.CTkLabel(vid_src_frame, text="No folder selected", text_color="gray", anchor="w")
        self.vid_src_label.pack(side="left", padx=10, pady=6, fill="x", expand=True)

        self.vid_browse_src_btn = ctk.CTkButton(vid_src_frame, text="Browse", width=80, height=28, command=self.select_vid_source)
        self.vid_browse_src_btn.pack(side="right", padx=8, pady=4)

        ctk.CTkLabel(container, text="2. Output location", font=("Arial", 14, "bold")).pack(anchor="w", pady=(2, 4))
        vid_out_frame = ctk.CTkFrame(container)
        vid_out_frame.pack(fill="x", pady=(0, 8))

        self.vid_out_label = ctk.CTkLabel(vid_out_frame, text="Default: Converted_MP4 (inside source folder)", text_color="gray", anchor="w")
        self.vid_out_label.pack(side="left", padx=10, pady=6, fill="x", expand=True)

        self.vid_browse_out_btn = ctk.CTkButton(vid_out_frame, text="Browse", width=80, height=28, command=self.select_vid_output)
        self.vid_browse_out_btn.pack(side="right", padx=8, pady=4)

        ctk.CTkLabel(container, text="3. Target video quality (H.264 / AAC)", font=("Arial", 14, "bold")).pack(anchor="w", pady=(2, 4))
        vid_quality_frame = ctk.CTkFrame(container, fg_color="transparent")
        vid_quality_frame.pack(fill="x", pady=(0, 8))

        self.vid_quality_var = ctk.IntVar(value=20)
        q1 = ctk.CTkRadioButton(vid_quality_frame, text="High Quality (CRF 18)", variable=self.vid_quality_var, value=18)
        q1.pack(side="left", padx=(0, 15))

        q2 = ctk.CTkRadioButton(vid_quality_frame, text="Standard (CRF 20 - Recommended)", variable=self.vid_quality_var, value=20)
        q2.pack(side="left", padx=(0, 15))

        q3 = ctk.CTkRadioButton(vid_quality_frame, text="Smaller Size (CRF 24)", variable=self.vid_quality_var, value=24)
        q3.pack(side="left")

        ctk.CTkLabel(container, text="4. Conversion progress", font=("Arial", 14, "bold")).pack(anchor="w", pady=(2, 4))
        self.vid_progress = ctk.CTkProgressBar(container, height=10)
        self.vid_progress.pack(fill="x", pady=(2, 4))
        self.vid_progress.set(0)

        self.vid_status_label = ctk.CTkLabel(container, text="Ready to convert .mov videos to .mp4", text_color="gray")
        self.vid_status_label.pack(anchor="w", pady=(0, 8))

        vid_btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        vid_btn_frame.pack(fill="x", pady=(2, 8))

        self.vid_start_btn = ctk.CTkButton(vid_btn_frame, text="CONVERT VIDEOS TO MP4", height=38, font=("Arial", 13, "bold"), command=self.start_video_conversion)
        self.vid_start_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.vid_cancel_btn = ctk.CTkButton(vid_btn_frame, text="CANCEL", height=38, width=90, fg_color="#555555", hover_color="#777777", command=self.cancel_task, state="disabled")
        self.vid_cancel_btn.pack(side="right")

        ctk.CTkLabel(container, text="Encodes with H.264 (yuv420p) + AAC for 100% native playback on any Windows laptop without paid extensions.", text_color="gray", font=("Arial", 10)).pack(pady=(2, 0))

    # ==========================================
    # Tab 3: Face Filter & Trip Cleaner
    # ==========================================
    def setup_face_filter_tab(self, tab):
        container = ctk.CTkFrame(tab, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=15, pady=8)

        ctk.CTkLabel(container, text="1. Select photo collection to scan", font=("Arial", 14, "bold")).pack(anchor="w", pady=(2, 4))
        face_src_frame = ctk.CTkFrame(container)
        face_src_frame.pack(fill="x", pady=(0, 6))

        self.face_src_label = ctk.CTkLabel(face_src_frame, text="No folder selected", text_color="gray", anchor="w")
        self.face_src_label.pack(side="left", padx=10, pady=6, fill="x", expand=True)

        self.face_browse_src_btn = ctk.CTkButton(face_src_frame, text="Browse", width=80, height=28, command=self.select_face_source)
        self.face_browse_src_btn.pack(side="right", padx=8, pady=4)

        ctk.CTkLabel(container, text="2. Select reference photos of faces to identify", font=("Arial", 14, "bold")).pack(anchor="w", pady=(2, 4))
        ref_frame = ctk.CTkFrame(container)
        ref_frame.pack(fill="x", pady=(0, 6))

        # Person 1 (You)
        p1_subframe = ctk.CTkFrame(ref_frame, fg_color="transparent")
        p1_subframe.pack(fill="x", padx=8, pady=3)
        ctk.CTkLabel(p1_subframe, text="Person 1 (You):", width=110, font=("Arial", 12, "bold"), anchor="w").pack(side="left")
        self.person_a_label = ctk.CTkLabel(p1_subframe, text="No reference photo selected (Required)", text_color="gray", anchor="w")
        self.person_a_label.pack(side="left", padx=6, fill="x", expand=True)
        self.person_a_btn = ctk.CTkButton(p1_subframe, text="Choose", width=75, height=26, command=self.select_person_a)
        self.person_a_btn.pack(side="right")

        # Person 2 (Husband / Partner)
        p2_subframe = ctk.CTkFrame(ref_frame, fg_color="transparent")
        p2_subframe.pack(fill="x", padx=8, pady=(0, 4))
        ctk.CTkLabel(p2_subframe, text="Person 2 (Husband):", width=110, font=("Arial", 12, "bold"), anchor="w").pack(side="left")
        self.person_b_label = ctk.CTkLabel(p2_subframe, text="No reference photo selected (Optional)", text_color="gray", anchor="w")
        self.person_b_label.pack(side="left", padx=6, fill="x", expand=True)
        self.person_b_btn = ctk.CTkButton(p2_subframe, text="Choose", width=75, height=26, command=self.select_person_b)
        self.person_b_btn.pack(side="right")

        # Mode Selection
        ctk.CTkLabel(container, text="3. Operation mode & action", font=("Arial", 14, "bold")).pack(anchor="w", pady=(2, 4))

        self.face_mode_var = ctk.StringVar(value="trip_cleaner")

        mode_select_frame = ctk.CTkFrame(container, fg_color="transparent")
        mode_select_frame.pack(fill="x", pady=(0, 4))

        m1 = ctk.CTkRadioButton(
            mode_select_frame,
            text="Trip Cleaner (Keep Us + Scenery; Move Other People's Photos Out)",
            variable=self.face_mode_var,
            value="trip_cleaner",
            font=("Arial", 12, "bold")
        )
        m1.pack(anchor="w", pady=(0, 2))

        m2 = ctk.CTkRadioButton(
            mode_select_frame,
            text="Standard Filter (Copy/move photos of Us into Matched_Photos)",
            variable=self.face_mode_var,
            value="standard_filter"
        )
        m2.pack(anchor="w")

        # Trip Cleaner removal scope frame
        self.trip_scope_frame = ctk.CTkFrame(container)
        self.trip_scope_frame.pack(fill="x", pady=(4, 6), padx=4)

        ctk.CTkLabel(
            self.trip_scope_frame,
            text="Trip Cleaner Removal Scope:",
            font=("Arial", 12, "bold")
        ).pack(anchor="w", padx=10, pady=(6, 2))

        self.trip_scope_var = ctk.StringVar(value="solo_only")
        sc1 = ctk.CTkRadioButton(
            self.trip_scope_frame,
            text="Move other people's solo photos only (Keep scenery & group photos)",
            variable=self.trip_scope_var,
            value="solo_only"
        )
        sc1.pack(anchor="w", padx=15, pady=(2, 2))

        sc2 = ctk.CTkRadioButton(
            self.trip_scope_frame,
            text="Move all photos without us (Both other solo & other group shots)",
            variable=self.trip_scope_var,
            value="all_without_us"
        )
        sc2.pack(anchor="w", padx=15, pady=(2, 6))

        # Progress
        ctk.CTkLabel(container, text="4. Progress", font=("Arial", 14, "bold")).pack(anchor="w", pady=(2, 4))
        self.face_progress = ctk.CTkProgressBar(container, height=10)
        self.face_progress.pack(fill="x", pady=(2, 4))
        self.face_progress.set(0)

        self.face_status_label = ctk.CTkLabel(container, text="Ready to process photos", text_color="gray")
        self.face_status_label.pack(anchor="w", pady=(0, 6))

        # Action buttons
        face_btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        face_btn_frame.pack(fill="x", pady=(2, 6))

        self.face_start_btn = ctk.CTkButton(
            face_btn_frame,
            text="CLEAN TRIP PHOTOS (MOVE OTHERS OUT)",
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
            text="Scenery & landscape photos (0 faces detected) and photos with You/Husband are always kept in your main folder.",
            text_color="gray",
            font=("Arial", 10)
        ).pack(pady=(2, 0))

    # ==========================================
    # Tab 4: Date Organizer
    # ==========================================
    def setup_organizer_tab(self, tab):
        container = ctk.CTkFrame(tab, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=15, pady=8)

        ctk.CTkLabel(container, text="1. Select photo/video collection to organize", font=("Arial", 14, "bold")).pack(anchor="w", pady=(2, 4))
        org_src_frame = ctk.CTkFrame(container)
        org_src_frame.pack(fill="x", pady=(0, 8))

        self.org_src_label = ctk.CTkLabel(org_src_frame, text="No folder selected", text_color="gray", anchor="w")
        self.org_src_label.pack(side="left", padx=10, pady=6, fill="x", expand=True)

        self.org_browse_src_btn = ctk.CTkButton(org_src_frame, text="Browse", width=80, height=28, command=self.select_org_source)
        self.org_browse_src_btn.pack(side="right", padx=8, pady=4)

        ctk.CTkLabel(container, text="2. Output location", font=("Arial", 14, "bold")).pack(anchor="w", pady=(2, 4))
        org_out_frame = ctk.CTkFrame(container)
        org_out_frame.pack(fill="x", pady=(0, 8))

        self.org_out_label = ctk.CTkLabel(org_out_frame, text="Default: Organized_Photos (inside source folder)", text_color="gray", anchor="w")
        self.org_out_label.pack(side="left", padx=10, pady=6, fill="x", expand=True)

        self.org_browse_out_btn = ctk.CTkButton(org_out_frame, text="Browse", width=80, height=28, command=self.select_org_output)
        self.org_browse_out_btn.pack(side="right", padx=8, pady=4)

        ctk.CTkLabel(container, text="3. Folder structure style", font=("Arial", 14, "bold")).pack(anchor="w", pady=(2, 4))
        struct_frame = ctk.CTkFrame(container, fg_color="transparent")
        struct_frame.pack(fill="x", pady=(0, 8))

        self.org_structure_var = ctk.StringVar(value="year_month")
        self.org_structure_menu = ctk.CTkOptionMenu(
            struct_frame,
            values=[
                "Year / Month (e.g. 2024 / 2024-08 August)",
                "Year / Month / Day (e.g. 2024 / 2024-08 / 2024-08-20)",
                "Daily Folders (e.g. 2024-08-20)",
                "Year Only (e.g. 2024)"
            ],
            width=360,
            command=self.update_org_structure
        )
        self.org_structure_menu.pack(side="left")

        ctk.CTkLabel(container, text="4. Organization options", font=("Arial", 14, "bold")).pack(anchor="w", pady=(2, 4))
        opts_frame = ctk.CTkFrame(container, fg_color="transparent")
        opts_frame.pack(fill="x", pady=(0, 8))

        self.org_action_var = ctk.StringVar(value="copy")
        org_r1 = ctk.CTkRadioButton(opts_frame, text="Copy files (Safest)", variable=self.org_action_var, value="copy")
        org_r1.pack(side="left", padx=(0, 15))

        org_r2 = ctk.CTkRadioButton(opts_frame, text="Move files", variable=self.org_action_var, value="move")
        org_r2.pack(side="left", padx=(0, 20))

        self.org_rename_var = ctk.BooleanVar(value=False)
        self.org_rename_chk = ctk.CTkCheckBox(opts_frame, text="Prepend timestamp (YYYYMMDD_HHMMSS_name.jpg)", variable=self.org_rename_var)
        self.org_rename_chk.pack(side="left")

        ctk.CTkLabel(container, text="5. Progress", font=("Arial", 14, "bold")).pack(anchor="w", pady=(2, 4))
        self.org_progress = ctk.CTkProgressBar(container, height=10)
        self.org_progress.pack(fill="x", pady=(2, 4))
        self.org_progress.set(0)

        self.org_status_label = ctk.CTkLabel(container, text="Ready to organize photos by date", text_color="gray")
        self.org_status_label.pack(anchor="w", pady=(0, 8))

        org_btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        org_btn_frame.pack(fill="x", pady=(2, 6))

        self.org_start_btn = ctk.CTkButton(org_btn_frame, text="ORGANIZE BY DATE", height=38, font=("Arial", 13, "bold"), command=self.start_organizing)
        self.org_start_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.org_cancel_btn = ctk.CTkButton(org_btn_frame, text="CANCEL", height=38, width=90, fg_color="#555555", hover_color="#777777", command=self.cancel_task, state="disabled")
        self.org_cancel_btn.pack(side="right")

        ctk.CTkLabel(container, text="Extracts EXIF & QuickTime metadata, Google Photos JSONs, and Live Photo pairs.", text_color="gray", font=("Arial", 10)).pack(pady=(2, 0))

    # ==========================================
    # Video Converter Callbacks
    # ==========================================
    def select_vid_source(self):
        if self.running:
            return
        folder = filedialog.askdirectory(title="Select folder containing .mov videos")
        if not folder:
            return
        self.vid_source_folder = Path(folder)
        if not self.vid_custom_output:
            self.vid_output_folder = self.vid_source_folder / "Converted_MP4"
            self.vid_out_label.configure(text=str(self.vid_output_folder))
        self.vid_src_label.configure(text=str(self.vid_source_folder))
        self.vid_status_label.configure(text="Video folder selected. Ready to convert.")

    def select_vid_output(self):
        if self.running:
            return
        folder = filedialog.askdirectory(title="Select output folder for converted .mp4 videos")
        if not folder:
            return
        self.vid_output_folder = Path(folder)
        self.vid_custom_output = True
        self.vid_out_label.configure(text=str(self.vid_output_folder))

    def start_video_conversion(self):
        if self.running:
            return
        if not self.vid_source_folder:
            messagebox.showwarning("Select a folder", "Please select your video folder first.")
            return
        if not self.vid_output_folder:
            self.vid_output_folder = self.vid_source_folder / "Converted_MP4"

        if self.vid_source_folder == self.vid_output_folder or self.vid_output_folder in self.vid_source_folder.parents:
            messagebox.showerror("Invalid output folder", "Output folder cannot be the source folder or a parent directory.")
            return

        self.running = True
        self.active_task = "video_converter"
        self.cancel_event.clear()

        self.vid_start_btn.configure(state="disabled")
        self.vid_browse_src_btn.configure(state="disabled")
        self.vid_browse_out_btn.configure(state="disabled")
        self.vid_cancel_btn.configure(state="normal")

        self.vid_progress.set(0)
        self.vid_status_label.configure(text="Scanning .mov videos...")

        crf = self.vid_quality_var.get()

        self.worker = threading.Thread(
            target=self.run_video_worker,
            args=(crf,),
            daemon=True
        )
        self.worker.start()

    def run_video_worker(self, crf):
        try:
            results = convert_video_folder(
                self.vid_source_folder,
                self.vid_output_folder,
                crf=crf,
                progress_callback=lambda cur, tot, name: self.events.put(("vid_progress", cur, tot, name)),
                cancel_event=self.cancel_event
            )
            self.events.put(("vid_finished", results))
        except Exception as error:
            self.events.put(("error", str(error)))

    # ==========================================
    # Organizer Callbacks
    # ==========================================
    def update_org_structure(self, choice):
        if "Year Only" in choice:
            self.org_structure_var.set("year_only")
        elif "Year / Month / Day" in choice:
            self.org_structure_var.set("year_month_day")
        elif "Daily Folders" in choice:
            self.org_structure_var.set("daily")
        else:
            self.org_structure_var.set("year_month")

    def select_org_source(self):
        if self.running:
            return
        folder = filedialog.askdirectory(title="Select photo collection folder to organize")
        if not folder:
            return
        self.org_source_folder = Path(folder)
        if not self.org_custom_output:
            self.org_output_folder = self.org_source_folder / "Organized_Photos"
            self.org_out_label.configure(text=str(self.org_output_folder))
        self.org_src_label.configure(text=str(self.org_source_folder))
        self.org_status_label.configure(text="Collection selected. Ready to organize.")

    def select_org_output(self):
        if self.running:
            return
        folder = filedialog.askdirectory(title="Select output folder for organized photos")
        if not folder:
            return
        self.org_output_folder = Path(folder)
        self.org_custom_output = True
        self.org_out_label.configure(text=str(self.org_output_folder))

    def start_organizing(self):
        if self.running:
            return

        if not self.org_source_folder:
            messagebox.showwarning("Select a folder", "Please select your photo folder first.")
            return

        if not self.org_output_folder:
            self.org_output_folder = self.org_source_folder / "Organized_Photos"

        if self.org_source_folder == self.org_output_folder or self.org_output_folder in self.org_source_folder.parents:
            messagebox.showerror("Invalid output folder", "Output folder cannot be the source folder or a parent directory.")
            return

        self.running = True
        self.active_task = "organizer"
        self.cancel_event.clear()

        self.org_start_btn.configure(state="disabled")
        self.org_browse_src_btn.configure(state="disabled")
        self.org_browse_out_btn.configure(state="disabled")
        self.org_cancel_btn.configure(state="normal")

        self.org_progress.set(0)
        self.org_status_label.configure(text="Scanning photo dates...")

        structure = self.org_structure_var.get()
        action = self.org_action_var.get()
        rename_files = self.org_rename_var.get()

        self.worker = threading.Thread(
            target=self.run_organizer_worker,
            args=(structure, action, rename_files),
            daemon=True
        )
        self.worker.start()

    def run_organizer_worker(self, structure, action, rename_files):
        try:
            results = organize_photos_by_date(
                source_folder=self.org_source_folder,
                output_folder=self.org_output_folder,
                structure=structure,
                action=action,
                rename_files=rename_files,
                progress_callback=lambda cur, tot, name: self.events.put(("org_progress", cur, tot, name)),
                cancel_event=self.cancel_event
            )
            self.events.put(("org_finished", results))
        except Exception as error:
            self.events.put(("error", str(error)))

    # ==========================================
    # Image Converter Callbacks
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
    # Face Filter & Trip Cleaner Callbacks
    # ==========================================
    def select_face_source(self):
        if self.running:
            return
        folder = filedialog.askdirectory(title="Select photo collection folder to scan")
        if not folder:
            return
        self.face_source_folder = Path(folder)
        self.face_output_folder = self.face_source_folder
        self.face_src_label.configure(text=str(self.face_source_folder))
        self.face_status_label.configure(text="Collection selected. Choose reference faces.")

    def select_person_a(self):
        if self.running:
            return
        file_path = filedialog.askopenfilename(
            title="Select clear reference photo of Person 1 (You)",
            filetypes=[("Image files", "*.jpg;*.jpeg;*.heic;*.heif;*.hif;*.png;*.webp;*.bmp")]
        )
        if file_path:
            self.person_a_path = Path(file_path)
            self.person_a_label.configure(text=self.person_a_path.name, text_color="white")

    def select_person_b(self):
        if self.running:
            return
        file_path = filedialog.askopenfilename(
            title="Select clear reference photo of Person 2 (Husband)",
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
            messagebox.showwarning("Reference photo needed", "Please choose at least a reference photo for Person 1 (You).")
            return

        if not self.face_output_folder:
            self.face_output_folder = self.face_source_folder

        self.running = True
        self.active_task = "face_filter"
        self.cancel_event.clear()

        self.face_start_btn.configure(state="disabled")
        self.face_browse_src_btn.configure(state="disabled")
        self.person_a_btn.configure(state="disabled")
        self.person_b_btn.configure(state="disabled")
        self.face_cancel_btn.configure(state="normal")

        self.face_progress.set(0)
        self.face_status_label.configure(text="Initializing face recognition engine...")

        mode = self.face_mode_var.get()
        trip_scope = self.trip_scope_var.get()

        self.worker = threading.Thread(
            target=self.run_face_worker,
            args=(mode, trip_scope),
            daemon=True
        )
        self.worker.start()

    def run_face_worker(self, mode, trip_scope):
        try:
            if mode == "trip_cleaner":
                results = clean_trip_photos(
                    source_folder=self.face_source_folder,
                    output_folder=self.face_output_folder,
                    person_a_ref=self.person_a_path,
                    person_b_ref=self.person_b_path,
                    removal_scope=trip_scope,
                    progress_callback=lambda cur, tot, txt: self.events.put(("face_progress", cur, tot, txt)),
                    cancel_event=self.cancel_event
                )
                results["mode"] = "trip_cleaner"
            else:
                results = filter_photos_by_faces(
                    source_folder=self.face_source_folder,
                    output_folder=self.face_output_folder,
                    person_a_ref=self.person_a_path,
                    person_b_ref=self.person_b_path,
                    action="move",
                    progress_callback=lambda cur, tot, txt: self.events.put(("face_progress", cur, tot, txt)),
                    cancel_event=self.cancel_event
                )
                results["mode"] = "standard_filter"

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
            elif self.active_task == "video_converter":
                self.vid_cancel_btn.configure(state="disabled")
                self.vid_status_label.configure(text="Cancelling video conversion...")
            elif self.active_task == "face_filter":
                self.face_cancel_btn.configure(state="disabled")
                self.face_status_label.configure(text="Cancelling face filtering...")
            elif self.active_task == "organizer":
                self.org_cancel_btn.configure(state="disabled")
                self.org_status_label.configure(text="Cancelling date organization...")

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

                elif ev_type == "vid_progress":
                    current, total, name = event[1], event[2], event[3]
                    self.vid_progress.set(current / total if total else 0)
                    self.vid_status_label.configure(text=f"Converting {current:,}/{total:,}: {name}")

                elif ev_type == "vid_finished":
                    self.show_vid_results(event[1])

                elif ev_type == "face_progress":
                    current, total, text = event[1], event[2], event[3]
                    self.face_progress.set(current / total if total else 0)
                    self.face_status_label.configure(text=text)

                elif ev_type == "face_finished":
                    self.show_face_results(event[1])

                elif ev_type == "org_progress":
                    current, total, name = event[1], event[2], event[3]
                    self.org_progress.set(current / total if total else 0)
                    self.org_status_label.configure(text=f"Organizing {current:,}/{total:,}: {name}")

                elif ev_type == "org_finished":
                    self.show_org_results(event[1])

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

        # Reset video converter UI
        self.vid_start_btn.configure(state="normal")
        self.vid_browse_src_btn.configure(state="normal")
        self.vid_browse_out_btn.configure(state="normal")
        self.vid_cancel_btn.configure(state="disabled")

        # Reset face filter UI
        self.face_start_btn.configure(state="normal")
        self.face_browse_src_btn.configure(state="normal")
        self.person_a_btn.configure(state="normal")
        self.person_b_btn.configure(state="normal")
        self.face_cancel_btn.configure(state="disabled")

        # Reset organizer UI
        self.org_start_btn.configure(state="normal")
        self.org_browse_src_btn.configure(state="normal")
        self.org_browse_out_btn.configure(state="normal")
        self.org_cancel_btn.configure(state="disabled")

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

    def show_vid_results(self, results):
        self.finish_all_ui()
        total = results["total"]
        converted = results["converted"]
        failed = results["failed"]
        cancelled = results["cancelled"]

        if total:
            self.vid_progress.set((converted + failed) / total)

        status_text = "Video conversion cancelled." if cancelled else "Video conversion completed successfully!"
        self.vid_status_label.configure(text=status_text)

        summary = (
            f"Videos found: {total:,}\n"
            f"Successfully converted to MP4: {converted:,}\n"
            f"Failed: {failed:,}\n"
            f"Cancelled: {'Yes' if cancelled else 'No'}\n\n"
            f"Output folder:\n{self.vid_output_folder}"
        )
        if results["errors"]:
            summary += "\n\nFirst errors:\n" + "\n".join(results["errors"][:5])

        if not cancelled and failed == 0:
            messagebox.showinfo("PhotoFlow - Video Conversion Complete", summary)
        else:
            messagebox.showwarning("PhotoFlow - Results", summary)

    def show_face_results(self, results):
        self.finish_all_ui()
        total = results["total"]
        cancelled = results["cancelled"]

        status_text = "Operation cancelled." if cancelled else "Trip photo processing complete!"
        self.face_status_label.configure(text=status_text)

        if results.get("mode") == "trip_cleaner":
            summary = (
                f"Trip Cleaner Finished!\n\n"
                f"Total photos scanned: {total:,}\n\n"
                f"KEPT in your main collection folder:\n"
                f"  • Photos with You / Husband: {results['kept_us']:,}\n"
                f"  • Scenery & Landscape photos (0 faces): {results['kept_scenery']:,}\n"
                f"  • Other group photos: {results.get('kept_other_groups', 0):,}\n\n"
                f"REMOVED (Moved out of collection):\n"
                f"  • Other people's photos: {results['removed_others']:,}\n\n"
                f"Location of removed photos:\n"
                f"{self.face_output_folder / 'Removed_Other_People'}"
            )
        else:
            matched = results.get("matched", 0)
            unmatched = results.get("unmatched", 0)
            summary = (
                f"Face Filtering Finished!\n\n"
                f"Total photos scanned: {total:,}\n"
                f"Matched photos moved: {matched:,}\n"
                f"  • Person 1 photos: {results.get('person_a_count', 0):,}\n"
                f"  • Person 2 photos: {results.get('person_b_count', 0):,}\n"
                f"  • Photos with both: {results.get('both_count', 0):,}\n"
                f"Other photos: {unmatched:,}\n\n"
                f"Destination:\n{self.face_output_folder / 'Matched_Photos'}"
            )

        if results.get("errors"):
            summary += "\n\nErrors encountered:\n" + "\n".join(results["errors"][:5])

        messagebox.showinfo("PhotoFlow - Complete", summary)

    def show_org_results(self, results):
        self.finish_all_ui()
        total = results["total"]
        organized = results["organized"]
        failed = results["failed"]
        cancelled = results["cancelled"]

        if total:
            self.org_progress.set((organized + failed) / total)

        status_text = "Organization cancelled." if cancelled else "Date organization complete!"
        self.org_status_label.configure(text=status_text)

        years_summary = "\n".join([f"  • {yr}: {cnt:,} items" for yr, cnt in sorted(results["years"].items())])
        sources_summary = "\n".join([
            f"  • From {src}: {cnt:,} items"
            for src, cnt in results.get("sources", {}).items() if cnt > 0
        ])

        summary = (
            f"Total files scanned: {total:,}\n"
            f"Successfully organized: {organized:,}\n\n"
            f"Timestamp Sources:\n{sources_summary if sources_summary else '  None'}\n\n"
            f"Items by Year:\n{years_summary if years_summary else '  None'}\n\n"
            f"Failed: {failed:,}\n"
            f"Cancelled: {'Yes' if cancelled else 'No'}\n\n"
            f"Output destination:\n{self.org_output_folder}"
        )
        if results["errors"]:
            summary += "\n\nFirst errors:\n" + "\n".join(results["errors"][:5])

        messagebox.showinfo("PhotoFlow - Date Organization Complete", summary)


if __name__ == "__main__":
    app = PhotoFlowApp()
    app.mainloop()
