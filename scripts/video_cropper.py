# video_cropper.py
import sys, os, cv2, ffmpeg, json, numpy as np
from scripts.custom_graphics_view import CustomGraphicsView
from PyQt6.QtWidgets import (
    QApplication, QWidget, QFileDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QListWidget, QSlider, QGraphicsPixmapItem, QLineEdit, QSpinBox,
    QSizePolicy, QCheckBox, QListWidgetItem, QComboBox, QMessageBox
)
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QIcon, QMouseEvent
from PyQt6.QtCore import Qt, QTimer

# Custom scene (modified to use the new crop region)
from scripts.custom_graphics_scene import CustomGraphicsScene

# Import helper modules
from scripts.video_loader import VideoLoader
from scripts.video_editor import VideoEditor
from scripts.video_exporter import VideoExporter

class VideoCropper(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HunyClip")
        self.setGeometry(100, 100, 800, 600)
        self.setWindowIcon(QIcon("icons/favicon.ico"))
        
        # Core state
        self.folder_path = ""
        self.video_files = []  # List of video dicts
        self.current_video = None
        self.crop_regions = {}  # Dict to store crop region data per video
        self.current_rect = None  # Reference to the active crop region item
        self.longest_edge = 1024
        self.cap = None
        self.frame_count = 0
        self.original_width = 0
        self.original_height = 0
        self.start_x = None
        self.start_y = None
        self.end_x = None
        self.end_y = None
        self.clip_aspect_ratio = 1.0  # Default
        
        # Trimming properties
        self.trim_length = 60
        self.trim_points = {}
        self.is_playing = False
        self.loop_playback = False
        
        # Export properties
        self.export_uncropped = False
        self.export_image = False
        self.trim_modified = False
        
        # Session file
        self.session_file = "session_data.json"
        
        # UI widgets
        self.video_list = QListWidget()
        
        # Aspect ratio options (for crop constraint)
        self.aspect_ratios = {
            "Free-form": None,
            "1:1 (Square)": 1.0,
            "4:3 (Standard)": 4/3,
            "16:9 (Widescreen)": 16/9,
            "9:16 (Vertical Video)": 9/16,
            "2:1 (Cinematic)": 2.0,
            "3:2 (Classic Photo)": 3/2,
            "21:9 (Ultrawide)": 21/9
        }
        
        # Create helper modules and pass self.
        self.loader = VideoLoader(self)
        self.editor = VideoEditor(self)
        self.exporter = VideoExporter(self)
        
        # Load previous session.
        self.loader.load_session()
        
        self.initUI()
    
    def initUI(self):
        main_layout = QHBoxLayout(self)
        
        # LEFT PANEL
        left_panel = QVBoxLayout()
        icon_label = QLabel(self)
        icon_pixmap = QPixmap("icons/folder_icon.png")
        icon_label.setPixmap(icon_pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_panel.addWidget(icon_label)
        
        self.folder_button = QPushButton("Select Folder")
        self.folder_button.clicked.connect(self.loader.load_folder)
        left_panel.addWidget(self.folder_button)
        
        self.video_list.itemClicked.connect(self.loader.load_video)
        self.video_list.itemChanged.connect(self.loader.update_list_item_color)
        left_panel.addWidget(self.video_list, 1)


        
        self.duplicate_button = QPushButton("Duplicate Clip")
        self.duplicate_button.clicked.connect(self.loader.duplicate_clip)
        left_panel.addWidget(self.duplicate_button)
        
        self.clear_crop_button = QPushButton("Clear Crop")
        self.clear_crop_button.clicked.connect(self.loader.clear_crop_region)
        left_panel.addWidget(self.clear_crop_button)
        
        self.clip_length_label = QLabel("Clip Length: 0")
        left_panel.addWidget(self.clip_length_label)
        self.trim_point_label = QLabel("Trim Point: 0")
        left_panel.addWidget(self.trim_point_label)
        
        trim_layout = QHBoxLayout()
        trim_layout.addWidget(QLabel("Trim Length (frames):"))
        self.trim_spin = QSpinBox()
        self.trim_spin.setValue(60)
        self.trim_spin.setMaximum(999)
        self.trim_spin.valueChanged.connect(lambda v: setattr(self, 'trim_length', v))
        trim_layout.addWidget(self.trim_spin)
        left_panel.addLayout(trim_layout)
        
        self.export_cropped_checkbox = QCheckBox("Export Cropped Clips")
        self.export_cropped_checkbox.setChecked(False)
        left_panel.addWidget(self.export_cropped_checkbox)
        
        self.export_uncropped_checkbox = QCheckBox("Export Uncropped Clips")
        self.export_uncropped_checkbox.setChecked(False)
        left_panel.addWidget(self.export_uncropped_checkbox)
        
        self.export_image_checkbox = QCheckBox("Export Image at Trim Point")
        self.export_image_checkbox.setChecked(False)
        left_panel.addWidget(self.export_image_checkbox)
        
        main_layout.addLayout(left_panel, 1)

        # self.video_list = QListWidget()
        self.video_list.setStyleSheet("QListWidget::item:selected { background-color: #3A4F7A; }")
        
        # RIGHT PANEL
        right_panel = QVBoxLayout()
        keybindings_label = QLabel("Click and drag to set crop region.  ||   Shortcuts: |  Z - Preview Trim section  |  X - Next Clip  |  C - Play/Pause  | Q/W - Step Trim Left/Right")
        keybindings_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        keybindings_label.setStyleSheet("font-size: 12px; color: #ECEFF4;")
        right_panel.addWidget(keybindings_label)
        
        aspect_ratio_layout = QHBoxLayout()
        aspect_ratio_layout.addWidget(QLabel("Aspect Ratio:"))
        self.aspect_ratio_combo = QComboBox()
        for ratio_name in self.aspect_ratios.keys():
            self.aspect_ratio_combo.addItem(ratio_name)
        self.aspect_ratio_combo.currentTextChanged.connect(self.set_aspect_ratio)
        aspect_ratio_layout.addWidget(self.aspect_ratio_combo)
        right_panel.addLayout(aspect_ratio_layout)
        
        self.graphics_view = CustomGraphicsView()
        self.graphics_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.graphics_view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.graphics_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.scene = CustomGraphicsScene(self)
        self.graphics_view.setScene(self.scene)
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)
        self.graphics_view.setMouseTracking(True)
        right_panel.addWidget(self.graphics_view, 1)
        
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setEnabled(False)
        self.slider.sliderMoved.connect(self.editor.scrub_video)
        right_panel.addWidget(self.slider)
        
        self.thumbnail_label = QWidget(self)
        self.thumbnail_label.setWindowFlags(Qt.WindowType.ToolTip)
        self.thumbnail_label.setStyleSheet("background-color: black; border: 1px solid white;")
        self.thumbnail_label.hide()
        right_panel.addWidget(self.thumbnail_label)
        self.thumbnail_image_label = QLabel(self.thumbnail_label)
        self.thumbnail_image_label.setGeometry(0, 0, 160, 90)
        
        self.slider.installEventFilter(self)
        
        self.resolution_input = QLineEdit()
        self.resolution_input.setPlaceholderText("Set longest edge (default 1024)")
        self.resolution_input.textChanged.connect(self.set_longest_edge)
        right_panel.addWidget(self.resolution_input)
        
        self.submit_button = QPushButton("Export Cropped Videos")
        self.submit_button.clicked.connect(self.exporter.export_videos)
        right_panel.addWidget(self.submit_button)
        
        main_layout.addLayout(right_panel, 3)
    
    def set_aspect_ratio(self, ratio_name):
        ratio_value = self.aspect_ratios.get(ratio_name)
        self.scene.set_aspect_ratio(ratio_value)
    
    def set_longest_edge(self):
        try:
            self.longest_edge = int(self.resolution_input.text())
        except ValueError:
            self.longest_edge = 1080

    def clear_crop_region_controller(self):
        """
        Remove all interactive crop region items from the scene.
        This ensures that when loading a new clip or creating a new crop region,
        only one crop region is visible.
        """
        from scripts.interactive_crop_region import InteractiveCropRegion
        # Collect all items that are instances of InteractiveCropRegion.
        items_to_remove = [item for item in self.scene.items() if isinstance(item, InteractiveCropRegion)]
        for item in items_to_remove:
            self.scene.removeItem(item)
        self.current_rect = None


    def crop_rect_updating(self, rect):
        """
        Callback invoked during crop region adjustment.
        You can use this to update a preview or status label.
        """
        print(f"Crop region updating: {rect}")

    def crop_rect_finalized(self, rect):
        """
        Callback invoked when the crop region is finalized (on mouse release or after a wheel event).
        This saves the crop region relative to the original clip dimensions.
        """
        if not self.current_video:
            return
        pixmap = self.pixmap_item.pixmap()
        if pixmap is None or pixmap.width() == 0:
            return
        scale_w = self.original_width / pixmap.width()
        scale_h = self.original_height / pixmap.height()
        x = int(rect.x() * scale_w)
        y = int(rect.y() * scale_h)
        w = int(rect.width() * scale_w)
        h = int(rect.height() * scale_h)
        self.crop_regions[self.current_video] = (x, y, w, h)
        self.check_current_video_item()

    def check_current_video_item(self):
        # Find the list item corresponding to the current video and mark it checked.
        for i in range(self.video_list.count()):
            item = self.video_list.item(i)
            if item.text() == self.current_video:
                if item.checkState() != Qt.CheckState.Checked:
                    item.setCheckState(Qt.CheckState.Checked)
                break

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Z:
            self.editor.toggle_loop_playback()
        elif key == Qt.Key.Key_X:
            self.editor.next_clip()
        elif key == Qt.Key.Key_C:
            self.editor.toggle_play_forward()
        elif key == Qt.Key.Key_Q:  # Added for stepping left
            self.editor.move_trim(-1)
        elif key == Qt.Key.Key_W:  # Added for stepping right
            self.editor.move_trim(1)
        elif key == Qt.Key.Key_Left:
            self.editor.move_trim(-1)
        elif key == Qt.Key.Key_Right:
            self.editor.move_trim(1)
        elif key == Qt.Key.Key_Up:
            self.editor.navigate_clip(-1)
        elif key == Qt.Key.Key_Down:
            self.editor.navigate_clip(1)
        else:
            super().keyPressEvent(event)

    
    def eventFilter(self, source, event):
        # This event filter is only used for the slider.
        if source is self.slider:
            if event.type() == QMouseEvent.Type.MouseButtonPress:
                self.editor.move_trim_to_click_position(event)
            elif event.type() == QMouseEvent.Type.HoverMove:
                self.editor.show_thumbnail(event)
            elif event.type() == QMouseEvent.Type.Leave:
                self.thumbnail_label.hide()
        return False

    def closeEvent(self, event):
        self.loader.save_session()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    if os.path.exists("styles/dark_mode.css"):
        with open("styles/dark_mode.css", "r") as file:
            app.setStyleSheet(file.read())
    window = VideoCropper()
    window.show()
    sys.exit(app.exec())
