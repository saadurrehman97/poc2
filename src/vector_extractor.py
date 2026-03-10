"""
Enhanced Vector Text Extraction with Aggressive Filtering
Eliminates useless symbols like CLEAN, FOOD, TRASH, etc.
Returns both filtered symbols AND raw spans for VLM processing
"""
from typing import List, Dict, Tuple
from collections import defaultdict
import re

try:
    import fitz  # PyMuPDF
    PDF_SUPPORT = True
except ImportError:
    try:
        import pymupdf as fitz
        PDF_SUPPORT = True
    except ImportError:
        PDF_SUPPORT = False

from symbol_validator import classify_and_count_symbols
from logger_setup import get_logger
import sys
sys.path.append('..')
from data.symbol_database import SYMBOL_DB, NOISE_WORDS

logger = get_logger(__name__)

# ENHANCEMENT 1: Expanded noise words for aggressive filtering
ADDITIONAL_NOISE_WORDS = {
    # Food / Service Areas
    "CLEAN","FOOD","REF","TRASH","DIRTY","TRAY","PAY","CREAM","SUGAR",
    "REC","REC.","STORAGE","SERVE","DISH","WASH","WAREWASH",
    "COOLER","FREEZER","PANTRY","RECEIVING","DRY",

    # Kitchen Equipment
    "OVEN","RANGE","GRILL","FRYER","STEAMER","BROILER","WARMER",
    "REFRIGERATOR","FRIDGE","ICE","MACHINE","MAKER",
    "DISHWASHER","DISPOSAL","COMPACTOR","HOOD",

    # Furniture
    "COUNTER","SHELF","RACK","CART","STAND","BENCH",

    # Project Phases
    "FUTURE","PROPOSED","DEMO","DEMOLITION","REQUIRED",

    # Access / Layout
    "ENTRY","EXIT","ENTRANCE","ACCESS","HALLWAY",
    "FRONT","BACK","SIDE","REAR","LEFT","RIGHT","CENTER",

    # Misc
    "SEAL","MAX","GAP"
}

# Combine with existing noise words
ALL_NOISE_WORDS = NOISE_WORDS | ADDITIONAL_NOISE_WORDS


def is_plumbing_symbol(text: str) -> bool:
    """
    ENHANCEMENT 2: STRICT plumbing symbol validation - NO LOOSE MATCHES
    Returns True ONLY for actual plumbing symbols, NOT just measurement numbers
    
    CRITICAL FIX: NOT accepting bare numbers/measurements like "6", "4", "30", "8"
    Those are measurements, not symbols. Symbols must have context (CW, HW, etc.)
    """
    text = text.strip().upper()
    
    # Quick reject: noise words - check FIRST
    if text in ALL_NOISE_WORDS:
        return False
    
    # Quick reject: bare numbers (6, 4, 30, 8, 2, 9, 5/8, 12) - THESE ARE NOT SYMBOLS
    # Symbol MUST have a unit/abbreviation context
    if re.match(r'^\d+(/\d+)?["\']?$', text):
        # BLOCKING: Accept ONLY if it's a known symbol like "3/4" in SYMBOL_DB
        # Single measurements without context are NOT symbols
        return False
    
    # Quick accept: known plumbing symbols
    if text in SYMBOL_DB:
        return True
    
    # Pattern 1: Fixture labels (WC-1, LAV-2, AC-1, etc.)
    # These are from SYMBOL_DB structure
    if re.match(r'^[A-Z]{2,4}-\d+[A-Z]?$', text):
        base = text.split('-')[0]
        if base in SYMBOL_DB or base in ['WC', 'LAV', 'UR', 'SK', 'MS', 'EWC', 'HB', 'FD', 'DN', 'EWS', 'FCO', 'GWH', 'RP', 'SS', 'WCO', 'WF', 'WH', 'HR']:
            return True
    
    # Pattern 2: Pipe sizes WITH abbreviations (3/4" CW, 1" HW, 1/2" NG, 1 1/2" SAN, etc.)
    # CRITICAL: MUST have 2+ letter abbreviation (CW, HW, HWR, NG, SAN, GW, etc.)
    # This filters out bare measurements like "6", "4", "30"
    if re.search(r'\d+\s*["\']?\s*([A-Z]{2,})', text):
        # Check if it matches known pipe size patterns
        if re.search(r'(CW|HW|HWR|NG|SAN|GW|V|FP|CD|CA|ST|OST|TW)', text):
            return True
    
    # Pattern 3: Pipe routing/flow symbols (UP, DOWN, RISER, DROP, BRANCH, etc.)
    # routing_symbols = {
    #     'UP', 'DOWN', 'RISER', 'DROP', 'RISE', 'BRANCH', 'CONNECTION', 'POC'
    # }
    # if text in routing_symbols:
    #     return True
    
    # # Pattern 4: Known abbreviations (CLEANOUT, METER, etc.)
    # plumbing_abbrev = {
    #     'CLEANOUT', 'POC', 'ETR', 'METER', 'THERM', 'VTR', 
    #     'CV', 'GV', 'BV', 'PV', 'TV', 'BFP', 'ELB', 'TEE', 'CK', 'GATE'
    # }
    # if text in plumbing_abbrev:
    #     return True
    
    # Reject everything else - be STRICT
    return False


