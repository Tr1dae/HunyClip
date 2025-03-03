import os, ffmpeg, cv2
from PyQt6.QtWidgets import QMessageBox

class VideoExporter:
    def __init__(self, main_app):
        self.main_app = main_app

    def export_videos(self):
        # Check toggles and warn if needed.
        if not self.main_app.export_uncropped_checkbox.isChecked():
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setText("Uncropped clips will not be exported.")
            msg.setInformativeText("Toggle 'Export Uncropped Clips' to export all clips.")
            msg.setWindowTitle("Export Warning")
            continue_button = msg.addButton("Continue Anyway", QMessageBox.ButtonRole.AcceptRole)
            return_button = msg.addButton("Return", QMessageBox.ButtonRole.RejectRole)
            msg.exec()
            if msg.clickedButton() == return_button:
                return

        if not self.main_app.export_cropped_checkbox.isChecked():
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setText("Cropped clips will not be exported.")
            msg.setInformativeText("Toggle 'Export Cropped Clips' to export cropped clips.")
            msg.setWindowTitle("Export Warning")
            continue_button = msg.addButton("Continue Anyway", QMessageBox.ButtonRole.AcceptRole)
            return_button = msg.addButton("Return", QMessageBox.ButtonRole.RejectRole)
            msg.exec()
            if msg.clickedButton() == return_button:
                return

        output_folder = os.path.join(self.main_app.folder_path, "cropped")
        os.makedirs(output_folder, exist_ok=True)
        if self.main_app.export_uncropped_checkbox.isChecked():
            uncropped_folder = os.path.join(self.main_app.folder_path, "uncropped")
            os.makedirs(uncropped_folder, exist_ok=True)
        
        # Loop through the video entries.
        for entry in self.main_app.video_files:
            video_path = entry["original_path"]
            display_name = entry["display_name"]
            crop = self.main_app.crop_regions.get(display_name)
            # Instead of reading the check state from the QListWidget item,
            # use the export_enabled flag stored in the entry.
            if not entry.get("export_enabled", False):
                continue

            cap = cv2.VideoCapture(video_path)
            orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            trim_start = self.main_app.trim_points.get(display_name, 0)
            duration = self.main_app.trim_length / fps

            if self.main_app.export_image_checkbox.isChecked():
                cap.set(cv2.CAP_PROP_POS_FRAMES, trim_start)
                ret, frame = cap.read()
                if ret:
                    base_name = os.path.splitext(display_name)[0]
                    if crop:
                        x, y, w, h = crop
                        if x < 0 or y < 0 or w <= 0 or h <= 0 or x+w > orig_w or y+h > orig_h:
                            print(f"Invalid crop region for {display_name}")
                            continue
                        cropped_frame = frame[y:y+h, x:x+w]
                        if cropped_frame.size == 0:
                            print(f"Empty crop region for {display_name}")
                            continue
                        cropped_image_name = f"{base_name}_cropped.png"
                        cropped_image_path = os.path.join(output_folder, cropped_image_name)
                        cv2.imwrite(cropped_image_path, cropped_frame)
                        print(f"Exported cropped image for {display_name} to {cropped_image_path}")
                    if self.main_app.export_uncropped_checkbox.isChecked():
                        uncropped_image_name = f"{base_name}.png"
                        uncropped_image_path = os.path.join(uncropped_folder, uncropped_image_name)
                        cv2.imwrite(uncropped_image_path, frame)
                        print(f"Exported uncropped image for {display_name} to {uncropped_image_path}")

            if self.main_app.export_cropped_checkbox.isChecked() and crop:
                x, y, w, h = crop
                if x < 0 or y < 0 or w <= 0 or h <= 0 or x+w > orig_w or y+h > orig_h:
                    print(f"Invalid crop region for {display_name}")
                else:
                    if self.main_app.longest_edge % 2 != 0:
                        self.main_app.longest_edge -= 1
                    if h % 2 != 0:
                        h -= 1
                    if w % 2 != 0:
                        w -= 1
                    output_name = display_name.replace('.', '_cropped.')
                    output_path = os.path.join(output_folder, output_name)
                    (ffmpeg.input(video_path, ss=trim_start/fps, t=duration)
                        .filter('crop', w, h, x, y)
                        .filter('scale', self.main_app.longest_edge, -2)
                        .output(output_path)
                        .run(overwrite_output=True))
                    print(f"Exported cropped {display_name} to {output_path}")

            if self.main_app.export_uncropped_checkbox.isChecked():
                uncropped_path = os.path.join(uncropped_folder, display_name)
                (ffmpeg.input(video_path, ss=trim_start/fps, t=duration)
                    .output(uncropped_path)
                    .run(overwrite_output=True))
                print(f"Exported uncropped {display_name} to {uncropped_path}")

            cap.release()
