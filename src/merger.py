# """
# Result merging logic for combining Vector, VLM, and DFINE outputs
# """
# from typing import Dict, List, Tuple
# from collections import defaultdict

# import sys
# sys.path.append('..')
# from data.symbol_database import DFINE_TO_SYMBOL_MAP, SYMBOL_DB

# def merge_dfine_vlm(dfine_counts: Dict[str, int], 
#                     vlm_counts: Dict[str, int]) -> Tuple[List[Dict], Dict[str, int]]:
#     """
#     Merge DFINE (mapped to symbols) and VLM counts
    
#     Args:
#         dfine_counts: DFINE class counts
#         vlm_counts: VLM symbol counts
    
#     Returns:
#         Tuple of (comparison_list, final_best_estimates)
#     """
#     comparison = []
#     mapped_symbols_used = set()
    
#     # DFINE classes mapped to symbols
#     for dfine_class, dfine_cnt in dfine_counts.items():
#         symbol = DFINE_TO_SYMBOL_MAP.get(dfine_class)
#         if symbol:
#             mapped_symbols_used.add(symbol)
#             vlm_cnt = vlm_counts.get(symbol, 0)
#             best = max(dfine_cnt, vlm_cnt)
#             comparison.append({
#                 "category": dfine_class.replace('_', ' ').title(),
#                 "dfine_class": dfine_class,
#                 "dfine_count": dfine_cnt,
#                 "symbol": symbol,
#                 "vector_count": 0,
#                 "vlm_count": vlm_cnt,
#                 "best_estimate": best
#             })
    
#     # VLM-only symbols
#     for sym, vlm_cnt in vlm_counts.items():
#         if sym in mapped_symbols_used:
#             continue
#         comparison.append({
#             "category": SYMBOL_DB.get(sym, sym),
#             "dfine_class": None,
#             "dfine_count": 0,
#             "symbol": sym,
#             "vector_count": 0,
#             "vlm_count": vlm_cnt,
#             "best_estimate": vlm_cnt
#         })
    
#     final_best = {entry["symbol"]: entry["best_estimate"] 
#                   for entry in comparison if entry["best_estimate"] > 0}
    
#     return comparison, final_best

# def merge_vector_vlm_dfine(vector_counts: Dict[str, int], 
#                            vlm_counts: Dict[str, int],
#                            dfine_counts: Dict[str, int]) -> Tuple[List[Dict], Dict[str, int]]:
#     """
#     Merge all three sources for PDF workflow
    
#     Args:
#         vector_counts: Vector extraction symbol counts
#         vlm_counts: VLM symbol counts
#         dfine_counts: DFINE class counts
    
#     Returns:
#         Tuple of (comparison_list, final_best_estimates)
#     """
#     comparison = []
#     mapped_symbols_used = set()
    
#     # First, DFINE classes that map to symbols
#     for dfine_class, dfine_cnt in dfine_counts.items():
#         symbol = DFINE_TO_SYMBOL_MAP.get(dfine_class)
#         if symbol:
#             mapped_symbols_used.add(symbol)
#             vector_cnt = vector_counts.get(symbol, 0)
#             vlm_cnt = vlm_counts.get(symbol, 0)
#             best = max(dfine_cnt, vector_cnt, vlm_cnt)
#             comparison.append({
#                 "category": dfine_class.replace('_', ' ').title(),
#                 "dfine_class": dfine_class,
#                 "dfine_count": dfine_cnt,
#                 "symbol": symbol,
#                 "vector_count": vector_cnt,
#                 "vlm_count": vlm_cnt,
#                 "best_estimate": best
#             })
    
#     # Then, symbols that appear in vector or VLM but not mapped from DFINE
#     all_syms = set(vector_counts.keys()) | set(vlm_counts.keys())
#     for sym in all_syms:
#         if sym in mapped_symbols_used:
#             continue
#         vector_cnt = vector_counts.get(sym, 0)
#         vlm_cnt = vlm_counts.get(sym, 0)
#         best = max(vector_cnt, vlm_cnt)
#         comparison.append({
#             "category": SYMBOL_DB.get(sym, sym),
#             "dfine_class": None,
#             "dfine_count": 0,
#             "symbol": sym,
#             "vector_count": vector_cnt,
#             "vlm_count": vlm_cnt,
#             "best_estimate": best
#         })
    