def filter_by_spatial_context(spans: List[Dict]) -> List[Dict]:
    """
    ENHANCEMENT 3: Spatial filtering
    Filters out text that appears in title blocks, notes areas, etc.
    """
    if not spans:
        return spans
    
    # Calculate page bounds
    all_y_coords = [s['bbox'][1] for s in spans if s.get('bbox')]
    if not all_y_coords:
        return spans
    
    page_height = max(all_y_coords)
    
    filtered = []
    for span in spans:
        bbox = span.get('bbox')
        if not bbox:
            continue
        
        x1, y1, x2, y2 = bbox
        
        # FILTER 1: Skip title blocks (usually bottom 15% of page)
        if y1 > page_height * 0.85:
            continue
        
        # FILTER 2: Skip very large text (likely titles, not symbols)
        if span.get('size', 0) > 20:
            continue
        
        # FILTER 3: Skip bold/heavy text (often room labels)
        flags = span.get('flags', 0)
        is_bold = flags & 2**4  # Bold flag
        if is_bold and span.get('size', 0) > 14:
            # Large bold text is probably a room label
            continue
        
        filtered.append(span)
    
    return filtered


def filter_by_text_characteristics(spans: List[Dict]) -> List[Dict]:
    """
    ENHANCEMENT 4: Text characteristic filtering
    Filters based on font properties and text patterns
    """
    filtered = []
    
    for span in spans:
        text = span.get('text', '').strip().upper()
        
        # Skip empty
        if not text:
            continue
        
        # Skip very long text (likely descriptions, not symbols)
        if len(text) > 30:
            continue
        
        # Skip sentences (contain spaces and multiple words)
        words = text.split()
        if len(words) > 4:
            continue
        
        # Skip text that's all lowercase (rare in technical drawings)
        if text.islower():
            continue
        
        # Skip text with special characters (except plumbing symbols)
        if re.search(r'[!@#$%^&*()_+=\[\]{}\\|;<>?~`]', text):
            # Exception: Allow quotes for pipe sizes
            if not re.search(r'\d+["\']', text):
                continue
        
        filtered.append(span)
    
    return filtered


def extract_vector_text_with_positions(pdf_path: str) -> List[Dict]:
    """
    Enhanced text extraction with position/font info
    NOW WITH VECTOR PAGE DETECTION: Skips image-only pages
    """
    if not PDF_SUPPORT:
        logger.error("PDF support not available. PyMuPDF not installed.")
        return []
    
    doc = fitz.open(pdf_path)
    results = []
    vector_pages = []  # Track which pages have meaningful vectors
    
    for page_num, page in enumerate(doc, start=1):
        page_dict = page.get_text("dict")
        page_spans = []
        
        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:  # Only text blocks
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if not text:
                        continue
                    page_spans.append({
                        "page": page_num,
                        "text": text,
                        "bbox": span.get("bbox"),
                        "size": span.get("size", 0),
                        "flags": span.get("flags", 0),
                        "font": span.get("font", "")
                    })
        
        # CRITICAL: Check if page is vector-based
        # Vector pages should have moderate amount of text (not image-only, not pure text document)
        # Image-only pages have 0-5 text spans (mostly empty space)
        # Pure text pages have 100+ spans (documents, not drawings)
        # Vector CAD drawings: 10-80 text elements (symbols, labels)
        if len(page_spans) >= 8:  # At least 8 text elements suggest vector data
            results.extend(page_spans)
            vector_pages.append(page_num)
            logger.debug(f"Page {page_num}: VECTOR-BASED ({len(page_spans)} text elements)")
        else:
            logger.debug(f"Page {page_num}: IMAGE-ONLY or EMPTY ({len(page_spans)} text elements) - SKIPPING")
    
    doc.close()
    
    if vector_pages:
        logger.info(f"   📄 Processing {len(vector_pages)} vector-based page(s): {vector_pages}")
    
    return results


