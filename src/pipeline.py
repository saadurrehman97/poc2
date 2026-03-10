import json
import csv
import cv2
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
from PIL import Image

from config import Config
from vector_extractor import extract_vector_symbols, is_pdf_supported
from dfine_detector import DFINEPipeline
from vlm_extractor import run_vlm_extraction, run_vlm_connection_extraction  # NEW: VLM extraction + connections
from merger import merge_vector_dfine, merge_dfine_only, merge_vector_dfine_vlm  # NEW: VLM merger
from logger_setup import get_logger, log_section, log_step
from data.symbol_database import DFINE_TO_SYMBOL_MAP  # NEW: For symbol mapping

logger = get_logger(__name__)

def run_pdf_workflow(pdf_path: str, out_dir: Path, dfine_pipeline: DFINEPipeline) -> Dict:
    """Complete workflow for PDF documents with tile saving
    
    NEW: Vector extraction returns raw_spans that are passed to VLM
    This allows VLM to extract symbols from ALL text, not just filtered ones
    """
    if not is_pdf_supported():
        raise RuntimeError("PDF support not installed")
    
    logger.info("\n📄 Processing PDF...")
    
    # Step 1: Vector text extraction
    vector_counts, unknown_counts, rejected_counts, raw_spans = extract_vector_symbols(pdf_path)
    
    # Step 2: Render PDF for DFINE
    logger.info("\n📄 Rendering PDF for DFINE detection...")
    try:
        import fitz
        PDF_LIB = "PyMuPDF"
    except ImportError:
        try:
            import pymupdf as fitz
            PDF_LIB = "PyMuPDF"
        except ImportError:
            logger.error("PyMuPDF not installed. Cannot render PDF.")
            raise RuntimeError("PDF support not installed")
    
    # Simple PDF to images conversion
    doc = fitz.open(pdf_path)
    dfine_images = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=fitz.Matrix(Config.PDF_DPI_FOR_DFINE / 72, Config.PDF_DPI_FOR_DFINE / 72))
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        dfine_images.append({
            'page': page_num + 1,
            'pil_image': img
        })
    doc.close()
    
    # Step 3: DFINE detection with tile saving
    log_section(logger, "🔍 DFINE OBJECT DETECTION")
    
    from collections import defaultdict
    all_dfine_detections = []
    dfine_counts_by_class = defaultdict(int)
    page_dfine_results = []
    
    # Create tiles directory
    tiles_dir = out_dir / "detected_tiles"
    tiles_dir.mkdir(exist_ok=True)
    
    for page_img in dfine_images:
        page_num = page_img['page']
        pil_img = page_img['pil_image']
        logger.info(f"   Page {page_num}: detecting...")
        
        # Get tiles for this page
        tiles, positions = dfine_pipeline.tile_image(pil_img)
        
        # Detect on each tile and save
        tile_detections = []
        tiles_saved = 0
        for tile_idx, (tile_pil, pos) in enumerate(zip(tiles, positions), 1):
            tile_dets = dfine_pipeline.detect_on_tile(tile_pil, pos)
            tile_detections.extend(tile_dets)
            
            # Save tile with detections if any found
            if tile_dets:
                tile_np = np.array(tile_pil)
                # Adjust detections to tile coordinates
                tile_local_dets = []
                x_start, y_start, _, _ = pos
                for det in tile_dets:
                    local_det = det.copy()
                    local_det['bbox'] = [
                        det['bbox'][0] - x_start,
                        det['bbox'][1] - y_start,
                        det['bbox'][2] - x_start,
                        det['bbox'][3] - y_start
                    ]
                    tile_local_dets.append(local_det)
                
                tile_with_boxes = dfine_pipeline.draw_detections(
                    tile_np, tile_local_dets,
                    draw_labels=True, line_thickness=2, font_scale=0.5
                )
                tile_bgr = cv2.cvtColor(tile_with_boxes, cv2.COLOR_RGB2BGR)
                tile_path = tiles_dir / f"page_{page_num:02d}_tile_{tile_idx:03d}.jpg"
                cv2.imwrite(str(tile_path), tile_bgr)
                tiles_saved += 1
        
        # Apply NMS to all tile detections
        detections = dfine_pipeline.apply_nms(tile_detections)
        
        all_dfine_detections.extend(detections)
        for d in detections:
            dfine_counts_by_class[d['class_name']] += 1
        
        page_dfine_results.append({
            'page': page_num,
            'detections': detections,
            'total_tiles': len(tiles),
            'tiles_with_detections': tiles_saved
        })
        logger.info(f"      Found {len(detections)} objects after NMS")
        logger.info(f"      Saved {tiles_saved} tiles with detections to: {tiles_dir.name}/")
        
        # Save full page image with all detections
        page_np = np.array(pil_img)
        page_with_boxes = dfine_pipeline.draw_detections(page_np, detections,
                                                        draw_labels=True,
                                                        line_thickness=2,
                                                        font_scale=0.5)
        page_bgr = cv2.cvtColor(page_with_boxes, cv2.COLOR_RGB2BGR)
        page_path = out_dir / f"full_image_detected_page_{page_num:02d}.jpg"
        cv2.imwrite(str(page_path), page_bgr)
        logger.info(f"      Saved full image: {page_path.name}")
    
    logger.info(f"\n✅ DFINE total: {len(all_dfine_detections)} detections, "
          f"{len(dfine_counts_by_class)} classes")
    
    # Step 4: SKIP VLM EXTRACTION - Use Vector + DFINE directly (more accurate)
    vlm_counts = {}
    vlm_connections = []
    if Config.VLM_ENABLED:
        log_section(logger, "🧠 VLM SYMBOL EXTRACTION - SKIPPED")
        logger.info("   ℹ️ Using Vector + DFINE symbols directly (more accurate than VLM counting)")
        logger.info(f"   ✓ Vector: {len(vector_counts)} symbols (100% accurate text extraction)")
        logger.info(f"   ✓ DFINE: {len(dfine_counts_by_class)} classes (visual object detection)")
        
        # Copy Vector counts (100% accurate for text-based symbols)
        vlm_counts = vector_counts.copy()
        logger.info(f"   ✓ Using {len(vlm_counts)} symbols from Vector extraction")
        
        # Step 4.5: Extract symbol-to-pipe connections using ONLY FIXTURE symbols from SYMBOL_DB
        log_section(logger, "🔗 VLM SYMBOL-PIPE CONNECTION EXTRACTION (Step 4)")
        
        # Import SYMBOL_DB to filter fixture symbols only
        from data.symbol_database import SYMBOL_DB
        
        # Filter Vector symbols to ONLY fixtures from SYMBOL_DB (exclude pipe sizes)
        fixture_symbols_from_vector = [sym for sym in vector_counts.keys() if sym in SYMBOL_DB]
        
        # Map DFINE classes to symbols, then filter to ONLY fixtures from SYMBOL_DB
        dfine_mapped_symbols = [DFINE_TO_SYMBOL_MAP.get(cls, cls) for cls in dfine_counts_by_class.keys()]
        fixture_symbols_from_dfine = [sym for sym in dfine_mapped_symbols if sym in SYMBOL_DB]
        
        # Combine fixture symbols only (no pipe sizes, no DFINE classes)
        all_fixture_symbols = list(set(fixture_symbols_from_vector + fixture_symbols_from_dfine))
        
        logger.info(f"   📋 Analyzing connections for {len(all_fixture_symbols)} FIXTURE symbols (from SYMBOL_DB)")
        logger.info(f"      - From Vector: {len(fixture_symbols_from_vector)} fixtures (filtered from {len(vector_counts)} total)")
        logger.info(f"      - From DFINE: {len(fixture_symbols_from_dfine)} fixtures (filtered from {len(dfine_counts_by_class)} total)")
        logger.info(f"      ℹ️  Excluded: pipe sizes (1/2\" NG, etc.) and DFINE classes (Riser Up Elbow, etc.)")
        
        vlm_connections = run_vlm_connection_extraction(
            pdf_path=pdf_path, 
            enabled=True,
            detected_symbols=all_fixture_symbols  # Only pass fixture symbols
        )
        if vlm_connections:
            logger.info(f"   ✅ VLM found {len(vlm_connections)} symbol-pipe connections")
        else:
            logger.warning("   ⚠️ No symbol-pipe connections found")
            logger.info("      Possible reasons:")
            logger.info("      - Drawing quality may be low")
            logger.info("      - Pipe labels may not be clearly visible")
            logger.info("      - Try increasing VLM_DPI_LIST or VLM_TIMEOUT in config.py")
    
    # Step 5: Merge Vector + DFINE + VLM
    logger.info("\n📊 Merging Vector + DFINE + VLM Results")
    comparison, final_best = merge_vector_dfine_vlm(
        vector_counts, dfine_counts_by_class, vlm_counts
    )
    
    # Build final JSON
    final_json = {
        "document": str(pdf_path),
        "file_type": "PDF",
        "timestamp": datetime.now().strftime('%Y%m%d_%H%M%S'),
        "output_directory": str(out_dir),
        "pages": page_dfine_results,
        "aggregated": {
            "dfine": {
                "by_class": dict(dfine_counts_by_class),
                "total_detections": len(all_dfine_detections)
            },
            "vector": {
                "by_symbol": vector_counts,
                "unknown_symbols": unknown_counts,
                "rejected_text": dict(sorted(rejected_counts.items(), 
                                            key=lambda x: x[1], reverse=True)[:20])
            },
            "vlm": {  # NEW: VLM results (Step 3 skipped, using Vector counts)
                "by_symbol": vlm_counts,
                "total_symbols": len(vlm_counts),
                "total_instances": sum(vlm_counts.values()) if vlm_counts else 0,
                "connections": vlm_connections,  # NEW: Step 4 - Symbol-pipe connections
                "note": "VLM Step 3 skipped - using Vector counts directly (more accurate)"
            }
        },
        "comparison": comparison,
        "final_best_estimates": final_best,
        "metadata": {
            "pages": len(dfine_images),
            "dfine_onnx_path": Config.DFINE_ONNX_PATH,
            "vector_font_percentile": Config.VECTOR_FONT_PERCENTILE,
            "dfine_confidence_threshold": Config.DFINE_CONFIDENCE_THRESHOLD,
            "vlm_enabled": Config.VLM_ENABLED,  # NEW
            "vlm_model": Config.VLM_MODEL,  # NEW
            "vlm_dpi_list": Config.VLM_DPI_LIST,  # NEW
            "device": str(Config.DEVICE),
            "pdf_support": is_pdf_supported(),
            "raw_spans_used": len(raw_spans)
        }
    }
    
    return final_json