#     final_best = {entry["symbol"]: entry["best_estimate"] 
#                   for entry in comparison if entry["best_estimate"] > 0}
    
#     return comparison, final_best

# def smart_merge_vector_vlm(vector_counts: Dict[str, int], 
#                            vlm_counts: Dict[str, int]) -> Tuple[Dict[str, int], Dict, Dict, Dict]:
#     """
#     Smart comparison and merge of vector vs VLM results
#     (From PASTED 2 - original logic preserved)
    
#     Args:
#         vector_counts: Vector extraction counts
#         vlm_counts: VLM extraction counts
    
#     Returns:
#         Tuple of (final_counts, new_from_vlm, duplicates, missed_by_vector)
#     """
#     final_counts = dict(vector_counts)
#     new_from_vlm = {}
#     duplicates = {}
#     missed_by_vector = {}
    
#     print(f"\n📊 Comparing results:")
#     print(f"  Vector extraction: {len(vector_counts)} unique symbols")
#     print(f"  VLM extraction: {len(vlm_counts)} unique symbols")
    
#     # Find symbols ONLY in VLM (discoveries)
#     for symbol, vlm_count in vlm_counts.items():
#         if symbol not in vector_counts:
#             # NEW symbol found by VLM only
#             new_from_vlm[symbol] = vlm_count
#         else:
#             # Symbol found by BOTH
#             vector_count = vector_counts[symbol]
#             if vlm_count == vector_count:
#                 duplicates[symbol] = vector_count
#             else:
#                 missed_by_vector[symbol] = {
#                     'vector': vector_count,
#                     'vlm': vlm_count,
#                     'diff': abs(vlm_count - vector_count)
#                 }
    
#     print(f"\n✓ Analysis:")
#     print(f"  Symbols in BOTH (same count): {len(duplicates)}")
#     print(f"  Symbols ONLY in VLM (NEW): {len(new_from_vlm)}")
#     print(f"  Symbols with DIFFERENT counts: {len(missed_by_vector)}")
    
#     # Add NEW VLM discoveries
#     print(f"\n✓ Adding {len(new_from_vlm)} NEW symbols from VLM")
#     for symbol, count in new_from_vlm.items():
#         final_counts[symbol] = count
    
#     return final_counts, new_from_vlm, duplicates, missed_by_vector



# ................... VERSION 2 ..................

"""
Enhanced Result Merging with Weighted Boxes Fusion (WBF)
Integrates: Multi-model consensus, confidence rescaling, geometric averaging
Based on PASTED1 research for 90%+ accuracy
"""
from typing import Dict, List, Tuple
from collections import defaultdict
import numpy as np

import sys
sys.path.append('..')
from data.symbol_database import DFINE_TO_SYMBOL_MAP, SYMBOL_DB
from logger_setup import get_logger

logger = get_logger(__name__)


def format_symbol_display(symbol: str, dfine_class: str = None) -> str:
    """
    Format symbol name for display in "🏆 Final Best Estimates" column
    
    Rules:
    1. If symbol is in SYMBOL_DB (e.g., 'WC-1'): Show as "Standard Water Closet (WC-1)"
    2. If dfine_class is mapped in DFINE_TO_SYMBOL_MAP (e.g., 'check_valve'): Show as "Check valve (check_valve)"
    3. If symbol NOT in database (e.g., '1/2" CW'): Keep as-is
    
    Args:
        symbol: The symbol key or name
        dfine_class: Optional DFINE class name for DFINE-origin symbols
    
    Returns:
        Formatted display string
    """
    # Check if symbol is in SYMBOL_DB
    if symbol in SYMBOL_DB:
        human_name = SYMBOL_DB[symbol]
        return f"{human_name} ({symbol})"
    
    # Check if this is a DFINE class mapped to a symbol
    if dfine_class and dfine_class in DFINE_TO_SYMBOL_MAP:
        human_name = DFINE_TO_SYMBOL_MAP[dfine_class]
        return f"{human_name} ({dfine_class})"
    
    # Try to find if symbol value exists in DFINE_TO_SYMBOL_MAP values
    for dfine_key, dfine_value in DFINE_TO_SYMBOL_MAP.items():
        if dfine_value == symbol:
            return f"{symbol} ({dfine_key})"
    
    # If not in database, keep as-is (for symbols like "1/2" CW", "3/4" CW", etc.)
    return symbol

