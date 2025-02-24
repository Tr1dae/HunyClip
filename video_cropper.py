import sys
import os
import cv2
import ffmpeg
import numpy as np
import json
from PyQt6.QtWidgets import (
    QApplication, QWidget, QFileDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QListWidget, QSlider, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QLineEdit,
    QSpinBox, QSizePolicy, QCheckBox, QListWidgetItem
)
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QMouseEvent
from PyQt6.QtCore import Qt, QRectF, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMessageBox

class VideoCropper(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HunyClip")
        self.setGeometry(100, 100, 800, 600)
        
        # Set the window icon
        self.setWindowIcon(QIcon("favicon.ico"))    
        self.folder_path = ""
        self.video_files = []  # Now stores dicts instead of strings
        self.current_video = None
        self.crop_regions = {} 
        self.current_rect = None 
        self.longest_edge = 1024
        self.cap = None
        self.frame_count = 0
        self.original_width = 0
        self.original_height = 0
        self.display_width = 0
        self.display_height = 0
        self.start_x = None
        self.start_y = None
        self.end_x = None
        self.end_y = None
        
        # New properties for trimming
        self.trim_length = 60
        self.trim_points = {}
        self.is_playing = False
        self.loop_playback = False
        
        # New property for exporting uncropped clips
        self.export_uncropped = False
        self.export_image = False
        
        # Temp file to save session data
        self.session_file = "session_data.json"
        
        # Initialize video_list before loading session
        self.video_list = QListWidget()
        left_panel = QVBoxLayout()

        # Video list
        self.video_list.itemClicked.connect(self.load_video)
        self.video_list.itemChanged.connect(self.update_list_item_color)  # Connect itemChanged signal
        left_panel.addWidget(self.video_list, 1)
        
        # Load previous session if exists
        self.load_session()
        
        self.initUI()
    
    def initUI(self):
        main_layout = QHBoxLayout()
        left_panel = QVBoxLayout()
        
        # Add a QLabel to display the icon above the "Select Folder" button
        icon_label = QLabel(self)
        icon_pixmap = QPixmap("folder_icon.png")  # Replace "folder_icon.png" with the path to your PNG file
        icon_label.setPixmap(icon_pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio))  # Scale the icon to 32x32
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center the icon
        left_panel.addWidget(icon_label)

        # Folder selection
        self.folder_button = QPushButton("Select Folder")
        self.folder_button.clicked.connect(self.load_folder)
        left_panel.addWidget(self.folder_button)
        
        # Video list
        self.video_list.itemClicked.connect(self.load_video)
        left_panel.addWidget(self.video_list, 1)
        
        # Duplicate button
        self.duplicate_button = QPushButton("Duplicate Clip")
        self.duplicate_button.clicked.connect(self.duplicate_clip)
        left_panel.addWidget(self.duplicate_button)
        
        # Clear Crop button
        self.clear_crop_button = QPushButton("Clear Crop")
        self.clear_crop_button.clicked.connect(self.clear_crop_region)
        left_panel.addWidget(self.clear_crop_button)
        
        # Info labels
        self.clip_length_label = QLabel("Clip Length: 0")
        left_panel.addWidget(self.clip_length_label)
        self.trim_point_label = QLabel("Trim Point: 0")
        left_panel.addWidget(self.trim_point_label)
        
        # Trim controls
        trim_layout = QHBoxLayout()
        trim_layout.addWidget(QLabel("Trim Length (frames):"))
        self.trim_spin = QSpinBox()
        self.trim_spin.setValue(60)
        self.trim_spin.setMaximum(999)
        self.trim_spin.valueChanged.connect(lambda v: setattr(self, 'trim_length', v))
        trim_layout.addWidget(self.trim_spin)
        left_panel.addLayout(trim_layout)
        
        # Export Cropped toggle
        self.export_cropped_checkbox = QCheckBox("Export Cropped Clips")
        self.export_cropped_checkbox.setChecked(False)  # Default to OFF
        left_panel.addWidget(self.export_cropped_checkbox)

        # Export uncropped toggle
        self.export_uncropped_checkbox = QCheckBox("Export Uncropped Clips")
        self.export_uncropped_checkbox.setChecked(False)  # Default to OFF
        left_panel.addWidget(self.export_uncropped_checkbox)

        # Add "Export Image at Trim Point" toggle
        self.export_image_checkbox = QCheckBox("Export Image at Trim Point")
        self.export_image_checkbox.setChecked(False)  # Default to OFF
        left_panel.addWidget(self.export_image_checkbox)
        
        main_layout.addLayout(left_panel, 1)
        
        # Right panel
        right_panel = QVBoxLayout()

        # Keybinding label
        keybindings_label = QLabel("Click and drag to set crop region.  ||   Shortcuts: |  Z - Preview Trim section  |  X - Next Clip  |  C - Play/Pause  | Q/W - Step Trim Left/Right")
        keybindings_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center the text
        keybindings_label.setStyleSheet("font-size: 12px; color: #ECEFF4;")  # Style the label
        right_panel.addWidget(keybindings_label)
        
        # Video display
        self.graphics_view = QGraphicsView()
        self.graphics_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.graphics_view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.graphics_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.scene = QGraphicsScene()
        self.graphics_view.setScene(self.scene)
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)
        right_panel.addWidget(self.graphics_view, 1)
        
        # Timeline scrubber
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setEnabled(False)
        self.slider.sliderMoved.connect(self.scrub_video)
        right_panel.addWidget(self.slider)
        
        # Longest edge input
        self.resolution_input = QLineEdit()
        self.resolution_input.setPlaceholderText("Set longest edge (default 1024)")
        self.resolution_input.textChanged.connect(self.set_longest_edge)
        right_panel.addWidget(self.resolution_input)
        
        # Submit button
        self.submit_button = QPushButton("Export Cropped Videos")
        self.submit_button.clicked.connect(self.export_videos)
        right_panel.addWidget(self.submit_button)
        
        main_layout.addLayout(right_panel, 3)
        self.setLayout(main_layout)
        
        # Enable mouse tracking and events
        self.graphics_view.viewport().setMouseTracking(True)
        self.graphics_view.viewport().installEventFilter(self)
    
    def clear_crop_region(self):
        if self.current_video and self.current_video in self.crop_regions:
            self.crop_regions[self.current_video] = None
            if self.current_rect:
                self.scene.removeItem(self.current_rect)
                self.current_rect = None
            self.enable_export_for_current_video()  # Update export status

    def load_session(self):
        if os.path.exists(self.session_file):
            with open(self.session_file, 'r') as file:
                session_data = json.load(file)
                self.folder_path = session_data.get('folder_path', "")
                self.video_files = session_data.get('video_files', [])  # Ensure export_enabled is retained

                self.crop_regions = session_data.get('crop_regions', {})
                self.trim_points = session_data.get('trim_points', {})
                self.longest_edge = session_data.get('longest_edge', 1024)
                self.trim_length = session_data.get('trim_length', 60)
                self.export_uncropped = session_data.get('export_uncropped', False)
                self.export_image = session_data.get('export_image', False)

                # Restore tickboxes
                self.video_list.clear()
                for entry in self.video_files:
                    self.add_video_item(entry['display_name'], entry.get('export_enabled', False))

                # Only reload folder if it wasn't already stored in session
                if self.folder_path and os.path.exists(self.folder_path):
                    self.load_folder_contents()

    def save_session(self):
        # Ensure that the latest checkbox states are stored in self.video_files
        for i in range(self.video_list.count()):
            item = self.video_list.item(i)
            self.video_files[i]['export_enabled'] = item.checkState() == Qt.CheckState.Checked

        session_data = {
            'folder_path': self.folder_path,
            'video_files': self.video_files,
            'crop_regions': self.crop_regions,
            'trim_points': self.trim_points,
            'longest_edge': self.longest_edge,
            'trim_length': self.trim_length,
            'export_uncropped': self.export_uncropped,
            'export_image': self.export_image
        }

        with open(self.session_file, 'w') as file:
            json.dump(session_data, file)

    def closeEvent(self, event):
        self.save_session()
        event.accept()
    
    def load_folder_contents(self):
        files = [f for f in os.listdir(self.folder_path) 
                if f.lower().endswith(('.mp4', '.avi', '.mov'))]

        # Preserve previous settings if they exist
        previous_video_files = {entry['display_name']: entry for entry in self.video_files}

        self.video_files = []
        for f in files:
            display_name = f
            video_entry = previous_video_files.get(display_name, {
                'original_path': os.path.join(self.folder_path, f),
                'display_name': display_name,
                'copy_number': 0,
                'export_enabled': False  # Default if not found in session
            })
            self.video_files.append(video_entry)

        # Clear and re-add items
        self.video_list.clear()
        for entry in self.video_files:
            self.add_video_item(entry['display_name'], entry['export_enabled'])

        # Restore crop regions and trim points for existing videos
        for entry in self.video_files:
            if entry['display_name'] in self.crop_regions:
                entry['crop_region'] = self.crop_regions[entry['display_name']]
            if entry['display_name'] in self.trim_points:
                entry['trim_point'] = self.trim_points[entry['display_name']]
    
    def load_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.folder_path = folder
            self.load_folder_contents()
       
    def duplicate_clip(self):
        current_item = self.video_list.currentItem()
        if not current_item:
            return
            
        current_idx = self.video_list.row(current_item)
        original_entry = self.video_files[current_idx]
        
        # Find next available copy number
        new_copy = original_entry['copy_number'] + 1
        base_name, ext = os.path.splitext(original_entry['display_name'])
        new_display = f"{base_name}_{new_copy}{ext}"
        
        # Create new entry
        new_entry = {
            'original_path': original_entry['original_path'],
            'display_name': new_display,
            'copy_number': new_copy,
            'export_enabled': True
        }
        self.video_files.append(new_entry)
        self.add_video_item(new_display, True)
        
        # Copy existing settings
        self.crop_regions[new_display] = self.crop_regions.get(
            original_entry['display_name'], None
        )
        self.trim_points[new_display] = self.trim_points.get(
            original_entry['display_name'], 0
        )
    
    def eventFilter(self, source, event):
        if source is self.graphics_view.viewport():
            if event.type() == QMouseEvent.Type.MouseButtonPress:
                self.start_selection(event)
            elif event.type() == QMouseEvent.Type.MouseButtonRelease:
                self.end_selection(event)
        return super().eventFilter(source, event)
    
    def start_selection(self, event):
        pos = self.graphics_view.mapToScene(event.pos())
        self.start_x = pos.x()
        self.start_y = pos.y()
    
    def end_selection(self, event):
        pos = self.graphics_view.mapToScene(event.pos())
        self.end_x = pos.x()
        self.end_y = pos.y()
        
        if None not in (self.start_x, self.start_y, self.end_x, self.end_y):
            # Ensure the crop rectangle stays within the video bounds
            x1 = max(0, min(self.start_x, self.end_x))  # Clip x1 to 0 or higher
            y1 = max(0, min(self.start_y, self.end_y))  # Clip y1 to 0 or higher
            x2 = min(self.pixmap_item.pixmap().width(), max(self.start_x, self.end_x))  # Clip x2 to video width
            y2 = min(self.pixmap_item.pixmap().height(), max(self.start_y, self.end_y))  # Clip y2 to video height
            
            # Ensure the crop rectangle has a valid width and height
            w = max(0, x2 - x1)  # Width cannot be negative
            h = max(0, y2 - y1)  # Height cannot be negative
            
            # If the crop rectangle is too small, skip it
            if w < 10 or h < 10:  # Minimum size threshold (adjust as needed)
                print("Crop region is too small. Please select a larger area.")
                return
            
            # Scale the crop region to the original video dimensions
            scale_w = self.original_width / self.pixmap_item.pixmap().width()
            scale_h = self.original_height / self.pixmap_item.pixmap().height()
            
            self.crop_regions[self.current_video] = (
                int(x1 * scale_w), int(y1 * scale_h),
                int(w * scale_w), int(h * scale_h)
            )
            
            # Draw the crop rectangle on the screen
            self.draw_crop_rectangle(x1, y1, w, h)
            self.enable_export_for_current_video()  # Enable export when crop is modified
    
    def draw_crop_rectangle(self, x, y, w, h):
        if self.current_rect:
            self.scene.removeItem(self.current_rect)
        
        # Ensure the rectangle stays within the video bounds
        x = max(0, min(x, self.pixmap_item.pixmap().width() - w))
        y = max(0, min(y, self.pixmap_item.pixmap().height() - h))
        
        self.current_rect = self.scene.addRect(x, y, w, h, QPen(QColor(255, 0, 0)))

    def enable_export_for_current_video(self):
        current_item = self.video_list.currentItem()
        if current_item:
            current_item.setCheckState(Qt.CheckState.Checked)
            self.update_list_item_color(current_item)

    def update_list_item_color(self, item):
        idx = self.video_list.row(item)
        if idx >= 0 and idx < len(self.video_files):
            self.video_files[idx]['export_enabled'] = item.checkState() == Qt.CheckState.Checked
        if item.checkState() == Qt.CheckState.Checked:
            item.setBackground(QColor(100, 150, 100))  # Light green color for enabled items
        else:
            item.setBackground(QColor(0, 0, 0, 0))  # Reset to default color (transparent)           
    
    def load_video(self, item):
        idx = self.video_list.row(item)
        video_entry = self.video_files[idx]
        video_path = video_entry['original_path']
        display_name = video_entry['display_name']
        
        # Use display name as key
        self.current_video = display_name
        
        # Release previous video if needed
        if hasattr(self, 'cap') and self.cap:
            self.cap.release()

        # Initialize crop_regions if not already set
        if display_name not in self.crop_regions:
            self.crop_regions[display_name] = None

        # Open the video and get frame count
        self.cap = cv2.VideoCapture(video_path)

        # Ensure video opened correctly
        if not self.cap.isOpened():
            print("Error: Could not open video file.")
            return  

        self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.original_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.original_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Ensure frame count is valid before proceeding
        if self.frame_count <= 0:
            print("Error: Video frame count is 0 or not read correctly.")
            return  

        # Enforce a valid trim position
        if display_name not in self.trim_points or self.trim_points[display_name] <= 0:
            self.trim_points[display_name] = self.frame_count // 2  # Always default to middle if unset or invalid

        trim_frame = self.trim_points[display_name]  # Now this will always be correct

        # Set up the slider and labels
        self.slider.setMaximum(self.frame_count - 1)
        self.slider.setEnabled(True)
        self.slider.setValue(trim_frame)
        self.clip_length_label.setText(f"Clip Length: {self.frame_count}")
        self.update_trim_label()

        # Seek the video to the trim position
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, trim_frame)

        # Force frame decoding to ensure it's properly set
        for _ in range(5):  # Multiple grabs to ensure proper seeking
            self.cap.grab()

        ret, frame = self.cap.read()
        if ret:
            self.display_frame(frame)
        else:
            print("Error: Could not read frame at trim point.")

        # Draw crop rectangle only if a crop region is set for this video
        if self.crop_regions[display_name]:
            crop = self.crop_regions[display_name]
            scale_w = self.pixmap_item.pixmap().width() / self.original_width
            scale_h = self.pixmap_item.pixmap().height() / self.original_height
            x, y, w, h = crop[0] * scale_w, crop[1] * scale_h, crop[2] * scale_w, crop[3] * scale_h
            self.draw_crop_rectangle(x, y, w, h)
        else:
            # Remove the crop rectangle if no crop is set
            if self.current_rect:
                self.scene.removeItem(self.current_rect)
                self.current_rect = None

    def scrub_video(self, position):
        if self.cap:
            self.trim_points[self.current_video] = int(float(position))
            self.update_trim_label()
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.trim_points[self.current_video])
            ret, frame = self.cap.read()
            if ret:
                self.display_frame(frame)
            self.enable_export_for_current_video()  # Enable export when trim is modified

    def add_video_item(self, display_name, export_enabled):
        item = QListWidgetItem(display_name)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked if export_enabled else Qt.CheckState.Unchecked)  # Restore saved checkbox state
        self.update_list_item_color(item)  # Update color based on state
        self.video_list.addItem(item)

    def update_trim_label(self):
        val = self.slider.value()
        self.trim_point_label.setText(f"Trim Point: {val}")
        self.trim_points[self.current_video] = val
    
    def display_frame(self, frame):
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        
        scaled_pixmap = pixmap.scaled(
            self.graphics_view.width()-20, 
            self.graphics_view.height()-20, 
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.pixmap_item.setPixmap(scaled_pixmap)
        self.graphics_view.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
    
    def set_longest_edge(self):
        try:
            self.longest_edge = int(self.resolution_input.text())
        except ValueError:
            self.longest_edge = 1080
    
    def export_videos(self):
        # Check if the "Export Uncropped Clips" toggle is disabled
        if not self.export_uncropped_checkbox.isChecked():
            # Create a warning popup for uncropped videos
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setText("Uncropped clips will not be exported.")
            msg.setInformativeText("Toggle 'Export Uncropped Clips' to export all clips.")
            msg.setWindowTitle("Export Warning")

            # Add "Continue Anyway" and "Return" buttons
            continue_button = msg.addButton("Continue Anyway", QMessageBox.ButtonRole.AcceptRole)
            return_button = msg.addButton("Return", QMessageBox.ButtonRole.RejectRole)

            # Show the popup and wait for user input
            msg.exec()

            # If the user clicks "Return", cancel the export
            if msg.clickedButton() == return_button:
                return

        # Now check for the cropped checkbox
        if not self.export_cropped_checkbox.isChecked():
            # Create a warning popup for cropped videos
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setText("Cropped clips will not be exported.")
            msg.setInformativeText("Toggle 'Export Cropped Clips' to export cropped clips.")
            msg.setWindowTitle("Export Warning")

            # Add "Continue Anyway" and "Return" buttons
            continue_button = msg.addButton("Continue Anyway", QMessageBox.ButtonRole.AcceptRole)
            return_button = msg.addButton("Return", QMessageBox.ButtonRole.RejectRole)

            # Show the popup and wait for user input
            msg.exec()

            # If the user clicks "Return", cancel the export
            if msg.clickedButton() == return_button:
                return

        
        output_folder = os.path.join(self.folder_path, "cropped")
        os.makedirs(output_folder, exist_ok=True)
        
        # Create uncropped folder if the toggle is enabled
        if self.export_uncropped_checkbox.isChecked():
            uncropped_folder = os.path.join(self.folder_path, "uncropped")
            os.makedirs(uncropped_folder, exist_ok=True)
        
        for entry in self.video_files:
            video_path = entry['original_path']
            display_name = entry['display_name']
            crop = self.crop_regions.get(display_name)
            
            # Check if the item is enabled for export
            item = self.video_list.item(self.video_files.index(entry))
            if item.checkState() != Qt.CheckState.Checked:
                continue
            
            cap = cv2.VideoCapture(video_path)
            orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            # Get trim point
            trim_start = self.trim_points.get(display_name, 0)
            
            # Calculate duration for both cropped and uncropped videos
            duration = self.trim_length / fps  # Duration is always calculated
            
            # Export image at trim point if the toggle is enabled
            if self.export_image_checkbox.isChecked():
                # Seek to the trim point
                cap.set(cv2.CAP_PROP_POS_FRAMES, trim_start)
                ret, frame = cap.read()
                if ret:
                    # Save the frame as an image with the same naming convention as cropped videos
                    base_name = os.path.splitext(display_name)[0]  # Remove original extension
                    
                    # Export cropped image (with crop applied)
                    if crop:
                        x, y, w, h = crop
                        # Ensure crop region is within bounds
                        if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > orig_w or y + h > orig_h:
                            print(f"Invalid crop region for {display_name}: x={x}, y={y}, w={w}, h={h}")
                            continue  # Skip this frame if the crop region is invalid
                        
                        # Apply crop to the frame
                        cropped_frame = frame[y:y+h, x:x+w]
                        if cropped_frame.size == 0:
                            print(f"Empty crop region for {display_name}: x={x}, y={y}, w={w}, h={h}")
                            continue  # Skip this frame if the crop region is empty
                        
                        cropped_image_name = f"{base_name}_cropped.png"  # Use _cropped.png suffix
                        cropped_image_path = os.path.join(output_folder, cropped_image_name)
                        cv2.imwrite(cropped_image_path, cropped_frame)
                        print(f"Exported cropped image for {display_name} to {cropped_image_path}")
                    
                    # Export uncropped image if the toggle is enabled
                    if self.export_uncropped_checkbox.isChecked():
                        uncropped_image_name = f"{base_name}.png"  # Use _uncropped.png suffix
                        uncropped_image_path = os.path.join(uncropped_folder, uncropped_image_name)
                        cv2.imwrite(uncropped_image_path, frame)
                        print(f"Exported uncropped image for {display_name} to {uncropped_image_path}")
            
            # Export cropped video if a crop region is set
            if self.export_cropped_checkbox.isChecked() and crop:
                x, y, w, h = crop
                # Ensure crop region is within bounds
                if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > orig_w or y + h > orig_h:
                    print(f"Invalid crop region for {display_name}: x={x}, y={y}, w={w}, h={h}")
                else:
                    # Ensure scaled dimensions are even numbers
                    if self.longest_edge % 2 != 0:
                        self.longest_edge -= 1  # Force even number

                    if h % 2 != 0:
                        h -= 1
                    if w % 2 != 0:
                        w -= 1
                                    
                    # Export cropped video
                    output_name = display_name.replace('.', '_cropped.')
                    output_path = os.path.join(output_folder, output_name)
                    (
                        ffmpeg
                        .input(video_path, ss=trim_start / fps, t=duration)
                        .filter('crop', w, h, x, y)
                        .filter('scale', self.longest_edge, -2)
                        .output(output_path)
                        .run(overwrite_output=True)
                    )
                    print(f"Exported cropped {display_name} to {output_path}")

            
            # Export uncropped video if the toggle is enabled
            if self.export_uncropped_checkbox.isChecked():
                uncropped_path = os.path.join(uncropped_folder, display_name)
                (
                    ffmpeg
                    .input(video_path, ss=trim_start / fps, t=duration)
                    .output(uncropped_path)
                    .run(overwrite_output=True)
                )
                print(f"Exported uncropped {display_name} to {uncropped_path}")
            
            cap.release()

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Z:
            self.toggle_loop_playback()
        elif key == Qt.Key.Key_X:
            self.next_clip()
        elif key == Qt.Key.Key_C:
            self.toggle_play_forward()
        elif key == Qt.Key.Key_Left:
            self.move_trim(-1)
        elif key == Qt.Key.Key_Right:
            self.move_trim(1)
        elif key == Qt.Key.Key_Up:
            self.navigate_clip(-1)
        elif key == Qt.Key.Key_Down:
            self.navigate_clip(1)
    
    def toggle_loop_playback(self):
        self.loop_playback = not self.loop_playback
        if self.loop_playback:
            self.start_loop_playback()
        else:
            self.stop_playback()
    
    def start_loop_playback(self):
        if self.cap and self.loop_playback:
            start = self.trim_points[self.current_video]
            end = start + self.trim_length
            current_frame = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
            
            if current_frame >= end:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, start)
            
            ret, frame = self.cap.read()
            if ret:
                self.display_frame(frame)
                QTimer.singleShot(30, self.start_loop_playback)  # Use QTimer instead of root.after
    
    def toggle_play_forward(self):
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.play_forward()
        else:
            self.stop_playback()
    
    def play_forward(self):
        if self.is_playing and self.cap:
            ret, frame = self.cap.read()
            if ret:
                current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
                self.trim_points[self.current_video] = current_frame
                self.slider.setValue(current_frame)
                self.update_trim_label()
                self.display_frame(frame)
                QTimer.singleShot(30, self.play_forward)
    
    def stop_playback(self):
        self.is_playing = False
        self.loop_playback = False
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 
                       self.trim_points.get(self.current_video, 0))
    
    def next_clip(self):
        current_idx = self.video_list.currentRow()
        new_idx = min(len(self.video_files)-1, current_idx + 1)
        self.video_list.setCurrentRow(new_idx)
        self.load_video(self.video_list.currentItem())
    
    def move_trim(self, step):
        new_val = self.slider.value() + step
        new_val = max(0, min(new_val, self.slider.maximum()))
        self.slider.setValue(new_val)
        self.update_trim_label()
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, new_val)
        ret, frame = self.cap.read()
        if ret:
            self.display_frame(frame)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Load the dark mode stylesheet from a file
    with open("dark_mode.css", "r") as file:
        dark_stylesheet = file.read()
    app.setStyleSheet(dark_stylesheet)
    
    try:
        window = VideoCropper()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"An error occurred: {e}")
        input("Press Enter to exit...")  # Keep the terminal open
        sys.exit(1)
