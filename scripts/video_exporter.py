import os, ffmpeg, cv2
from PyQt6.QtWidgets import QMessageBox

class VideoExporter:
    def __init__(self, main_app):
        self.main_app = main_app
        self.file_counter = 0  # Counter for incremental padding suffix

    def write_caption(self, output_file):
        """
        If a simple caption was provided, write it into a .txt file with the same base name as output_file.
        """
        caption = getattr(self.main_app, 'simple_caption', '').strip()
        if caption:
            base, _ = os.path.splitext(output_file)
            txt_file = base + ".txt"
            with open(txt_file, "w") as f:
                f.write(caption)
            print(f"Exported caption for {output_file} to {txt_file}")

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
        
        # Reset file counter for each export session
        self.file_counter = 0

        # Loop through the video entries.
        for entry in self.main_app.video_files:
            video_path = entry["original_path"]
            display_name = entry["display_name"]
            crop = self.main_app.crop_regions.get(display_name)

            # Safely handle export_prefix
            prefix = getattr(self.main_app, 'export_prefix', '').strip()

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
                    prefix = getattr(self.main_app, 'export_prefix', '').strip()

                    # Fallback: if neither export cropped nor export uncropped flags are ticked,
                    # export both a cropped image (if valid crop exists) and an uncropped image.
                    if (not self.main_app.export_cropped_checkbox.isChecked() and 
                        not self.main_app.export_uncropped_checkbox.isChecked()):
                        
                        # Export cropped image to the "cropped" folder if a crop exists
                        if crop:
                            x, y, w, h = crop
                            if x < 0 or y < 0 or w <= 0 or h <= 0 or x+w > orig_w or y+h > orig_h:
                                print(f"Invalid crop region for {display_name}")
                            else:
                                cropped_frame = frame[y:y+h, x:x+w]
                                if cropped_frame.size == 0:
                                    print(f"Empty crop region for {display_name}")
                                else:
                                    if prefix:
                                        self.file_counter += 1
                                        cropped_image_name = f"{prefix}_{self.file_counter:05d}_cropped.png"
                                    else:
                                        cropped_image_name = f"{base_name}_cropped.png"
                                    cropped_image_path = os.path.join(output_folder, cropped_image_name)
                                    cv2.imwrite(cropped_image_path, cropped_frame)
                                    print(f"Exported cropped image for {display_name} to {cropped_image_path}")
                                    self.write_caption(cropped_image_path)
                        
                        # Export uncropped image to the "uncropped" folder
                        uncropped_folder = os.path.join(self.main_app.folder_path, "uncropped")
                        os.makedirs(uncropped_folder, exist_ok=True)
                        if prefix:
                            self.file_counter += 1
                            uncropped_image_name = f"{prefix}_{self.file_counter:05d}.png"
                        else:
                            uncropped_image_name = f"{base_name}.png"
                        uncropped_image_path = os.path.join(uncropped_folder, uncropped_image_name)
                        cv2.imwrite(uncropped_image_path, frame)
                        print(f"Exported uncropped image for {display_name} to {uncropped_image_path}")
                        self.write_caption(uncropped_image_path)
                    else:
                        # Existing behavior when either export cropped or export uncropped flags are ticked.
                        if crop and self.main_app.export_cropped_checkbox.isChecked():
                            x, y, w, h = crop
                            if x < 0 or y < 0 or w <= 0 or h <= 0 or x+w > orig_w or y+h > orig_h:
                                print(f"Invalid crop region for {display_name}")
                            else:
                                cropped_frame = frame[y:y+h, x:x+w]
                                if cropped_frame.size == 0:
                                    print(f"Empty crop region for {display_name}")
                                else:
                                    if prefix:
                                        self.file_counter += 1
                                        cropped_image_name = f"{prefix}_{self.file_counter:05d}_cropped.png"
                                    else:
                                        cropped_image_name = f"{base_name}_cropped.png"
                                    cropped_image_path = os.path.join(output_folder, cropped_image_name)
                                    cv2.imwrite(cropped_image_path, cropped_frame)
                                    print(f"Exported cropped image for {display_name} to {cropped_image_path}")
                                    self.write_caption(cropped_image_path)
                        if self.main_app.export_uncropped_checkbox.isChecked():
                            uncropped_folder = os.path.join(self.main_app.folder_path, "uncropped")
                            os.makedirs(uncropped_folder, exist_ok=True)
                            if prefix:
                                self.file_counter += 1
                                uncropped_image_name = f"{prefix}_{self.file_counter:05d}.png"
                            else:
                                uncropped_image_name = f"{base_name}.png"
                            uncropped_image_path = os.path.join(uncropped_folder, uncropped_image_name)
                            cv2.imwrite(uncropped_image_path, frame)
                            print(f"Exported uncropped image for {display_name} to {uncropped_image_path}")
                            self.write_caption(uncropped_image_path)





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

                    base_name, ext = os.path.splitext(display_name)
                    prefix = getattr(self.main_app, 'export_prefix', '').strip()

                    # Full name replacement: ignore original name if prefix is provided
                    if prefix:
                        self.file_counter += 1
                        output_name = f"{prefix}_{self.file_counter:05d}_cropped{ext}"
                    else:
                        output_name = f"{base_name}_cropped{ext}"

                    output_path = os.path.join(output_folder, output_name)

                    end_frame = trim_start + self.main_app.trim_length
                    (
                        ffmpeg.input(video_path)
                        .filter('trim', start_frame=trim_start, end_frame=end_frame)
                        .filter('setpts', 'PTS-STARTPTS')
                        .filter('crop', w, h, x, y)
                        .filter('scale', self.main_app.longest_edge, -2)
                        .output(output_path, map_metadata='-1')
                        .run(overwrite_output=True)
                    )

                    print(f"Exported cropped {display_name} to {output_path}")
                    self.write_caption(output_path)



            if self.main_app.export_uncropped_checkbox.isChecked():
                base_name, ext = os.path.splitext(display_name)
                prefix = getattr(self.main_app, 'export_prefix', '').strip()

                # Full name replacement: use export_prefix and counter if provided
                if prefix:
                    self.file_counter += 1
                    uncropped_name = f"{prefix}_{self.file_counter:05d}{ext}"
                else:
                    uncropped_name = f"{base_name}{ext}"

                uncropped_path = os.path.join(uncropped_folder, uncropped_name)

                end_frame = trim_start + self.main_app.trim_length
                (
                    ffmpeg.input(video_path)
                    .filter('trim', start_frame=trim_start, end_frame=end_frame)
                    .filter('setpts', 'PTS-STARTPTS')
                    .output(uncropped_path, map_metadata='-1')
                    .run(overwrite_output=True)
                )

                print(f"Exported uncropped {display_name} to {uncropped_path}")
                self.write_caption(uncropped_path)



            cap.release()