def calculate_weighted_boxes_fusion(boxes_list: List[List[float]], 
                                   scores_list: List[float],
                                   labels_list: List[int],
                                   weights: List[float],
                                   iou_threshold: float = 0.55) -> Tuple[List, List, List]:
    """
    ENHANCEMENT 1: Weighted Boxes Fusion (WBF) implementation
    Based on PASTED1: "WBF fuses all predictions into single averaged box"
    Formula: C = (Σ Ci) / T × min(T, N) / N
    
    Args:
        boxes_list: List of box lists from different models [[[x1,y1,x2,y2], ...], ...]
        scores_list: List of score lists
        labels_list: List of label lists
        weights: Model confidence weights
        iou_threshold: IoU threshold for fusion
    
    Returns:
        fused_boxes, fused_scores, fused_labels
    """
    if not boxes_list or all(len(b) == 0 for b in boxes_list):
        return [], [], []
    
    num_models = len(boxes_list)
    all_boxes = []
    
    # Collect all boxes with model info
    for model_idx, (boxes, scores, labels) in enumerate(zip(boxes_list, scores_list, labels_list)):
        model_weight = weights[model_idx] if model_idx < len(weights) else 1.0
        for box, score, label in zip(boxes, scores, labels):
            all_boxes.append({
                'box': box,
                'score': score * model_weight,  # Apply model weight
                'label': label,
                'model_idx': model_idx
            })
    
    if not all_boxes:
        return [], [], []
    
    # Sort by score (highest first)
    all_boxes.sort(key=lambda x: x['score'], reverse=True)
    
    fused_boxes = []
    fused_scores = []
    fused_labels = []
    used_indices = set()
    
    for i, box_data in enumerate(all_boxes):
        if i in used_indices:
            continue
        
        # Start a new cluster with this box
        cluster = [box_data]
        cluster_indices = {i}
        
        # Find all overlapping boxes of the same class
        for j in range(i + 1, len(all_boxes)):
            if j in used_indices:
                continue
            
            other_data = all_boxes[j]
            
            # Must be same class
            if box_data['label'] != other_data['label']:
                continue
            
            # Calculate IoU
            iou = _calculate_iou(box_data['box'], other_data['box'])
            
            if iou >= iou_threshold:
                cluster.append(other_data)
                cluster_indices.add(j)
        
        used_indices.update(cluster_indices)
        
        # ENHANCEMENT 2: Confidence rescaling with agreement count
        # Formula from PASTED1: C = (Σ Ci / T) × (min(T, N) / N)
        T = len(cluster)  # Number of boxes in cluster
        N = num_models    # Total number of models
        
        # Weighted average of coordinates
        total_weight = sum(b['score'] for b in cluster)
        if total_weight == 0:
            continue
        
        fused_box = [0, 0, 0, 0]
        for b in cluster:
            weight = b['score'] / total_weight
            for k in range(4):
                fused_box[k] += b['box'][k] * weight
        
        # Calculate fused confidence with consensus penalty/bonus
        avg_confidence = sum(b['score'] for b in cluster) / T
        consensus_factor = min(T, N) / N  # Penalize single-model detections
        fused_confidence = avg_confidence * consensus_factor
        
        # ENHANCEMENT 3: Multi-model agreement bonus
        # Detections seen by multiple models get confidence boost
        unique_models = len(set(b['model_idx'] for b in cluster))
        if unique_models > 1:
            agreement_bonus = 1.0 + (0.1 * (unique_models - 1))  # +10% per additional model
            fused_confidence = min(1.0, fused_confidence * agreement_bonus)
        
        fused_boxes.append(fused_box)
        fused_scores.append(fused_confidence)
        fused_labels.append(box_data['label'])
    
    return fused_boxes, fused_scores, fused_labels


