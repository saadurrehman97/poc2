# Neptune Plumbing Symbol Extraction

A comprehensive pipeline for extracting plumbing symbols from engineering drawings using multiple extraction methods:

- **Vector Extraction**: Text-based extraction from PDF files
- **VLM (Vision Language Model)**: Image-based extraction using Ollama
- **DFINE Object Detection**: Deep learning-based symbol detection using ONNX

## Project Structure

```
neptune-plumbing/
├── src/
│   ├── config.py              # Configuration settings
│   ├── vector_extractor.py    # PDF vector text extraction
│   ├── vlm_extractor.py       # Vision Language Model extraction
│   ├── dfine_detector.py      # DFINE object detection pipeline
│   ├── symbol_validator.py    # Symbol validation and cleaning
│   ├── merger.py              # Result merging logic
│   └── pipeline.py            # Main pipeline orchestrator
├── data/
│   └── symbol_database.py     # Symbol definitions and mappings
├── weight/
│   └── hgnetv2/               # ONNX model files (download separately)
├── outputs/                   # Pipeline results
├── backup/                    # Jupyter notebooks for reference
├── assets/                    # Static assets for Streamlit
├── classes.txt                # Class names for DFINE detection
├── app.py                     # Streamlit frontend
├── quickstart.py              # Quick test script
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Installation

1. **Clone the repository**

```bash
git clone <repository-url>
cd neptune-plumbing
```

2. **Install Python dependencies**

```bash
pip install -r requirements.txt
```

3. **Download ONNX model files**

   Download the required ONNX models from this Google Drive:

   https://drive.google.com/drive/folders/1ZTTiDFxES9_PI_UiGyo9UfPZexESSIS5?usp=sharing

   Place the files according to paths specified in `src/config.py`:
   - Place ONNX model at: `weight/hgnetv2/`
   - Ensure the ONNX model in `DFINE_ONNX_PATH` in `src/config.py` is same as what placed at `weight/hgnetv2/`
   - Ensure `classes.txt` is in the root directory

4. **Setup Ollama (Optional - for VLM extraction)**

```bash
# Follow instructions at https://ollama.ai
ollama pull qwen2.5vl:7b
```

## Usage

### Command Line

```bash
# Process a PDF file
python src/pipeline.py /path/to/drawing.pdf

# Process an image file
python src/pipeline.py /path/to/drawing.png --output-dir ./results

# Quick test
python quickstart.py
```

### Streamlit Web Interface

```bash
streamlit run app.py
```

Then open http://localhost:8501 in your browser.

### Docker (Alternative)

```bash
docker-compose up
```

## Features

- **Multi-Method Extraction**: Combines vector, VLM, and object detection
- **Smart Merging**: Intelligent comparison and merging of results
- **PDF Support**: Full support for multi-page PDF drawings
- **Large Image Support**: Tiling system for processing large images
- **Interactive UI**: Streamlit-based web interface
- **Detailed Reports**: JSON reports with comparison and metadata
- **ONNX Runtime**: Fast inference using ONNX models

## Configuration

Edit `src/config.py` to customize:

- Model paths (ONNX model location)
- Detection thresholds and confidence scores
- DPI settings for PDF rendering
- Output directories
- Device (CPU/GPU)
- Tile size for large image processing

Key configuration paths:

- `DFINE_ONNX_PATH`: Path to ONNX model file
- `DFINE_CLASS_NAMES_PATH`: Path to classes.txt
- `OUTPUT_BASE_DIR`: Directory for output files

## Output

The pipeline generates:

- `merged_pipeline_results.json`: Complete analysis results
- `full_detected.jpg` or `page_XX_detected.jpg`: Annotated images
- Comparison table between extraction methods
- Best estimates for each symbol

## Requirements

- Python 3.8+
- ONNX Runtime (CPU or GPU)
- PyMuPDF (fitz) for PDF processing
- OpenCV, PIL, NumPy for image processing
- Streamlit for web interface
- (Optional) Ollama with qwen2.5vl:7b model for VLM extraction

## Training Context

For details on plumbing symbol detection model training, the following can be viewed:

- `/custom_detection.yml`

## Developers involved:

- Saim Kaleem
- Awais Ahmad
