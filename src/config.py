import torch
from pathlib import Path

class Config:
    """All configurable parameters for the merged pipeline"""

    # NEW: ONNX model path (preferred)
    DFINE_ONNX_PATH = "weight/hgnetv2/best_stg2.onnx"
    
    # Optional: path to class names text file (one per line, in order)
    DFINE_CLASS_NAMES_PATH = "classes.txt"
    
    DFINE_TILE_SIZE = 1024
    DFINE_OVERLAP = 200
    DFINE_CONFIDENCE_THRESHOLD = 0.5
    DFINE_IOU_THRESHOLD = 0.5
    
    # ---------- VLM settings ----------
    VLM_MODEL = "qwen3-vl:30b-a3b-instruct"  # UPDATED: New 30B model with better accuracy
    VLM_DPI_LIST = [400, 500, 600]  # ENHANCED: Multi-DPI support for comparison
    VLM_TIMEOUT = 600  # INCREASED: More time for large images
    VLM_MAX_DIM = 4000  # INCREASED: Can handle larger images without tiling
    VLM_ENABLED = True  # NEW: Control VLM activation
    VLM_PROCESS_DPI_SEPARATELY = True  # NEW: Process each DPI separately, then combine
    VLM_MIN_COUNT_THRESHOLD = 2  # NEW: Only keep symbols appearing in 2+ DPI results
    
    # ---------- Vector extraction (PDF only) ----------
    VECTOR_FONT_PERCENTILE = 60
    
    # ---------- PDF rendering ----------
    PDF_DPI_FOR_DFINE = 300
    PDF_DPI_FOR_VLM = [300, 600]
    
    # ---------- Output - WORKSPACE DIRECTORY ----------
    OUTPUT_BASE_DIR = "outputs"
    
    # ---------- Device ----------
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # ---------- Colors for visualization ----------
    COLORS = [
        (0, 255, 0),    # Green
        (255, 0, 0),    # Blue
        (0, 0, 255),    # Red
        (255, 255, 0),  # Cyan
        (255, 0, 255),  # Magenta
        (0, 255, 255),  # Yellow
        (128, 0, 128),  # Purple
        (255, 165, 0),  # Orange
        (0, 128, 128),  # Teal
        (128, 128, 0)   # Olive
    ]
    
    @classmethod
    def update_paths(cls, onnx_path=None, output_dir=None):
        """Update paths dynamically (optional)"""
        if onnx_path:
            cls.DFINE_ONNX_PATH = onnx_path
        if output_dir:
            cls.OUTPUT_BASE_DIR = output_dir
    
    @classmethod
    def validate(cls):
        """Validate configuration"""
        errors = []
        if not Path(cls.DFINE_ONNX_PATH).exists():
            errors.append(f"DFINE ONNX model not found: {cls.DFINE_ONNX_PATH}")
        if cls.DFINE_CLASS_NAMES_PATH and not Path(cls.DFINE_CLASS_NAMES_PATH).exists():
            print(f"⚠️ Class names file not found: {cls.DFINE_CLASS_NAMES_PATH} (will use hardcoded list)")
        return errors
    
    @classmethod
    def ensure_output_dir(cls):
        """Create output directory if it doesn't exist"""
        output_path = Path(cls.OUTPUT_BASE_DIR)
        output_path.mkdir(parents=True, exist_ok=True)
        print(f"📁 Output directory ready: {output_path}")
        return str(output_path)