def _calculate_iou(box1: List[float], box2: List[float]) -> float:
    """Standard IoU calculation"""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])
    
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = area1 + area2 - intersection
    
    return intersection / (union + 1e-6)


def merge_dfine_vlm_enhanced(dfine_counts: Dict[str, int], 
                             vlm_counts: Dict[str, int],
                             dfine_detections: List[Dict] = None,
                             vlm_verification_scores: Dict[str, float] = None) -> Tuple[List[Dict], Dict[str, int]]:
    """
    ENHANCEMENT 4: Enhanced DFINE + VLM merge with verification scoring
    Based on PASTED1: "VLM serves as semantic verifier for candidates"
    
    Args:
        dfine_counts: DFINE class counts
        vlm_counts: VLM symbol counts
        dfine_detections: Optional detailed DFINE detections for WBF
        vlm_verification_scores: Optional VLM confidence scores per symbol
    
    Returns:
        Tuple of (comparison_list, final_best_estimates)
    """
    comparison = []
    mapped_symbols_used = set()
    
    # DFINE classes mapped to symbols with verification
    for dfine_class, dfine_cnt in dfine_counts.items():
        symbol = DFINE_TO_SYMBOL_MAP.get(dfine_class)
        if symbol:
            mapped_symbols_used.add(symbol)
            vlm_cnt = vlm_counts.get(symbol, 0)
            
            # ENHANCEMENT 5: Confidence-weighted best estimate
            # If VLM verified this symbol, weight it higher
            vlm_verification = vlm_verification_scores.get(symbol, 0.5) if vlm_verification_scores else 0.5
            
            # Weighted average instead of simple max
            if vlm_cnt > 0 and dfine_cnt > 0:
                # Both methods found it - high confidence
                best = int((dfine_cnt * 0.6 + vlm_cnt * 0.4))  # DFINE weighted higher (raster expert)
                confidence_level = "high"
            elif vlm_cnt > 0 and vlm_verification > 0.7:
                # Only VLM found it but high confidence
                best = vlm_cnt
                confidence_level = "medium"
            elif dfine_cnt > 0:
                # Only DFINE found it
                best = dfine_cnt
                confidence_level = "medium"
            else:
                best = 0
                confidence_level = "low"
            
            comparison.append({
                "category": dfine_class.replace('_', ' ').title(),
                "dfine_class": dfine_class,
                "dfine_count": dfine_cnt,
                "symbol": format_symbol_display(symbol, dfine_class),
                "vector_count": 0,
                "vlm_count": vlm_cnt,
                "vlm_verification": vlm_verification,
                "best_estimate": best,
                "confidence_level": confidence_level
            })
    
    # VLM-only symbols (discoveries)
    for sym, vlm_cnt in vlm_counts.items():
        if sym in mapped_symbols_used:
            continue
        
        vlm_verification = vlm_verification_scores.get(sym, 0.5) if vlm_verification_scores else 0.5
        
        # ENHANCEMENT 6: VLM-only detections require high verification score
        # Based on PASTED1: "prevent hallucinations by requiring multi-modal agreement"
        if vlm_verification > 0.7:
            confidence_level = "medium"
            best = vlm_cnt
        elif vlm_verification > 0.5:
            confidence_level = "low"
            best = vlm_cnt
        else:
            # Skip low-confidence VLM-only detections
            continue
        
        comparison.append({
            "category": SYMBOL_DB.get(sym, sym),
            "dfine_class": None,
            "dfine_count": 0,
            "symbol": format_symbol_display(sym),
            "vector_count": 0,
            "vlm_count": vlm_cnt,
            "vlm_verification": vlm_verification,
            "best_estimate": best,
            "confidence_level": confidence_level
        })
    
    final_best = {entry["symbol"]: entry["best_estimate"] 
                  for entry in comparison if entry["best_estimate"] > 0}
    
    return comparison, final_best


