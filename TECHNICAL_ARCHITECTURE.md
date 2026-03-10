# Technical Architecture & Implementation Details

## System Overview

### 3-Layer Symbol Extraction Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     INPUT: PDF / IMAGE                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
        ┌─────────────────────────────────────────┐
        │      LAYER 1: VECTOR EXTRACTION         │
        │  Extract text metadata from PDF         │
        │  Accuracy: 100% for text                │
        │  Coverage: Only PDF text symbols        │
        └─────────────────────────────────────────┘
                              ↓
        ┌─────────────────────────────────────────┐
        │    LAYER 2: DFINE OBJECT DETECTION      │
        │  Visual detection of objects            │
        │  Accuracy: ~80%                         │
        │  Coverage: All visual symbols           │
        └─────────────────────────────────────────┘
                              ↓
        ┌─────────────────────────────────────────┐
        │    LAYER 3: VLM MODEL (NEWLY ACTIVE)    │
        │  AI Vision Language Model               │
        │  Model: qwen3-vl:30b-a3b-instruct      │
        │  DPIs: 400, 500, 600                   │
        │  Accuracy: ~85%+                       │
        │  Coverage: All visible symbols         │
        └─────────────────────────────────────────┘
                              ↓
        ┌─────────────────────────────────────────┐
        │      INTELLIGENT RESULT MERGING         │
        │  Priority: Vector > VLM > DFINE        │
        │  Confidence Scoring                    │
        │  Noise Filtering                       │
        └─────────────────────────────────────────┘
                              ↓
        ┌─────────────────────────────────────────┐
        │   OUTPUT: FINAL SYMBOL COUNTS           │
        │   With Confidence Scores &              │
        │   Source Attribution                   │
        └─────────────────────────────────────────┘
```

---

## Detailed Processing Flows

### Flow 1: PDF Processing (Complete 3-Layer)

```
PDF File Input
    ↓
├─→ Vector Extraction (Async)
│   ├─ Open PDF with PyMuPDF
│   ├─ Extract all text spans
│   ├─ Filter by font size (percentile)
│   ├─ Apply spatial filtering
│   ├─ Validate plumbing symbols
│   └─ Return: {symbol: count, ...}
│
├─→ DFINE Detection (Async)
│   ├─ Render PDF at PDF_DPI (300)
│   ├─ Split into tiles (1024x1024)
│   ├─ Detect on each tile with ONNX
│   ├─ Apply NMS (deduplicate)
│   ├─ Map classes to symbols
│   └─ Return: {class: count, ...}
│
└─→ VLM Extraction (NEW - Multi-DPI)
    ├─ For each DPI in [400, 500, 600]:
    │   ├─ Render PDF page at DPI
    │   ├─ Downscale if >4000px
    │   ├─ Build extraction prompt
    │   ├─ Send to ollama qwen3-vl
    │   ├─ Parse JSON response
    │   ├─ Filter noise words
    │   └─ Store results
    │
    ├─ Consensus Voting:
    │   ├─ Count DPI appearances per symbol
    │   ├─ Filter: keep symbols in 2+ DPIs
    │   ├─ Use max count across DPIs
    │   └─ Return: {symbol: count, ...}
    │
    └─ If VLM fails at any DPI:
        └─ Uses results from successful DPIs

                ↓↓↓ ALL COMPLETE ↓↓↓

    Merge Results:
    ├─ Vector symbols → confidence: HIGH
    ├─ VLM symbols not in Vector → confidence: MEDIUM-HIGH
    ├─ DFINE symbols → confidence: MEDIUM
    └─ Final output with source attribution

    Output:
    {
      "vector": {...},
      "dfine": {...},
      "vlm": {...},
      "final_best_estimates": {...},
      "metadata": {...}
    }
```

### Flow 2: Image Processing (2-Layer)

```
Image File Input
    ↓
