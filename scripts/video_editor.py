# video_editor.py
import cv2
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QPen
from PyQt6.QtCore import Qt, QTimer, QRectF
from scripts.interactive_crop_region import InteractiveCropRegion  # New interactive crop region

class VideoEditor:
    def __init__(self, main_app):
        self.main_app = main_app

    def load_video(self, video_entry):
        video_path = video_entry["original_path"]
        self.main_app.cap = cv2.VideoCapture(video_path)
        if not self.main_app.cap.isOpened():
            print("Error: Could not open video file.")
            return
        self.main_app.frame_count = int(self.main_app.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.main_app.original_width = int(self.main_app.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.main_app.original_height = int(self.main_app.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.main_app.clip_aspect_ratio = self.main_app.original_width / self.main_app.original_height
        if (self.main_app.current_video not in self.main_app.trim_points or 
            self.main_app.trim_points[self.main_app.current_video] <= 0):
            self.main_app.trim_points[self.main_app.current_video] = self.main_app.frame_count // 2
        trim_frame = self.main_app.trim_points[self.main_app.current_video]
        self.main_app.slider.setMaximum(self.main_app.frame_count - 1)
        self.main_app.slider.setEnabled(True)
        self.main_app.slider.setValue(trim_frame)
        self.main_app.clip_length_label.setText(f"Clip Length: {self.main_app.frame_count}")
        self.update_trim_label()
        self.main_app.cap.set(cv2.CAP_PROP_POS_FRAMES, trim_frame)
        for _ in range(5):
            self.main_app.cap.grab()
        ret, frame = self.main_app.cap.read()
        if ret:
            self.display_frame(frame)
        else:
            print("Error: Could not read frame at trim point.")

        # Check if there is a crop region saved for this video.
        crop = self.main_app.crop_regions.get(self.main_app.current_video)
        if crop:
            # Scale the saved crop region to the displayed image dimensions.
            scale_w = self.main_app.pixmap_item.pixmap().width() / self.main_app.original_width
            scale_h = self.main_app.pixmap_item.pixmap().height() / self.main_app.original_height
            x = crop[0] * scale_w
            y = crop[1] * scale_h
            w = crop[2] * scale_w
            h = crop[3] * scale_h
            self.draw_crop_rectangle(x, y, w, h)
        else:
            # Remove any lingering interactive crop region items from the scene.
            items_to_remove = [item for item in self.main_app.scene.items() 
                               if isinstance(item, InteractiveCropRegion)]
            for item in items_to_remove:
                self.main_app.scene.removeItem(item)
            self.main_app.current_rect = None

    def display_frame(self, frame):
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        scaled_pixmap = pixmap.scaled(
            self.main_app.graphics_view.width() - 20,
            self.main_app.graphics_view.height() - 20,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.main_app.pixmap_item.setPixmap(scaled_pixmap)
        self.main_app.graphics_view.fitInView(self.main_app.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
        # Set the scene boundaries to match the pixmap's bounding rectangle.
        self.main_app.scene.setSceneRect(self.main_app.pixmap_item.boundingRect())

    def scrub_video(self, position):
        if self.main_app.cap:
            self.main_app.trim_points[self.main_app.current_video] = int(position)
            self.main_app.trim_modified = True
            self.update_trim_label()
            self.main_app.cap.set(cv2.CAP_PROP_POS_FRAMES, int(position))
            ret, frame = self.main_app.cap.read()
            if ret:
                self.display_frame(frame)

    def update_trim_label(self):
        val = self.main_app.slider.value()
        # Only update the text if it's different to prevent cursor jumping
        if str(val) != self.main_app.trim_point_label.text():
            self.main_app.trim_point_label.setText(str(val))
        self.main_app.trim_points[self.main_app.current_video] = val
        if self.main_app.trim_modified:
            self.main_app.check_current_video_item()
            self.main_app.trim_modified = False

    def start_selection(self, event):
        pos = self.main_app.graphics_view.mapToScene(event.pos())
        self.main_app.start_x = pos.x()
        self.main_app.start_y = pos.y()

    def end_selection(self, event):
        pos = self.main_app.graphics_view.mapToScene(event.pos())
        self.main_app.end_x = pos.x()
        self.main_app.end_y = pos.y()
        if None not in (self.main_app.start_x, self.main_app.start_y, 
                        self.main_app.end_x, self.main_app.end_y):
            x1 = max(0, min(self.main_app.start_x, self.main_app.end_x))
            y1 = max(0, min(self.main_app.start_y, self.main_app.end_y))
            x2 = min(self.main_app.pixmap_item.pixmap().width(), max(self.main_app.start_x, self.main_app.end_x))
            y2 = min(self.main_app.pixmap_item.pixmap().height(), max(self.main_app.start_y, self.main_app.end_y))
            w = max(0, x2 - x1)
            h = max(0, y2 - y1)
            if w < 10 or h < 10:
                print("Crop region is too small.")
                return
            scale_w = self.main_app.original_width / self.main_app.pixmap_item.pixmap().width()
            scale_h = self.main_app.original_height / self.main_app.pixmap_item.pixmap().height()
            self.main_app.crop_regions[self.main_app.current_video] = (
                int(x1 * scale_w), int(y1 * scale_h), int(w * scale_w), int(h * scale_h)
            )
            self.draw_crop_rectangle(x1, y1, w, h)
            self.main_app.check_current_video_item()

    def draw_crop_rectangle(self, x, y, w, h):
        from scripts.interactive_crop_region import InteractiveCropRegion
        # Remove any existing crop region.
        if self.main_app.current_rect:
            self.main_app.scene.removeItem(self.main_app.current_rect)
        # Create a new interactive crop region.
        rect = QRectF(x, y, w, h)
        aspect = self.main_app.scene.aspect_ratio if hasattr(self.main_app.scene, "aspect_ratio") else None
        self.main_app.current_rect = InteractiveCropRegion(rect, aspect_ratio=aspect)
        self.main_app.scene.addItem(self.main_app.current_rect)
        # Set the scene's crop_item pointer to the current region.
        self.main_app.scene.crop_item = self.main_app.current_rect

    def trim_point_edited(self):
        try:
            new_value = int(self.main_app.trim_point_label.text())
        except ValueError:
            return
            
        # Validate the input
        new_value = max(0, min(new_value, self.main_app.frame_count - 1))
        
        # Update the slider and video position
        self.main_app.slider.setValue(new_value)
        self.main_app.trim_points[self.main_app.current_video] = new_value
        self.main_app.cap.set(cv2.CAP_PROP_POS_FRAMES, new_value)
        
        # Update the display
        ret, frame = self.main_app.cap.read()
        if ret:
            self.display_frame(frame)
        
        # Mark as modified
        self.main_app.trim_modified = True
        self.main_app.check_current_video_item()


    def move_trim_to_click_position(self, event):
        if not self.main_app.cap:
            return
        pos = event.position().toPoint()
        slider_width = self.main_app.slider.width()
        frame_pos = int((pos.x() / slider_width) * self.main_app.frame_count)
        frame_pos = max(0, min(frame_pos, self.main_app.frame_count - 1))
        self.main_app.slider.setValue(frame_pos)
        self.main_app.trim_modified = True
        self.update_trim_label()
        self.main_app.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
        ret, frame = self.main_app.cap.read()
        if ret:
            self.display_frame(frame)

    def show_thumbnail(self, event):
        if not self.main_app.cap:
            return
        pos = event.position().toPoint()
        slider_width = self.main_app.slider.width()
        frame_pos = int((pos.x() / slider_width) * self.main_app.frame_count)
        frame_pos = max(0, min(frame_pos, self.main_app.frame_count - 1))
        self.main_app.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
        ret, frame = self.main_app.cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(q_img)
            thumbnail_height = 300
            thumbnail_width = int(thumbnail_height * self.main_app.clip_aspect_ratio)
            self.main_app.thumbnail_label.setFixedSize(thumbnail_width, thumbnail_height)
            self.main_app.thumbnail_image_label.setGeometry(0, 0, thumbnail_width, thumbnail_height)
            scaled_pixmap = pixmap.scaled(thumbnail_width, thumbnail_height, Qt.AspectRatioMode.KeepAspectRatio)
            self.main_app.thumbnail_image_label.setPixmap(scaled_pixmap)
            global_pos = self.main_app.slider.mapToGlobal(event.position().toPoint())
            self.main_app.thumbnail_label.move(global_pos.x() - thumbnail_width // 2, 
                                                 global_pos.y() - thumbnail_height - 10)
            self.main_app.thumbnail_label.show()

    def toggle_loop_playback(self):
        self.main_app.loop_playback = not self.main_app.loop_playback
        if self.main_app.loop_playback:
            self.start_loop_playback()
        else:
            self.stop_playback()

    def start_loop_playback(self):
        if self.main_app.cap and self.main_app.loop_playback:
            start = self.main_app.trim_points[self.main_app.current_video]
            end = start + self.main_app.trim_length
            current_frame = self.main_app.cap.get(cv2.CAP_PROP_POS_FRAMES)
            if current_frame >= end:
                self.main_app.cap.set(cv2.CAP_PROP_POS_FRAMES, start)
            ret, frame = self.main_app.cap.read()
            if ret:
                self.display_frame(frame)
                QTimer.singleShot(30, self.start_loop_playback)

    def toggle_play_forward(self):
        self.main_app.is_playing = not self.main_app.is_playing
        if self.main_app.is_playing:
            self.play_forward()
        else:
            self.stop_playback()

    def play_forward(self):
        if self.main_app.is_playing and self.main_app.cap:
            ret, frame = self.main_app.cap.read()
            if ret:
                current_frame = int(self.main_app.cap.get(cv2.CAP_PROP_POS_FRAMES))
                self.main_app.trim_points[self.main_app.current_video] = current_frame
                self.main_app.slider.setValue(current_frame)
                self.update_trim_label()
                self.display_frame(frame)
                QTimer.singleShot(30, self.play_forward)

    def stop_playback(self):
        self.main_app.is_playing = False
        self.main_app.loop_playback = False
        if self.main_app.cap:
            self.main_app.cap.set(cv2.CAP_PROP_POS_FRAMES, 
                                  self.main_app.trim_points.get(self.main_app.current_video, 0))

    def next_clip(self):
        current_idx = self.main_app.video_list.currentRow()
        new_idx = min(len(self.main_app.video_files) - 1, current_idx + 1)
        self.main_app.video_list.setCurrentRow(new_idx)
        self.main_app.loader.load_video(self.main_app.video_list.currentItem())

    def move_trim(self, step):
        new_val = self.main_app.slider.value() + step
        new_val = max(0, min(new_val, self.main_app.slider.maximum()))
        self.main_app.slider.setValue(new_val)
        self.update_trim_label()
        if self.main_app.cap:
            self.main_app.cap.set(cv2.CAP_PROP_POS_FRAMES, new_val)
            ret, frame = self.main_app.cap.read()
            if ret:
                self.display_frame(frame)

    def navigate_clip(self, direction):
        # Placeholder for additional navigation between clips if needed
        pass