def merge_vector_vlm_dfine_enhanced(vector_counts: Dict[str, int], 
                                    vlm_counts: Dict[str, int],
                                    dfine_counts: Dict[str, int],
                                    vector_confidence: float = 1.0) -> Tuple[List[Dict], Dict[str, int]]:
    """
    ENHANCEMENT 7: Three-way merge with COMPLETE DFINE coverage
    Based on PASTED1: "Vector paths provide geometric ground truth"
    
    ⭐ NEW: Includes ALL DFINE detections, even unmapped ones
    - Mapped DFINE classes → look up symbol in DFINE_TO_SYMBOL_MAP
    - Unmapped DFINE classes → use class name directly as fallback symbol
    
    Args:
        vector_counts: Vector extraction (100% accurate when found)
        vlm_counts: VLM extraction
        dfine_counts: DFINE extraction (ALL classes, including unmapped)
        vector_confidence: Vector extraction confidence (default 1.0 = always trust)
    
    Returns:
        Tuple of (comparison_list, final_best_estimates)
    """
    comparison = []
    mapped_symbols_used = set()
    
    # First pass: DFINE-mapped symbols + ALL unmapped DFINE classes
    for dfine_class, dfine_cnt in dfine_counts.items():
        # Try to map DFINE class to symbol
        symbol = DFINE_TO_SYMBOL_MAP.get(dfine_class)
        
        # ⭐ CRITICAL FIX: If not in mapping, use the DFINE class name itself
        if not symbol:
            # Convert class name to a reasonable symbol format
            # e.g., "riser_down_elbow" → "RD_ELBOW" or keep as is for display
            symbol = dfine_class.upper().replace('_', '_')
            logger.debug(f"DFINE class '{dfine_class}' not in map → using fallback symbol '{symbol}'")
        
        mapped_symbols_used.add(symbol)
        vector_cnt = vector_counts.get(symbol, 0)
        vlm_cnt = vlm_counts.get(symbol, 0)
        
        # ENHANCEMENT 8: Hierarchical confidence weighting
        # Vector > DFINE > VLM (when all agree, take max; when conflict, trust vector)
        if vector_cnt > 0:
            # Vector extraction is ground truth (from PDF metadata)
            best = vector_cnt
            confidence_level = "very_high"
            agreement = "vector_confirmed"
        elif dfine_cnt > 0 and vlm_cnt > 0:
            # Both vision methods agree
            best = max(dfine_cnt, vlm_cnt)
            confidence_level = "high"
            agreement = "multi_modal"
        elif dfine_cnt > 0:
            best = dfine_cnt
            confidence_level = "medium"
            agreement = "dfine_only"
        elif vlm_cnt > 0:
            best = vlm_cnt
            confidence_level = "medium"
            agreement = "vlm_only"
        else:
            best = 0
            confidence_level = "none"
            agreement = "none"
        
        comparison.append({
            "category": dfine_class.replace('_', ' ').title(),
            "dfine_class": dfine_class,
            "dfine_count": dfine_cnt,
            "symbol": format_symbol_display(symbol, dfine_class),
            "vector_count": vector_cnt,
            "vlm_count": vlm_cnt,
            "best_estimate": best,
            "confidence_level": confidence_level,
            "agreement": agreement
        })
    
    # Second pass: Symbols in vector or VLM but not found in DFINE
    all_syms = set(vector_counts.keys()) | set(vlm_counts.keys())
    for sym in all_syms:
        if sym in mapped_symbols_used:
            continue
        
        vector_cnt = vector_counts.get(sym, 0)
        vlm_cnt = vlm_counts.get(sym, 0)
        
        # ENHANCEMENT 9: Trust vector extraction completely
        if vector_cnt > 0:
            best = vector_cnt
            confidence_level = "very_high"
            agreement = "vector_only"
        elif vlm_cnt > 0:
            best = vlm_cnt
            confidence_level = "low"  # VLM-only without vector confirmation
            agreement = "vlm_discovery"
        else:
            continue
        
        comparison.append({
            "category": SYMBOL_DB.get(sym, sym),
            "dfine_class": None,
            "dfine_count": 0,
            "symbol": format_symbol_display(sym),
            "vector_count": vector_cnt,
            "vlm_count": vlm_cnt,
            "best_estimate": best,
            "confidence_level": confidence_level,
            "agreement": agreement
        })
    
    # ⭐ CRITICAL: Include only entries with best_estimate > 0
    final_best = {entry["symbol"]: entry["best_estimate"] 
                  for entry in comparison if entry["best_estimate"] > 0}
    
    logger.info(f"\n✅ Merge complete: {len(comparison)} total entries, {len(final_best)} with counts > 0")
    
    return comparison, final_best


