# 📚 Manuscript Image Order Correction Tool

A Streamlit web application that automatically corrects alternating back-front scan ordering in manuscript images.

**Live Demo**: https://fileorder.streamlit.app/

## Features

- **Image Upload**: Upload multiple JPG, JPEG, or PNG images
- **Smart Reordering**: Automatically corrects alternating page scan patterns
- **Preview Comparison**: See before/after comparisons of the correction
- **Batch Download**: Download all corrected images as a ZIP file
- **Flexible Configuration**: Control how many images to exclude from correction

## Installation

### Requirements
- Python 3.8+
- pip

### Setup

1. Clone the repository:
```bash
git clone https://github.com/prnwork/File_Order_Correction_Tool.git
cd File_Order_Correction_Tool
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the Streamlit application:
```bash
streamlit run app.py
```

The application will open in your default browser at `http://localhost:8501`

### How to Use

1. **Upload Images**: Click "Upload Images" and select your manuscript page scans
2. **Set Correction Parameters**:
   - **Correct images at beginning**: Number of images at the start to skip correction
   - **Correct images at end**: Number of images at the end to skip correction
3. **Run Correction**: Click "🚀 Run Correction" to process the images
4. **Review**: Check the before/after comparison to verify the correction
5. **Download**: Click "📦 Download Corrected ZIP" to get your corrected images

## How It Works

The tool addresses a common scanning issue where manuscript pages are scanned in an alternating back-front pattern:
- Original order: [1F, 1B, 2F, 2B, 3F, 3B, ...]
- Corrected order: [1F, 2F, 3F, ..., 3B, 2B, 1B] (or appropriate sequence)

The reordering swaps consecutive pairs in the intermediate section:
- Images at the beginning and end are left untouched
- Intermediate images are reordered by swapping adjacent pairs

## Project Structure

```
.
├── app.py              # Main Streamlit application
├── logic.py            # Core image ordering logic
├── requirements.txt    # Python dependencies
├── .streamlit/         # Streamlit configuration
│   └── config.toml
└── README.md          # This file
```

## Dependencies

- **streamlit**: Web framework for the UI
- **Pillow**: Image processing and display

## License

This project is open source and available on GitHub.

## Support

For issues or feature requests, please open an issue on the GitHub repository.