def run_image_workflow(image_path: str, out_dir: Path, dfine_pipeline: DFINEPipeline) -> Dict:
    """Complete workflow for single image with tile saving"""
    logger.info("\n🖼️ Processing large image...")
    
    # Create tiles directory
    tiles_dir = out_dir / "detected_tiles"
    tiles_dir.mkdir(exist_ok=True)
    
    # Step 1: DFINE detection with tile saving
    log_section(logger, "🔍 DFINE OBJECT DETECTION")
    pil_image = Image.open(image_path).convert('RGB')
    full_np = np.array(pil_image)
    
    # Get tiles
    tiles, positions = dfine_pipeline.tile_image(pil_image)
    
    # Detect on each tile and save
    all_detections = []
    tiles_saved = 0
    for tile_idx, (tile_pil, pos) in enumerate(zip(tiles, positions), 1):
        logger.info(f"      Processing tile {tile_idx}/{len(tiles)}...")
        tile_dets = dfine_pipeline.detect_on_tile(tile_pil, pos)
        all_detections.extend(tile_dets)
        
        # Save tile with detections if any found
        if tile_dets:
            tile_np = np.array(tile_pil)
            # Adjust detections to tile coordinates
            tile_local_dets = []
            x_start, y_start, _, _ = pos
            for det in tile_dets:
                local_det = det.copy()
                local_det['bbox'] = [
                    det['bbox'][0] - x_start,
                    det['bbox'][1] - y_start,
                    det['bbox'][2] - x_start,
                    det['bbox'][3] - y_start
                ]
                tile_local_dets.append(local_det)
            
            tile_with_boxes = dfine_pipeline.draw_detections(
                tile_np, tile_local_dets,
                draw_labels=True, line_thickness=2, font_scale=0.5
            )
            tile_bgr = cv2.cvtColor(tile_with_boxes, cv2.COLOR_RGB2BGR)
            tile_path = tiles_dir / f"tile_{tile_idx:03d}.jpg"
            cv2.imwrite(str(tile_path), tile_bgr)
            tiles_saved += 1
    
    # Apply NMS
    filtered_detections = dfine_pipeline.apply_nms(all_detections)
    
    logger.info(f"   Found {len(filtered_detections)} objects after NMS")
    logger.info(f"   Saved {tiles_saved} tiles with detections to: {tiles_dir.name}/")
    
    # Count per class
    from collections import defaultdict
    dfine_counts = defaultdict(int)
    for d in filtered_detections:
        dfine_counts[d['class_name']] += 1
    
    # Draw and save full detected image
    full_detected = dfine_pipeline.draw_detections(full_np, filtered_detections,
                                                   draw_labels=True,
                                                   line_thickness=2,
                                                   font_scale=0.5)
    full_detected_bgr = cv2.cvtColor(full_detected, cv2.COLOR_RGB2BGR)
    full_detected_path = out_dir / "full_image_detected.jpg"
    cv2.imwrite(str(full_detected_path), full_detected_bgr)
    logger.info(f"   Saved full detected image: {full_detected_path.name}")
    
    # Step 2: Merge DFINE results
    logger.info("\n📊 Merging DFINE detection")
    comparison, final_best = merge_dfine_only(dfine_counts)
    
    # Step 3: SKIP VLM EXTRACTION - Use DFINE directly (more accurate)
    vlm_counts = {}
    vlm_connections = []
    if Config.VLM_ENABLED:
        log_section(logger, "🧠 VLM SYMBOL EXTRACTION - SKIPPED")
        logger.info("   ℹ️ Using DFINE symbols directly (more accurate than VLM counting)")
        logger.info(f"   ✓ DFINE: {len(dfine_counts)} classes (visual object detection)")
        
        # No Vector extraction for images, so vlm_counts stays empty
        # This is correct - we rely on DFINE for image-based detection
        
        # Step 3.5: Extract symbol-to-pipe connections using ONLY FIXTURE symbols from SYMBOL_DB
        log_section(logger, "🔗 VLM SYMBOL-PIPE CONNECTION EXTRACTION (Step 4)")
        
        # Import SYMBOL_DB to filter fixture symbols only
        from data.symbol_database import SYMBOL_DB
        
        # Map DFINE classes to symbols, then filter to ONLY fixtures from SYMBOL_DB
        dfine_mapped_symbols = [DFINE_TO_SYMBOL_MAP.get(cls, cls) for cls in dfine_counts.keys()]
        all_fixture_symbols = [sym for sym in dfine_mapped_symbols if sym in SYMBOL_DB]
        
        logger.info(f"   📋 Analyzing connections for {len(all_fixture_symbols)} FIXTURE symbols (from SYMBOL_DB)")
        logger.info(f"      - From DFINE: {len(all_fixture_symbols)} fixtures (filtered from {len(dfine_counts)} total)")
        logger.info(f"      ℹ️  Excluded: DFINE classes not in SYMBOL_DB (Riser Up Elbow, ball_valve, etc.)")
        
        vlm_connections = run_vlm_connection_extraction(
            image_path=image_path, 
            enabled=True,
            detected_symbols=all_fixture_symbols  # Only pass fixture symbols
        )
        if vlm_connections:
            logger.info(f"   ✅ VLM found {len(vlm_connections)} symbol-pipe connections")
            # Re-merge with VLM results if available
            from merger import merge_vector_dfine_vlm
            comparison, final_best = merge_vector_dfine_vlm({}, dfine_counts, vlm_counts)
        else:
            logger.warning("   ⚠️ No symbol-pipe connections found")
            logger.info("      Possible reasons:")
            logger.info("      - Drawing quality may be low")
            logger.info("      - Pipe labels may not be clearly visible")
            logger.info("      - Try increasing VLM_DPI_LIST or VLM_TIMEOUT in config.py")
    
    # Build final JSON
    final_json = {
        "document": str(image_path),
        "file_type": "Image",
        "timestamp": datetime.now().strftime('%Y%m%d_%H%M%S'),
        "output_directory": str(out_dir),
        "aggregated": {
            "dfine": {
                "by_class": dict(dfine_counts),
                "total_detections": len(filtered_detections)
            },
            "vector": {
                "by_symbol": {},
                "unknown_symbols": {},
                "rejected_text": {}
            },
            "vlm": {  # NEW: VLM results (Step 3 skipped for images)
                "by_symbol": vlm_counts,
                "total_symbols": len(vlm_counts),
                "total_instances": sum(vlm_counts.values()) if vlm_counts else 0,
                "connections": vlm_connections,  # NEW: Step 4 - Symbol-pipe connections
                "note": "VLM Step 3 skipped - using DFINE detections directly (more accurate)"
            }
        },
        "comparison": comparison,
        "final_best_estimates": final_best,
        "metadata": {
            "pages": 1,
            "total_tiles": len(tiles),
            "tiles_with_detections": tiles_saved,
            "dfine_onnx_path": Config.DFINE_ONNX_PATH,
            "dfine_confidence_threshold": Config.DFINE_CONFIDENCE_THRESHOLD,
            "vlm_enabled": Config.VLM_ENABLED,  # NEW
            "vlm_model": Config.VLM_MODEL,  # NEW
            "device": str(Config.DEVICE),
            "pdf_support": is_pdf_supported()
        }
    }
    
    return final_json

