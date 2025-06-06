
# HunyClip - Video Cropping Tool

HunyClip is a Python-based video cropping tool aimed at Hunyuanvideo dataset preparation.


![Screenshot](screenshot.jpg) 

## Features

- **Trim Videos**: Set trim points and export trimmed clips.
- **Crop Videos**: Select and crop specific regions of video files.
- **NEW! - Crop Aspect limit**: For very specific crop dimensions.
- **Duplicate Videos**: Duplicate video entries so multiple cuts can be made from the same source.
- **Selective Exports**: Load entire folder but only export selected items instead of entire folder.
- **Export Options**: Export cropped and uncropped video clips along with images for auto-captioning.
- **Keyboard Shortcuts**: Easily navigate and control the tool using keyboard shortcuts.
- **Session saves**: Working session states are saved.
- **NEW! - Thumbnail view**: For easy preview scrubbing along the timeline

## Installation

### Prerequisites

- Python 3.8 or higher
- FFmpeg (Ensure it's installed and added to your system's PATH)


### Steps

1. **Clone the Repository**:
      ```bash
      git clone https://github.com/Tr1dae/HunyClip.git
      cd HunyClip
      ```

2. **Set Up Virtual Environment and Run**:
 
   Run the `Start.bat` script to install dependencies and run the application. It's all bundled.


## Usage

1. **Select Folder**: Click the "Select Folder" button to choose a folder containing video files.
2. **Load Video**: Click on a video file from the list to load it.
3. **Crop Region**: Click and drag on the video display to select the crop region.
4. **Set Trim Point**: Use the slider to set the trim point.
5. **Toggle Export settings**: Toggle uncropped export and image exports as needed.
6. **Export Videos**: Click the "Export Cropped Videos" button to export the cropped and trimmed videos.

### Keyboard Shortcuts

- **Z**: Preview trim section.
- **X**: Next clip.
- **C**: Play/Pause.
- **Q/W**: Adjust the trim point by a frame left and right. 

## Contributing

Contributions are welcome! Please fork the repository and create a pull request with your changes.

## Acknowledgments

- PyQt6 for the GUI framework.
- OpenCV and FFmpeg for video processing.
