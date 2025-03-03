import os, json
from PyQt6.QtWidgets import QFileDialog, QListWidgetItem
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor  # Added import for QColor

class VideoLoader:
    def __init__(self, main_app):
        self.main_app = main_app
        self.session_file = "session_data.json"

    def load_folder(self):
        folder = QFileDialog.getExistingDirectory(self.main_app, "Select Folder")
        if folder:
            self.main_app.folder_path = folder
            # Check if we already have saved session data for this folder.
            if folder in self.main_app.folder_sessions:
                self.main_app.video_files = self.main_app.folder_sessions[folder]
                self.refresh_video_list()
            else:
                self.load_folder_contents()

    def load_folder_contents(self):
        files = [f for f in os.listdir(self.main_app.folder_path) 
                if f.lower().endswith(('.mp4', '.avi', '.mov'))]
        
        # Use saved session data for this folder if available.
        previous_videos = {}
        if self.main_app.folder_path in self.main_app.folder_sessions:
            previous_videos = {
                entry["display_name"]: entry 
                for entry in self.main_app.folder_sessions[self.main_app.folder_path]
            }
        
        new_video_files = []
        for f in files:
            display_name = f
            # If this video was loaded previously in this folder, preserve its settings.
            video_entry = previous_videos.get(display_name, {
                "original_path": os.path.join(self.main_app.folder_path, f),
                "display_name": display_name,
                "copy_number": 0,
                "export_enabled": False  # Default state
            })
            new_video_files.append(video_entry)
        
        # Append any duplicate entries (saved previously) that aren’t in the file list.
        for display_name, entry in previous_videos.items():
            if display_name not in files:
                new_video_files.append(entry)
        
        self.main_app.video_files = new_video_files
        # Save this folder's state.
        self.main_app.folder_sessions[self.main_app.folder_path] = new_video_files
        
        self.main_app.video_list.clear()
        for entry in self.main_app.video_files:
            self.add_video_item(entry["display_name"])
        
        self.save_session()

    def add_video_item(self, display_name):
        item = QListWidgetItem(display_name)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        # Look up the saved export state.
        entry = next((e for e in self.main_app.video_files if e["display_name"] == display_name), None)
        if entry and entry.get("export_enabled", False):
            item.setCheckState(Qt.CheckState.Checked)
        else:
            item.setCheckState(Qt.CheckState.Unchecked)
        self.update_list_item_color(item)
        self.main_app.video_list.addItem(item)

    def update_list_item_color(self, item):
        idx = self.main_app.video_list.row(item)
        if idx >= 0 and idx < len(self.main_app.video_files):
            # Update the export_enabled flag in the video_files entry.
            self.main_app.video_files[idx]["export_enabled"] = (item.checkState() == Qt.CheckState.Checked)
        if item.checkState() == Qt.CheckState.Checked:
            # Use a darker green.
            item.setBackground(QColor(0, 100, 0))
        else:
            item.setBackground(Qt.GlobalColor.transparent)
        
        # Save the session immediately after updating the state.
        self.save_session()


    def load_video(self, item):
        idx = self.main_app.video_list.row(item)
        if idx < 0 or idx >= len(self.main_app.video_files):
            return
        video_entry = self.main_app.video_files[idx]
        self.main_app.current_video = video_entry["display_name"]
        if self.main_app.cap:
            self.main_app.cap.release()
        
        # Clear any existing crop region from the previous clip.
        self.main_app.clear_crop_region_controller()
        
        if self.main_app.current_video not in self.main_app.crop_regions:
            self.main_app.crop_regions[self.main_app.current_video] = None
        self.main_app.editor.load_video(video_entry)

    def duplicate_clip(self):
        current_item = self.main_app.video_list.currentItem()
        if not current_item:
            return
        current_idx = self.main_app.video_list.row(current_item)
        original_entry = self.main_app.video_files[current_idx]
        base_name, ext = os.path.splitext(original_entry["display_name"])
        # Start with the next copy number.
        new_copy = original_entry["copy_number"] + 1
        new_display = f"{base_name}_{new_copy}{ext}"
        # Check for name collisions.
        existing_names = [entry["display_name"] for entry in self.main_app.video_files]
        while new_display in existing_names:
            new_copy += 1
            new_display = f"{base_name}_{new_copy}{ext}"
        new_entry = {
            "original_path": original_entry["original_path"],
            "display_name": new_display,
            "copy_number": new_copy,
            "export_enabled": original_entry.get("export_enabled", False)
        }
        self.main_app.video_files.append(new_entry)
        self.add_video_item(new_display)
        self.main_app.crop_regions[new_display] = self.main_app.crop_regions.get(original_entry["display_name"], None)
        self.main_app.trim_points[new_display] = self.main_app.trim_points.get(original_entry["display_name"], 0)
        self.save_session()

    def clear_crop_region(self):
        if self.main_app.current_video and self.main_app.current_video in self.main_app.crop_regions:
            self.main_app.crop_regions[self.main_app.current_video] = None
            if self.main_app.current_rect:
                self.main_app.scene.removeItem(self.main_app.current_rect)
                self.main_app.current_rect = None

    def refresh_video_list(self):
        self.main_app.video_list.clear()
        for entry in self.main_app.video_files:
            self.add_video_item(entry["display_name"])

    def load_session(self):
        if os.path.exists(self.session_file):
            with open(self.session_file, "r") as file:
                session_data = json.load(file)
                self.main_app.folder_path = session_data.get("folder_path", "")
                self.main_app.video_files = session_data.get("video_files", [])
                self.main_app.folder_sessions = session_data.get("folder_sessions", {})
                self.main_app.crop_regions = session_data.get("crop_regions", {})
                self.main_app.trim_points = session_data.get("trim_points", {})
                self.main_app.longest_edge = session_data.get("longest_edge", 1024)
                self.main_app.trim_length = session_data.get("trim_length", 60)
        if self.main_app.folder_path and os.path.exists(self.main_app.folder_path):
            if self.main_app.folder_path in self.main_app.folder_sessions:
                self.main_app.video_files = self.main_app.folder_sessions[self.main_app.folder_path]
                self.refresh_video_list()
            else:
                self.load_folder_contents()

    def save_session(self):
        # Update the export_enabled flag from the UI before saving.
        for i in range(self.main_app.video_list.count()):
            item = self.main_app.video_list.item(i)
            self.main_app.video_files[i]["export_enabled"] = (item.checkState() == Qt.CheckState.Checked)
        # Update the mapping for the current folder.
        self.main_app.folder_sessions[self.main_app.folder_path] = self.main_app.video_files
        
        session_data = {
            "folder_path": self.main_app.folder_path,
            "video_files": self.main_app.video_files,
            "folder_sessions": self.main_app.folder_sessions,
            "crop_regions": self.main_app.crop_regions,
            "trim_points": self.main_app.trim_points,
            "longest_edge": self.main_app.longest_edge,
            "trim_length": self.main_app.trim_length
        }
        with open(self.session_file, "w") as file:
            json.dump(session_data, file)