def filter_by_font_size(spans: List[Dict], percentile: int = 60) -> List[Dict]:
    """
    Filter text spans by font size percentile
    Now also filters out very large text
    """
    if not spans:
        return spans
    
    sizes = [s["size"] for s in spans]
    sizes.sort()
    
    # Calculate percentile threshold
    threshold = sizes[int(len(sizes) * percentile / 100)] if sizes else 999
    
    # Also set max threshold (no text larger than 18pt is likely a symbol)
    max_threshold = 18
    
    return [s for s in spans 
            if s["size"] <= threshold and s["size"] <= max_threshold]


def extract_vector_symbols(pdf_path: str, font_percentile: int = 60) -> Tuple[Dict, Dict, Dict, List[Dict]]:
    """
    ENHANCED: Complete vector extraction pipeline with AGGRESSIVE filtering
    
    CRITICAL IMPROVEMENTS:
    1. Skips image-only pages (pages with <8 text elements)
    2. Rejects bare measurements like "6", "4", "30" (NOT symbols)
    3. Requires pipe size abbreviations (CW, HW, NG, SAN, etc.)
    4. Final validation to remove any noise
    
    Returns:
        Tuple of (symbol_counts, unknown_symbols, rejected_text, raw_spans)
    """
    from logger_setup import log_section
    log_section(logger, "📝 VECTOR TEXT EXTRACTION")
    
    # Step 1: Extract all text with positions (SKIPS IMAGE-ONLY PAGES)
    spans = extract_vector_text_with_positions(pdf_path)
    if not spans:
        logger.warning("⚠️ No vector content found (all pages appear to be image-only)")
        return {}, {}, {}, []
    
    logger.debug(f"Extracted {len(spans)} text spans from vector pages")
    
    # Store raw spans for VLM processing
    raw_spans = spans.copy()
    
    # Step 2: Spatial filtering (remove title blocks, margins)
    spans = filter_by_spatial_context(spans)
    logger.debug(f"After spatial filtering: {len(spans)} spans")
    
    # Step 3: Text characteristic filtering
    spans = filter_by_text_characteristics(spans)
    logger.debug(f"After text filtering: {len(spans)} spans")
    
    # Step 4: Font size filtering
    filtered_spans = filter_by_font_size(spans, percentile=font_percentile)
    logger.debug(f"After font filtering: {len(filtered_spans)} spans (percentile: {font_percentile})")
    
    # Step 5: Extract text and apply STRICT plumbing symbol validation
    lines = []
    rejected_bare_numbers = 0
    
    for s in filtered_spans:
        text = s["text"].strip().upper()
        
        # CRITICAL CHECK: Reject bare numbers/measurements
        if re.match(r'^\d+(/\d+)?["\']?$', text):
            rejected_bare_numbers += 1
            logger.debug(f"Rejected bare measurement: '{text}' (not a symbol)")
            continue
        
        # Only include if it passes strict plumbing symbol check
        if is_plumbing_symbol(text):
            lines.append(text)
    
    if rejected_bare_numbers > 0:
        logger.info(f"   ℹ️ Rejected {rejected_bare_numbers} bare measurements (6, 4, 30, etc.) - NOT symbols")
    
    logger.debug(f"After plumbing symbol validation: {len(lines)} valid symbols")
    
    if len(lines) == 0:
        logger.warning("⚠️ No valid plumbing symbols found after filtering")
        logger.info("   Suggestion: Verify PDF contains vector-based drawings with labeled symbols")
    
    # Step 6: Classify and count symbols
    vector_counts, unknown_counts, rejected_counts = classify_and_count_symbols(
        lines, SYMBOL_DB
    )
    
    logger.info(f"   ✓ Found {len(vector_counts)} unique symbols ({sum(vector_counts.values())} instances)")
    
    # ENHANCEMENT 5: Final cleanup - remove any remaining noise
    final_counts = {}
    for symbol, count in vector_counts.items():
        # Double-check against noise words
        if symbol not in ALL_NOISE_WORDS:
            # Also reject bare numbers one final time
            if not re.match(r'^\d+(/\d+)?["\']?$', symbol):
                final_counts[symbol] = count
    
    removed = len(vector_counts) - len(final_counts)
    if removed > 0:
        logger.warning(f"   ⚠️ Removed {removed} invalid entries in final cleanup")
    
    return final_counts, unknown_counts, rejected_counts, raw_spans


def is_pdf_supported() -> bool:
    """Check if PDF support is available"""
    if not PDF_SUPPORT:
        logger.warning("PDF support not available. PyMuPDF not installed.")
    return PDF_SUPPORT