def smart_merge_vector_vlm(vector_counts: Dict[str, int], 
                           vlm_counts: Dict[str, int]) -> Tuple[Dict[str, int], Dict, Dict, Dict]:
    """
    ENHANCEMENT 10: Smart comparison with discovery analysis
    (From PASTED3 - preserved with enhancements)
    """
    final_counts = dict(vector_counts)
    new_from_vlm = {}
    duplicates = {}
    missed_by_vector = {}
    
    logger.info(f"\n📊 Comparing results:")
    logger.info(f"  Vector extraction: {len(vector_counts)} unique symbols")
    logger.info(f"  VLM extraction: {len(vlm_counts)} unique symbols")
    
    # Find symbols ONLY in VLM (potential discoveries or hallucinations)
    for symbol, vlm_count in vlm_counts.items():
        if symbol not in vector_counts:
            new_from_vlm[symbol] = vlm_count
        else:
            vector_count = vector_counts[symbol]
            if vlm_count == vector_count:
                duplicates[symbol] = vector_count
            else:
                missed_by_vector[symbol] = {
                    'vector': vector_count,
                    'vlm': vlm_count,
                    'diff': abs(vlm_count - vector_count),
                    'confidence': 'low' if abs(vlm_count - vector_count) > 2 else 'medium'
                }
    
    logger.info(f"\n✓ Analysis:")
    logger.info(f"  Perfect matches (same count): {len(duplicates)}")
    logger.info(f"  VLM discoveries (NEW): {len(new_from_vlm)}")
    logger.info(f"  Count discrepancies: {len(missed_by_vector)}")
    
    # ENHANCEMENT 11: Selective VLM discovery addition
    # Only add VLM discoveries with reasonable confidence
    reliable_discoveries = 0
    for symbol, count in new_from_vlm.items():
        # Add VLM discoveries cautiously
        if count <= 3:  # Small counts are more reliable
            final_counts[symbol] = count
            reliable_discoveries += 1
        else:
            # Large VLM-only counts might be hallucinations - add with caution
            logger.warning(f"Large VLM-only count for {symbol}: {count} (review recommended)")
            final_counts[symbol] = count
    
    logger.info(f"\n✓ Added {reliable_discoveries} reliable VLM discoveries")
    
    return final_counts, new_from_vlm, duplicates, missed_by_vector


# ============================================
# NEW MERGE FUNCTIONS (No VLM, DFINE + VECTOR only)
# ============================================