├─→ DFINE Detection
│   ├─ Tile large image (1024x1024)
│   ├─ Detect on each tile
│   ├─ Apply NMS
│   └─ Return: {class: count, ...}
│
└─→ VLM Extraction (Multi-DPI on single image)
    ├─ For each DPI in [400, 500, 600]:
    │   ├─ Downscale if >4000px
    │   ├─ Extract symbols
    │   └─ Store results
    │
    ├─ Consensus Voting (2+ DPI threshold)
    └─ Return: {symbol: count, ...}

    ↓
    Merge DFINE + VLM results
    ↓
    Output final estimates
```

---

## VLM Multi-DPI Processing Detail

### Why Multiple DPIs?

```
Resolution Comparison:

400 DPI (Lower Resolution)
────────────────────────────────────────────
△ Faster processing
△ Good for large text/symbols
△ Tolerance for slight image degradation
✗ May miss very small text (1/2" pipe size)
✗ Less detail in crowded areas

500 DPI (Medium Resolution)  ← SWEET SPOT
────────────────────────────────────────────
△ Balanced speed/quality
△ Catches most symbols clearly
△ Good consensus baseline

600 DPI (Higher Resolution)
────────────────────────────────────────────
△ Maximum detail
△ Captures small text clearly
✗ Slower processing
✗ More resources needed

CONSENSUS STRATEGY:
Symbol appears in 400DPI? ✓
Symbol appears in 500DPI? ✓
Symbol appears in 600DPI? ✓
→ HIGH CONFIDENCE (appears in all 3)

Symbol appears in 400DPI? ✓
Symbol appears in 500DPI? ✓
Symbol appears in 600DPI? ✗
→ MEDIUM CONFIDENCE (2/3 DPIs)

Symbol appears in 400DPI? ✓
Symbol appears in 500DPI? ✗
Symbol appears in 600DPI? ✗
→ FILTERED OUT (only 1/3 DPIs)
```

### Example: Extracting "3/4\" CW" Across DPIs

```
PDF Page at 400DPI:
┌─────────────────────────────┐
│ Drawing with "3/4" CW"     │
│ detected 5 times            │
└─────────────────────────────┘
Result: {"3/4\" CW": 5}

PDF Page at 500DPI:
┌─────────────────────────────┐
│ Drawing with "3/4" CW"     │ ← Clearer text
│ detected 5 times            │
└─────────────────────────────┘
Result: {"3/4\" CW": 5}

PDF Page at 600DPI:
┌─────────────────────────────┐
│ Drawing with "3/4" CW"     │ ← Sharpest
│ detected 4 times (1 faint)  │
└─────────────────────────────┘
Result: {"3/4\" CW": 4}

Consensus Voting:
─────────────────
Symbol: "3/4\" CW"
Appears in: 400DPI (count: 5)
           500DPI (count: 5)
           600DPI (count: 4)
─────────────────
DPI consensus: 3/3 ✓
Count to use: max(5,5,4) = 5
Confidence: HIGH (unanimous)
Decision: KEEP "3/4\" CW": 5
```

---

## Noise Word Filtering Logic

### Source: data/symbol_database.py

```python
NOISE_WORDS = {
    # Single letters (rarely valid symbols)
    'A', 'B', 'C', 'D', 'E', 'F', ...

    # Direction/area text (not plumbing)
    'NORTH', 'SOUTH', 'KITCHEN', 'ROOM',

    # Document text (not symbols)
    'PLAN', 'SHEET', 'PAGE', 'DRAWING',

    # Generic words
    'THE', 'AND', 'OR', 'IS', 'ARE',

    # More...
}
```

### Filtering Flow:

```
VLM Extraction Output:
{
    "3/4\" CW": 5,      ← Valid pipe size
    "WC-1": 3,          ← Valid fixture
    "CLEANOUT": 2,      ← Valid equipment
    "PLAN": 1,          ← NOISE ✗
    "A": 1,             ← NOISE ✗
    "NORTH": 1,         ← NOISE ✗
}

Noise Filter Pass:
{
    "3/4\" CW": 5,      ← Kept ✓
    "WC-1": 3,          ← Kept ✓
    "CLEANOUT": 2,      ← Kept ✓
}
```

---

## Image Downscaling Strategy

### Problem with Large Images:

```
Original PDF Page: 12000 × 9000 pixels
VLM Max: 4000 × 4000 pixels

What NOT to do (Tiling):
────────────────────────
┌───────────────┬───────────────┐
│  Tile 1       │  Tile 2       │
│ (Image chunks)│ (Image chunks)│
│  Process...   │  Process...   │
│  ⚠️ PROBLEM:  │  ⚠️ PROBLEM:  │
│  Symbols can  │  Symbols can  │
│  be split     │  be split     │
│  across tiles │  across tiles │
└───────────────┴───────────────┘

What TO do (Intelligent Downscaling):
──────────────────────────────────────
Original: 12000 × 9000 pixels
Max allowed: 4000 × 4000 pixels
Aspect ratio: 12000/9000 = 1.33

Calculate scale:
  width_scale = 4000 / 12000 = 0.333
  height_scale = 4000 / 9000 = 0.444
  min_scale = 0.333 (use this)

New size: 12000 × 0.333 = 4000
          9000 × 0.333 = 3000

Result: 4000 × 3000 pixels ✓
Used LANCZOS resampling for quality
→ All symbols visible in single pass
→ No splitting/merging needed
→ Faster processing
```

### Code Implementation:

```python
def _downscale_image_if_needed(image, max_dim=4000):
    """
    Aspect-ratio-preserving downscaling
    """
    width, height = image.size

    if width <= max_dim and height <= max_dim:
        return image  # No scaling needed

    # Scale factor (use minimum to fit both dimensions)
    scale = min(max_dim / width, max_dim / height)

    new_width = int(width * scale)
    new_height = int(height * scale)

    # High-quality resampling
    return image.resize(
        (new_width, new_height),
        Image.Resampling.LANCZOS
    )
```

---

## Error Handling & Resilience

### VLM Extraction Robustness:

```
User calls: run_vlm_extraction(pdf_path)
    ↓
Try rendering at 400DPI
├─ Success → Extract symbols
├─ Timeout → Log warning, continue to 500DPI
├─ Error → Log error, continue to 500DPI
└─ Process killed → Use remaining DPIs

Try rendering at 500DPI
├─ Success → Extract symbols
├─ Timeout → Log warning, continue to 600DPI
├─ Error → Log error, continue to 600DPI
└─ Process killed → Use 400DPI + 600DPI results

Try rendering at 600DPI
├─ Success → Extract symbols
├─ Timeout → Log warning, use 400+500
├─ Error → Log error, use 400+500
└─ Process killed → Use 400+500

Consensus voting on available results
├─ If 3/3 DPIs: Voting strength = HIGH
├─ If 2/3 DPIs: Voting strength = MEDIUM
├─ If 1/3 DPIs: Voting strength = LOW
└─ If 0/3 DPIs: Skip VLM, use Vector+DFINE

Return best available result
└─ Never crashes, always produces output
```

### Timeout Protection:

```python
# In config.py
VLM_TIMEOUT = 600  # seconds

# In vlm_extractor.py
try:
    result = subprocess.run(
        ["ollama", "run", model, prompt],
        timeout=self.timeout,
        ...
    )
except subprocess.TimeoutExpired:
    logger.warning(f"VLM timeout at {dpi}DPI")
    # Returns empty dict for this DPI
    # Continues with next DPI
    return {}
```

---

## Performance Characteristics

### Time Complexity (per PDF):

```
Vector Extraction:
  Time = O(n) where n = total text spans
  Typical: ~1-2 seconds

DFINE Detection:
  Time = O(pages × tiles)
  Typical: ~8-12 seconds

VLM Extraction (NEW):
  Time = O(pages × dpis × model_inference_time)
  Per DPI: ~15-20 seconds per page
  3 DPIs: ~45-60 seconds per page
  For 5-page PDF: ~3-5 minutes with GPU
  For 5-page PDF: ~15-30 minutes with CPU

Merging:
  Time = O(n) where n = total symbols
  Typical: <1 second
```

### Space Complexity:

```
Vector: O(n) = all text spans in memory
DFINE: O(p) = detections per page
VLM: O(d) = results per DPI (typically <1000 symbols)
Total: O(p + d) = all results combined
```

---

## Configuration Expansion Points

### For Future Enhancement:

```python
# Potential additions:

# 1. Custom DPI levels
VLM_DPI_LIST = [300, 400, 500, 600, 700, 800]

# 2. Per-DPI confidence weighting
VLM_DPI_WEIGHTS = {
    400: 1.0,
    500: 1.2,  # Higher weight for sweet spot
    600: 1.1
}

# 3. Adaptive timeouts based on image size
def adaptive_timeout(image_size):
    if image_size > 10000:
        return 900  # 15 min for huge images
    elif image_size > 5000:
        return 600  # 10 min for large
    else:
        return 300  # 5 min for normal

# 4. Symbol-specific extraction rules
SYMBOL_EXTRACTION_RULES = {
    "pipe_sizes": {"pattern": r"\d+['\"]", "confidence": 0.95},
    "fixture_labels": {"pattern": r"[A-Z]{2,4}-\d+", "confidence": 0.98}
}

# 5. Dynamic DPI selection based on image quality
def select_dpis_for_image(image):
    sharpness = measure_image_sharpness(image)
    if sharpness > 0.8:
        return [600]  # High quality, use best only
    elif sharpness > 0.5:
        return [400, 600]  # Normal, use 2 DPIs
    else:
        return [400, 500, 600]  # Low quality, use all
```

---

## Integration Points with Existing Code

### How VLM fits with other components:

```
config.py
├─ Provides model name, DPI list, timeouts
└─ Controls VLM_ENABLED flag

vector_extractor.py
├─ Returns raw_spans (not used by VLM currently)
├─ Filters symbols aggressively
└─ VLM compensates for over-filtering

dfine_detector.py
├─ Operates independently
├─ Returns detected classes
└─ Merges with VLM in merger.py

vlm_extractor.py (NEW)
├─ Standalone symbol extraction
├─ Multi-DPI rendering
├─ Consensus voting
└─ Noise filtering

merger.py (ENHANCED)
├─ New function: merge_vector_dfine_vlm
├─ Priority logic: Vector > VLM > DFINE
└─ Confidence attribution

pipeline.py (UPDATED)
├─ Calls VLM after DFINE
├─ Passes results to merger
└─ Includes VLM metadata in output
```

---

## Testing Strategy

### Unit Tests for VLM:

```python
def test_multi_dpi_extraction():
    """Test VLM at each DPI"""
    extractor = VLMSymbolExtractor()

    for dpi in [400, 500, 600]:
        symbols = extractor.extract_from_image(test_image, dpi)
        assert len(symbols) > 0, f"Failed at {dpi}DPI"

def test_consensus_voting():
    """Test combining results from multiple DPIs"""
    results = {
        400: {"3/4\" CW": 5, "WC-1": 3},
        500: {"3/4\" CW": 5, "WC-1": 3, "METER": 1},
        600: {"3/4\" CW": 4}
    }
    combined = extractor._combine_dpi_results(results, min_consensus=2)
    assert "3/4\" CW" in combined  # In all 3
    assert "WC-1" in combined  # In 2/3
    assert "METER" not in combined  # Only 1/3

def test_noise_filtering():
    """Test noise word removal"""
    symbols = {"3/4\" CW": 5, "PLAN": 1, "PAGE": 1}
    filtered = extractor._filter_noise(symbols)
    assert "3/4\" CW" in filtered
    assert "PLAN" not in filtered
    assert "PAGE" not in filtered
```

---

This architecture provides:

- ✅ Redundancy (3 extraction methods)
- ✅ Confidence scoring (knows which method extracted each symbol)
- ✅ Resilience (graceful fallbacks on timeout)
- ✅ Scalability (handles 12000x9000 images)
- ✅ Maintainability (clean separation of concerns)
- ✅ Extensibility (easy to add new features)