def save_results_to_files(results: Dict, out_dir: Path):
    """Save results to JSON and CSV files"""
    # Save JSON
    json_path = out_dir / "results.json"
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2)
    logger.info(f"💾 Saved JSON: {json_path.name}")
    
    # Save CSV with symbol counts
    csv_path = out_dir / "symbol_counts.csv"
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Symbol', 'Count', 'Source'])
        
        # Write final best estimates
        for symbol, count in sorted(results['final_best_estimates'].items(), 
                                    key=lambda x: x[1], reverse=True):
            writer.writerow([symbol, count, 'Best Estimate'])
    
    logger.info(f"💾 Saved CSV: {csv_path.name}")

def run_full_pipeline(input_path: str, output_dir: Optional[str] = None,
                     dfine_conf: Optional[float] = None,
                     onnx_path: Optional[str] = None) -> Dict:
    """Main entry point - automatically detects PDF vs image"""
    # Update config if parameters provided
    if output_dir:
        Config.OUTPUT_BASE_DIR = output_dir
    if dfine_conf:
        Config.DFINE_CONFIDENCE_THRESHOLD = dfine_conf
    if onnx_path:
        Config.DFINE_ONNX_PATH = onnx_path
    
    log_section(logger, "🚀 NEPTUNE PLUMBING PIPELINE: Vector + VLM + DFINE (ONNX)")
    
    input_path = str(input_path)
    file_ext = Path(input_path).suffix.lower()
    is_pdf = file_ext == '.pdf' and is_pdf_supported()
    
    logger.info(f"📁 Input: {Path(input_path).name}")
    logger.info(f"📄 Type: {'PDF' if is_pdf else 'Image'}")
    
    # Prepare output directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    stem = Path(input_path).stem
    out_dir = Path(Config.OUTPUT_BASE_DIR) / f"{stem}_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"📁 Output directory: {out_dir}")
    
    # Load DFINE model (ONNX)
    dfine_pipeline = DFINEPipeline()
    success = dfine_pipeline.load_model(onnx_path or Config.DFINE_ONNX_PATH)
    if not success:
        logger.error("Failed to load DFINE ONNX model. Exiting.")
        return {}
    
    # Dispatch to appropriate workflow
    if is_pdf:
        final = run_pdf_workflow(input_path, out_dir, dfine_pipeline)
    else:
        final = run_image_workflow(input_path, out_dir, dfine_pipeline)
    
    # Save results to JSON and CSV
    save_results_to_files(final, out_dir)
    
    # Print summary
    log_section(logger, "📋 SUMMARY")
    logger.info(f"Document: {Path(input_path).name}")
    logger.info(f"Pages:    {final['metadata'].get('pages', 1)}")
    logger.info(f"DFINE:    {len(final['aggregated']['dfine']['by_class'])} classes, "
          f"{final['aggregated']['dfine']['total_detections']} objects")
    if is_pdf:
        vc = final['aggregated']['vector']['by_symbol']
        logger.info(f"Vector:   {len(vc)} symbols, {sum(vc.values())} instances")
    logger.info(f"Comparison entries: {len(final['comparison'])}")
    logger.info("Best estimates (top 10):")
    top = sorted(final['final_best_estimates'].items(), key=lambda x: x[1], reverse=True)[:10]
    for sym, cnt in top:
        logger.info(f"   {sym}: {cnt}")
    logger.info(f"\n📂 Output files:")
    logger.info(f"   - results.json")
    logger.info(f"   - symbol_counts.csv")
    logger.info(f"   - full_image_detected*.jpg")
    logger.info(f"   - detected_tiles/ (folder with tile images)")
    logger.info("\n✅ Pipeline finished.")
    
    return final

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Neptune Plumbing Symbol Extraction Pipeline")
    parser.add_argument("input_path", help="Path to PDF or image file")
    parser.add_argument("--output-dir", default=Config.OUTPUT_BASE_DIR, 
                       help="Output directory")
    parser.add_argument("--dfine-conf", type=float, default=Config.DFINE_CONFIDENCE_THRESHOLD,
                       help="DFINE confidence threshold")
    parser.add_argument("--onnx-path", default=Config.DFINE_ONNX_PATH,
                       help="Path to DFINE ONNX model")
    
    args = parser.parse_args()
    
    run_full_pipeline(args.input_path, args.output_dir, args.dfine_conf, args.onnx_path)