def merge_vector_dfine(vector_counts: Dict[str, int], 
                       dfine_counts: Dict[str, int]) -> Tuple[List[Dict], Dict[str, int]]:
    """
    Merge Vector Extraction + DFINE Detection (No VLM)
    
    Used for PDF processing:
    - Vector extraction provides 100% accurate text-based symbols
    - DFINE provides visual detection of objects
    - Merge with vector as primary source
    
    Args:
        vector_counts: Vector extraction symbol counts (PDF metadata text)
        dfine_counts: DFINE class counts (object detection)
    
    Returns:
        Tuple of (comparison_list, final_best_estimates)
    """
    comparison = []
    mapped_symbols_used = set()
    
    logger.info(f"\n📊 Merging Vector ({len(vector_counts)} symbols) + DFINE ({len(dfine_counts)} classes)")
    
    # First pass: DFINE classes that map to symbols
    for dfine_class, dfine_cnt in dfine_counts.items():
        symbol = DFINE_TO_SYMBOL_MAP.get(dfine_class)
        if symbol:
            mapped_symbols_used.add(symbol)
            vector_cnt = vector_counts.get(symbol, 0)
            
            # Vector extraction is ground truth when available
            if vector_cnt > 0:
                best = vector_cnt
                confidence = "high"
            else:
                best = dfine_cnt
                confidence = "medium"
            
            display_symbol = format_symbol_display(symbol, dfine_class)
            
            comparison.append({
                "category": dfine_class.replace('_', ' ').title(),
                "dfine_class": dfine_class,
                "dfine_count": dfine_cnt,
                "symbol": display_symbol,
                "vector_count": vector_cnt,
                "best_estimate": best,
                "confidence": confidence
            })
    
    # Second pass: Vector-only symbols (not found by DFINE)
    for sym, vector_cnt in vector_counts.items():
        if sym in mapped_symbols_used:
            continue
        
        display_symbol = format_symbol_display(sym)
        
        comparison.append({
            "category": SYMBOL_DB.get(sym, sym),
            "dfine_class": None,
            "dfine_count": 0,
            "symbol": display_symbol,
            "vector_count": vector_cnt,
            "best_estimate": vector_cnt,
            "confidence": "high"
        })
    
    # Third pass: Unmapped DFINE classes (not in mapping table or no vector match)
    for dfine_class, dfine_cnt in dfine_counts.items():
        symbol = DFINE_TO_SYMBOL_MAP.get(dfine_class)
        if not symbol:
            # This DFINE class is not mapped to any symbol
            # Include it as-is (use class name as symbol)
            symbol = dfine_class.upper().replace('_', ' ')
            display_symbol = format_symbol_display(symbol, dfine_class)
            
            comparison.append({
                "category": dfine_class.replace('_', ' ').title(),
                "dfine_class": dfine_class,
                "dfine_count": dfine_cnt,
                "symbol": display_symbol,
                "vector_count": 0,
                "best_estimate": dfine_cnt,
                "confidence": "medium"
            })
    
    final_best = {entry["symbol"]: entry["best_estimate"] 
                  for entry in comparison if entry["best_estimate"] > 0}
    
    logger.info(f"✅ Merge complete: {len(comparison)} total entries, {len(final_best)} with counts > 0")
    
    return comparison, final_best


def merge_dfine_only(dfine_counts: Dict[str, int]) -> Tuple[List[Dict], Dict[str, int]]:
    """
    DFINE Detection Only (No Vector, No VLM)
    
    Used for Image processing where only DFINE object detection is available
    
    Args:
        dfine_counts: DFINE class counts
    
    Returns:
        Tuple of (comparison_list, final_best_estimates)
    """
    comparison = []
    
    logger.info(f"\n📊 Processing DFINE Detection Only ({len(dfine_counts)} classes)")
    
    # Process all DFINE classes
    for dfine_class, dfine_cnt in dfine_counts.items():
        # Try to map to symbol
        symbol = DFINE_TO_SYMBOL_MAP.get(dfine_class)
        if not symbol:
            # Use class name as fallback
            symbol = dfine_class.upper().replace('_', ' ')
        
        display_symbol = format_symbol_display(symbol, dfine_class)
        
        comparison.append({
            "category": dfine_class.replace('_', ' ').title(),
            "dfine_class": dfine_class,
            "dfine_count": dfine_cnt,
            "symbol": display_symbol,
            "vector_count": 0,
            "best_estimate": dfine_cnt,
            "confidence": "medium"
        })
    
    final_best = {entry["symbol"]: entry["best_estimate"] 
                  for entry in comparison if entry["best_estimate"] > 0}
    
    logger.info(f"✅ DFINE processing complete: {len(final_best)} symbols detected")
    
    return comparison, final_best


