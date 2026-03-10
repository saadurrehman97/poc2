import os
import math
import traceback
from typing import List, Dict, Tuple
from collections import defaultdict

import numpy as np
import cv2
from PIL import Image
import onnxruntime as ort

from config import Config
from logger_setup import get_logger

logger = get_logger(__name__)

# ============================================================================
# ONNX Pipeline – exact same interface as the original DFINEPipeline
# ============================================================================
class DFINEPipeline:
    """Encapsulates DFINE model (ONNX) loading, tiling, detection, NMS, and drawing"""

    def __init__(self):
        self.sess = None
        self.class_names = {}          # id -> name (loaded from file/hardcoded)
        self.class_names_list = []      # list indexed by id
        self.device = Config.DEVICE

    def _load_class_names(self) -> Dict[int, str]:
        """
        Load class names from file (if exists) or use hardcoded list from training.
        Returns a dict id -> name.
        """
        # If a class names file is specified and exists, read it
        if hasattr(Config, 'DFINE_CLASS_NAMES_PATH') and Config.DFINE_CLASS_NAMES_PATH:
            path = Config.DFINE_CLASS_NAMES_PATH
            if os.path.exists(path):
                with open(path, 'r') as f:
                    names = [line.strip() for line in f if line.strip()]
                if names:
                    logger.info(f"   ✓ Loaded {len(names)} class names from {path}")
                    return {i: name for i, name in enumerate(names)}

        # Hardcoded list from your training output (36 classes)
        # This matches the order in your YAML config.
        hardcoded_names = [
            'aquastat', 'ball_valve', 'branch_bottom_connection',
            'branch_side_connection', 'branch_top_connection', 'check_valve', 'cleanout',
            'concealed_type_sprinkler_head', 'connect_to_existing', 'direction_of_flow',
            'drip_leg_valve', 'drop_in_piping', 'elbow', 'gas_cock', 'gate_valve',
            'hose_bibb', 'meter', 'pipe_anchor', 'pipe_connection', 'pipe_endcap',
            'pipe_guide', 'piping_break', 'point_of_connection', 'pressure_guage',
            'pressure_regulating_valve', 'pressure_relief_valve', 'rise_or_drop_in_piping',
            'riser_down_elbow', 'riser_up_elbow', 'riser_up_in_piping', 'screwed_union',
            'strainer', 'thermometer', 'two_way_modulating_valve', 'wall_hydrant',
            'water_meter'
        ]
        logger.info(f"   ✓ Using hardcoded list of {len(hardcoded_names)} class names")
        return {i: name for i, name in enumerate(hardcoded_names)}

    def load_model(self, onnx_path: str = None) -> bool:
        """
        Load the ONNX model and set up the inference session.
        """
        onnx_path = onnx_path or Config.DFINE_ONNX_PATH

        logger.info("🔵 Loading DFINE ONNX model...")
        logger.info(f"   ONNX file: {onnx_path}")
        logger.info(f"   Device:    {self.device}")

        if not os.path.exists(onnx_path):
            logger.error(f"ONNX model not found: {onnx_path}")
            return False

        try:
            # Choose execution providers
            providers = ['CPUExecutionProvider']
            if self.device.type == 'cuda':
                providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
            
            self.sess = ort.InferenceSession(onnx_path, providers=providers)
            logger.info(f"   ✓ ONNX session created. Using providers: {self.sess.get_providers()}")

            # Load class names
            self.class_names = self._load_class_names()
            self.class_names_list = [self.class_names[i] for i in sorted(self.class_names.keys())]
            logger.info(f"   ✓ Loaded {len(self.class_names)} class names")

            logger.info("✅ DFINE ONNX model loaded successfully")
            return True

        except Exception as e:
            logger.error(f"DFINE ONNX load failed: {e}")
            logger.debug(traceback.format_exc())
            return False

    @staticmethod
    def _resize_with_aspect_ratio(pil_img: Image.Image, size: int = 1024):
        """
        Resize image to `size` while keeping aspect ratio, pad to square.
        Returns:
            resized_padded_img: PIL Image of size (size, size)
            ratio: scaling factor (new_size / original_size)
            pad_w: padding added left
            pad_h: padding added top
        """
        orig_w, orig_h = pil_img.size
        ratio = min(size / orig_w, size / orig_h)
        new_w = int(orig_w * ratio)
        new_h = int(orig_h * ratio)
        
        resized = pil_img.resize((new_w, new_h), Image.BILINEAR)
        
        # Create a new square image and paste the resized one centered
        padded = Image.new("RGB", (size, size), (0, 0, 0))
        pad_w = (size - new_w) // 2
        pad_h = (size - new_h) // 2
        padded.paste(resized, (pad_w, pad_h))
        
        return padded, ratio, pad_w, pad_h

    # ------------------------------------------------------------------------
    # Tiling (unchanged from original)
    # ------------------------------------------------------------------------
    def tile_image(self, pil_image: Image.Image) -> Tuple[List[Image.Image], List[Tuple]]:
        width, height = pil_image.size
        tile_size = Config.DFINE_TILE_SIZE
        overlap = Config.DFINE_OVERLAP
        stride = tile_size - overlap

        n_tiles_x = max(1, math.ceil((width - overlap) / stride))
        n_tiles_y = max(1, math.ceil((height - overlap) / stride))

        tiles = []
        positions = []

        for y_idx in range(n_tiles_y):
            for x_idx in range(n_tiles_x):
                x_start = min(x_idx * stride, width - tile_size)
                y_start = min(y_idx * stride, height - tile_size)
                x_end = min(x_start + tile_size, width)
                y_end = min(y_start + tile_size, height)

                tile = pil_image.crop((x_start, y_start, x_end, y_end))
                tiles.append(tile)
                positions.append((x_start, y_start, x_end, y_end))

        return tiles, positions

    # ------------------------------------------------------------------------
    # Detection on a single tile (ONNX inference)
    # ------------------------------------------------------------------------
    def detect_on_tile(self, tile_pil: Image.Image, position: Tuple) -> List[Dict]:
        """
        Run ONNX inference on one tile.
        Expected model inputs: 'images', 'orig_target_sizes'
        Outputs: labels, boxes, scores (each as list of numpy arrays)
        """
        try:
            # Original tile size
            orig_w, orig_h = tile_pil.size

            # Preprocess: resize with aspect ratio to 1024x1024 (model input size)
            resized_tile, ratio, pad_w, pad_h = self._resize_with_aspect_ratio(tile_pil, 1024)

            # Convert to tensor: [0,1] float32, CHW, add batch dim
            img_np = np.array(resized_tile).astype(np.float32) / 255.0      # HWC, [0,1]
            img_np = np.transpose(img_np, (2, 0, 1))                        # CHW
            img_np = np.expand_dims(img_np, axis=0)                         # NCHW

            # orig_target_sizes: size after resizing (including padding) – both 1024
            target_size = np.array([[1024, 1024]], dtype=np.int64)

            # Run inference
            outputs = self.sess.run(
                output_names=None,
                input_feed={'images': img_np, 'orig_target_sizes': target_size}
            )
            # outputs: [labels, boxes, scores] each as list of batch elements
            labels = outputs[0][0] if isinstance(outputs[0], list) else outputs[0]
            boxes = outputs[1][0] if isinstance(outputs[1], list) else outputs[1]
            scores = outputs[2][0] if isinstance(outputs[2], list) else outputs[2]

            # Convert to numpy if they aren't already (ONNX Runtime returns numpy)
            if not isinstance(labels, np.ndarray):
                labels = np.array(labels)
            if not isinstance(boxes, np.ndarray):
                boxes = np.array(boxes)
            if not isinstance(scores, np.ndarray):
                scores = np.array(scores)

            # Filter by confidence threshold
            mask = scores > Config.DFINE_CONFIDENCE_THRESHOLD
            labels = labels[mask]
            boxes = boxes[mask]
            scores = scores[mask]

            if len(labels) == 0:
                return []

            # Convert boxes from padded coordinates to original tile coordinates
            # Boxes are absolute in the padded image (1024x1024). To get original tile coordinates:
            # 1. subtract padding
            # 2. divide by ratio
            x1_pad = boxes[:, 0] - pad_w
            y1_pad = boxes[:, 1] - pad_h
            x2_pad = boxes[:, 2] - pad_w
            y2_pad = boxes[:, 3] - pad_h

            x1_orig = x1_pad / ratio
            y1_orig = y1_pad / ratio
            x2_orig = x2_pad / ratio
            y2_orig = y2_pad / ratio

            # Clip to original tile bounds (optional, but safe)
            x1_orig = np.clip(x1_orig, 0, orig_w)
            y1_orig = np.clip(y1_orig, 0, orig_h)
            x2_orig = np.clip(x2_orig, 0, orig_w)
            y2_orig = np.clip(y2_orig, 0, orig_h)

            # Convert to global coordinates (add tile offset)
            x_start, y_start, _, _ = position
            x1_global = x1_orig + x_start
            y1_global = y1_orig + y_start
            x2_global = x2_orig + x_start
            y2_global = y2_orig + y_start

            # Build detection dicts
            detections = []
            for i in range(len(labels)):
                class_id = int(labels[i])
                class_name = self.class_names.get(class_id, f"class_{class_id}")
                detections.append({
                    'bbox': [float(x1_global[i]), float(y1_global[i]),
                             float(x2_global[i]), float(y2_global[i])],
                    'confidence': float(scores[i]),
                    'class_id': class_id,
                    'class_name': class_name,
                    'width': float(x2_orig[i] - x1_orig[i]),
                    'height': float(y2_orig[i] - y1_orig[i])
                })

            return detections

        except Exception as e:
            logger.debug(f"Detection error on tile: {e}")
            traceback.print_exc()
            return []

    # ------------------------------------------------------------------------
    # NMS (unchanged)
    # ------------------------------------------------------------------------
    def apply_nms(self, detections: List[Dict]) -> List[Dict]:
        if not detections:
            return []

        by_class = defaultdict(list)
        for d in detections:
            by_class[d['class_name']].append(d)

        filtered = []

        for cls, cls_dets in by_class.items():
            cls_dets.sort(key=lambda x: x['confidence'], reverse=True)
            boxes = np.array([d['bbox'] for d in cls_dets])
            x1 = boxes[:, 0]
            y1 = boxes[:, 1]
            x2 = boxes[:, 2]
            y2 = boxes[:, 3]
            areas = (x2 - x1 + 1) * (y2 - y1 + 1)
            indices = np.arange(len(boxes))
            keep = []

            while len(indices) > 0:
                i = indices[0]
                keep.append(i)
                if len(indices) == 1:
                    break

                xx1 = np.maximum(x1[i], x1[indices[1:]])
                yy1 = np.maximum(y1[i], y1[indices[1:]])
                xx2 = np.minimum(x2[i], x2[indices[1:]])
                yy2 = np.minimum(y2[i], y2[indices[1:]])

                w = np.maximum(0, xx2 - xx1 + 1)
                h = np.maximum(0, yy2 - yy1 + 1)
                intersection = w * h
                union = areas[i] + areas[indices[1:]] - intersection
                iou = intersection / union

                indices = indices[1:][iou <= Config.DFINE_IOU_THRESHOLD]

            for idx in keep:
                filtered.append(cls_dets[idx])

        return filtered

    # ------------------------------------------------------------------------
    # Drawing (unchanged)
    # ------------------------------------------------------------------------
    def draw_detections(self, image: np.ndarray, detections: List[Dict],
                       draw_labels: bool = True, line_thickness: int = 2,
                       font_scale: float = 0.5) -> np.ndarray:
        img = image.copy()

        for det in detections:
            x1, y1, x2, y2 = map(int, det['bbox'])
            class_name = det['class_name']
            conf = det['confidence']
            class_id = det['class_id']
            color = Config.COLORS[class_id % len(Config.COLORS)]

            cv2.rectangle(img, (x1, y1), (x2, y2), color, line_thickness)

            if draw_labels:
                label = f"{class_name[:15]} {conf:.2f}"
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)
                label_y = max(y1 - 5, th + 5)
                cv2.rectangle(img, (x1, label_y - th - 5), (x1 + tw, label_y), color, -1)
                cv2.putText(img, label, (x1, label_y - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), 1, cv2.LINE_AA)

        return img


# ----------------------------------------------------------------------------
# Convenience function (unchanged from original)
# ----------------------------------------------------------------------------
def extract_dfine_symbols(image_path: str, dfine_pipeline: DFINEPipeline = None) -> Dict[str, int]:
    """
    Complete DFINE extraction pipeline for image
    """
    logger.info("🔍 DFINE Object Detection")

    if dfine_pipeline is None:
        dfine_pipeline = DFINEPipeline()
        success = dfine_pipeline.load_model()
        if not success:
            logger.error("Failed to load DFINE model")
            return {}

    pil_image = Image.open(image_path).convert('RGB')
    tiles, positions = dfine_pipeline.tile_image(pil_image)

    all_detections = []
    for tile_pil, pos in zip(tiles, positions):
        tile_dets = dfine_pipeline.detect_on_tile(tile_pil, pos)
        all_detections.extend(tile_dets)

    filtered_detections = dfine_pipeline.apply_nms(all_detections)

    logger.info(f"✓ Found {len(filtered_detections)} objects after NMS")

    dfine_counts = defaultdict(int)
    for d in filtered_detections:
        dfine_counts[d['class_name']] += 1

    return dict(dfine_counts)