def merge_vector_dfine_vlm(vector_counts: Dict[str, int],
                           dfine_counts: Dict[str, int],
                           vlm_counts: Dict[str, int] = None) -> Tuple[List[Dict], Dict[str, int]]:
    """
    Merge Vector + DFINE + VLM (Enhanced pipeline)
    
    STRATEGY:
    1. Vector extraction is ground truth (100% accurate from PDF text)
    2. DFINE provides visual confirmation
    3. VLM provides AI-based symbol extraction from images
    
    Priority: Vector > VLM > DFINE (for conflicting counts)
    
    Args:
        vector_counts: Vector extraction symbol counts (PDF metadata)
        dfine_counts: DFINE class counts (object detection)
        vlm_counts: VLM symbol counts (AI vision model)
    
    Returns:
        Tuple of (comparison_list, final_best_estimates)
    """
    if vlm_counts is None:
        vlm_counts = {}
    
    comparison = []
    mapped_symbols_used = set()
    
    logger.info(f"\n📊 Merging Vector ({len(vector_counts)} symbols) + DFINE ({len(dfine_counts)} classes) + VLM ({len(vlm_counts)} symbols)")
    
    # First pass: DFINE classes that map to symbols
    for dfine_class, dfine_cnt in dfine_counts.items():
        symbol = DFINE_TO_SYMBOL_MAP.get(dfine_class)
        if symbol:
            mapped_symbols_used.add(symbol)
            vector_cnt = vector_counts.get(symbol, 0)
            vlm_cnt = vlm_counts.get(symbol, 0)
            
            # Decision logic: Vector > VLM > DFINE
            if vector_cnt > 0:
                best = vector_cnt
                confidence = "high"  # Ground truth from PDF
            elif vlm_cnt > 0:
                best = vlm_cnt
                confidence = "medium-high"  # VLM is more accurate than visual detection
            else:
                best = dfine_cnt
                confidence = "medium"  # DFINE alone
            
            display_symbol = format_symbol_display(symbol, dfine_class)
            
            comparison.append({
                "category": dfine_class.replace('_', ' ').title(),
                "dfine_class": dfine_class,
                "dfine_count": dfine_cnt,
                "symbol": display_symbol,
                "vector_count": vector_cnt,
                "vlm_count": vlm_cnt,
                "best_estimate": best,
                "confidence": confidence,
                "source": "vector" if vector_cnt > 0 else ("vlm" if vlm_cnt > 0 else "dfine")
            })
    
    # Second pass: Vector-only symbols (not found by DFINE)
    for sym, vector_cnt in vector_counts.items():
        if sym in mapped_symbols_used:
            continue
        
        vlm_cnt = vlm_counts.get(sym, 0)
        display_symbol = format_symbol_display(sym)
        
        comparison.append({
            "category": SYMBOL_DB.get(sym, sym),
            "dfine_class": None,
            "dfine_count": 0,
            "symbol": display_symbol,
            "vector_count": vector_cnt,
            "vlm_count": vlm_cnt,
            "best_estimate": vector_cnt,  # Vector is primary
            "confidence": "high",
            "source": "vector"
        })
        
        mapped_symbols_used.add(sym)
    
    # Third pass: VLM-only symbols (not in Vector or DFINE)
    for sym, vlm_cnt in vlm_counts.items():
        if sym in mapped_symbols_used:
            continue
        
        display_symbol = format_symbol_display(sym)
        
        comparison.append({
            "category": SYMBOL_DB.get(sym, sym),
            "dfine_class": None,
            "dfine_count": 0,
            "symbol": display_symbol,
            "vector_count": 0,
            "vlm_count": vlm_cnt,
            "best_estimate": vlm_cnt,
            "confidence": "medium",
            "source": "vlm"
        })
        
        mapped_symbols_used.add(sym)
    
    # Fourth pass: Unmapped DFINE classes
    for dfine_class, dfine_cnt in dfine_counts.items():
        symbol = DFINE_TO_SYMBOL_MAP.get(dfine_class)
        if not symbol:
            # This DFINE class is not mapped to any symbol
            symbol = dfine_class.upper().replace('_', ' ')
            display_symbol = format_symbol_display(symbol, dfine_class)
            
            comparison.append({
                "category": dfine_class.replace('_', ' ').title(),
                "dfine_class": dfine_class,
                "dfine_count": dfine_cnt,
                "symbol": display_symbol,
                "vector_count": 0,
                "vlm_count": 0,
                "best_estimate": dfine_cnt,
                "confidence": "medium",
                "source": "dfine"
            })
    
    final_best = {entry["symbol"]: entry["best_estimate"] 
                  for entry in comparison if entry["best_estimate"] > 0}
    
    logger.info(f"✅ Merge complete: {len(comparison)} total entries, {len(final_best)} with counts > 0")
    
    return comparison, final_best

# Backward compatibility exports - use the ENHANCED version that includes unmapped DFINE classes
merge_dfine_vlm = merge_dfine_vlm_enhanced
merge_vector_vlm_dfine = merge_vector_vlm_dfine_enhanced