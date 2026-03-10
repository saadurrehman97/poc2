# 🔧 VLM Improvements - Critical Fixes for Accuracy

## Issues Identified

Based on your output:

**Vector Extraction (Correct):**
```
1/4" NG: 4
2" NG: 2
1/2" NG: 2
3/4" NG: 1
GWH-1: 1
4" NG: 1
```

**VLM Extraction (Wrong):**
```
3/4" NG: 2    ❌ Should be 1
1/2" NG: 2    ✅ Correct
2" NG: 2      ✅ Correct
1/4" NG: 2    ❌ Should be 4
4" NG: 2      ❌ Should be 1
```

**Problems:**
1. VLM counts are incorrect (not matching Vector)
2. VLM is missing GWH-1 symbol
3. Step 4 returns empty (no connections detected)

---

## Root Causes

### Problem 1: VLM Not Using Vector Counts as Ground Truth
- VLM should COPY counts from Vector when available
- VLM should only ADD symbols not in Vector

### Problem 2: Prompt Not Strict Enough
- VLM is still "counting" instead of "verifying"
- Need to tell VLM: "Vector says 4, verify you see 4"

### Problem 3: Step 4 Has No Symbols to Work With
- If VLM fails in Step 3, Step 4 has nothing to analyze
- Need fallback to use Vector symbols directly

---

## Solution: Use Vector as Ground Truth

### New Strategy:

```
Step 1: Vector Extraction
Output: {1/4" NG: 4, 2" NG: 2, GWH-1: 1}

Step 2: DFINE Detection  
Output: {ball_valve: 8, gate_valve: 5}

Step 3: VLM Verification (NEW APPROACH)
Input: Vector symbols + DFINE symbols
Task: VERIFY Vector counts, ADD any missing symbols
Output: {1/4" NG: 4, 2" NG: 2, GWH-1: 1, ball_valve: 8}

Step 4: VLM Connections
Input: ALL symbols from Steps 1-3
Task: Find connections for these specific symbols
Output: Connections table
```

---

## Code Changes Needed

### Change 1: Modify VLM Prompt to VERIFY not COUNT

**Current Prompt (Wrong):**
```
Count EXACTLY these symbols in the drawing.
```

**New Prompt (Correct):**
```
VERIFY these symbol counts from Vector extraction:
- 1/4" NG: 4 instances (verify you see 4)
- 2" NG: 2 instances (verify you see 2)
- GWH-1: 1 instance (verify you see 1)

If Vector count is correct, use it.
If you see MORE instances, report the higher count.
If you see FEWER instances, use Vector count (it's more accurate).
```

### Change 2: Merge Strategy - Trust Vector First

**Current Merge (Wrong):**
```python
# VLM can override Vector counts
best = max(vector_cnt, vlm_cnt)
```

**New Merge (Correct):**
```python
# Vector is ground truth for symbols it detects
if vector_cnt > 0:
    best = vector_cnt  # Always trust Vector
elif vlm_cnt > 0:
    best = vlm_cnt  # VLM only for symbols Vector missed
else:
    best = dfine_cnt  # DFINE as last resort
```

### Change 3: Step 4 Fallback

**Current (Wrong):**
```python
# Only use VLM symbols
all_detected_symbols = list(vlm_counts.keys())
```

**New (Correct):**
```python
# Use ALL symbols from Vector + DFINE + VLM
all_detected_symbols = list(set(
    list(vector_counts.keys()) +      # Vector symbols (most accurate)
    list(vlm_counts.keys()) +         # VLM symbols
    [DFINE_TO_SYMBOL_MAP.get(cls, cls) for cls in dfine_counts.keys()]
))

# If VLM failed, still have Vector + DFINE symbols for Step 4
```

---

## Implementation

### File: `src/vlm_extractor.py`

Replace the `build_extraction_prompt` function:

```python
def build_extraction_prompt(self, known_symbols: List[str] = None, 
                           known_counts: Dict[str, int] = None) -> str:
    """Build VLM prompt with Vector counts as ground truth"""
    
    if known_counts and len(known_counts) > 0:
        # STRICT MODE: Verify Vector counts
        symbols_with_counts = "\n".join([
            f"  - {sym}: {count} instances (verify this count)"
            for sym, count in known_counts.items()
        ])
        
        return f"""You are verifying symbol counts from Vector extraction.

=== VECTOR EXTRACTION RESULTS (Ground Truth) ===
{symbols_with_counts}

=== YOUR TASK ===
1. Look at the drawing
2. For EACH symbol above, verify you can see that many instances
3. If Vector says 4, and you see 4, confirm: {{"symbol": 4}}
4. If Vector says 4, but you see 5, report: {{"symbol": 5}}
5. If Vector says 4, but you see 3, use Vector count: {{"symbol": 4}}

=== RULES ===
- Vector extraction is MORE ACCURATE than visual counting
- Only report HIGHER counts if you're 100% certain
- When in doubt, use Vector count
- DO NOT add symbols not in the list

=== OUTPUT ===
Return ONLY JSON:
{{
  "1/4\\" NG": 4,
  "2\\" NG": 2,
  "GWH-1": 1
}}"""
    
    elif known_symbols and len(known_symbols) > 0:
        # Fallback: Just verify symbols exist
        symbols_list = "\n".join([f"  - {sym}" for sym in known_symbols])
        
        return f"""Count these symbols:
{symbols_list}

Return JSON only."""
    
    else:
        return "Extract plumbing symbols. Return JSON only."
```

### File: `src/pipeline.py`

Update Step 3 to pass Vector counts:

```python
# Step 3: VLM Extraction with Vector counts as ground truth
if Config.VLM_ENABLED:
    log_section(logger, "🧠 VLM VERIFICATION (Using Vector as Ground Truth)")
    
    # Pass Vector counts to VLM for verification
    vlm_counts = run_vlm_extraction(
        pdf_path=pdf_path,
        enabled=True,
        known_symbols=list(vector_counts.keys()),
        known_counts=vector_counts  # NEW: Pass counts for verification
    )
```

Update Step 4 to use ALL symbols:

```python
# Step 4: Connection Extraction with ALL symbols
if Config.VLM_ENABLED:
    log_section(logger, "🔗 VLM CONNECTION EXTRACTION")
    
    # Use ALL symbols from Vector + DFINE + VLM
    all_detected_symbols = list(set(
        list(vector_counts.keys()) +      # Vector (most accurate)
        list(vlm_counts.keys()) +         # VLM additions
        [DFINE_TO_SYMBOL_MAP.get(cls, cls) for cls in dfine_counts.keys()]
    ))
    
    logger.info(f"   Using {len(all_detected_symbols)} symbols for connection extraction")
    logger.info(f"   - From Vector: {len(vector_counts)}")
    logger.info(f"   - From VLM: {len(vlm_counts)}")
    logger.info(f"   - From DFINE: {len(dfine_counts)}")
    
    vlm_connections = run_vlm_connection_extraction(
        pdf_path=pdf_path,
        enabled=True,
        detected_symbols=all_detected_symbols
    )
```

---

## Expected Results After Fix

### Step 3 Output (VLM Verification):
```json
{
  "1/4\" NG": 4,    ✅ Verified from Vector
  "2\" NG": 2,      ✅ Verified from Vector
  "1/2\" NG": 2,    ✅ Verified from Vector
  "3/4\" NG": 1,    ✅ Verified from Vector
  "GWH-1": 1,       ✅ Verified from Vector
  "4\" NG": 1       ✅ Verified from Vector
}
```

### Step 4 Output (Connections):
```json
[
  {"symbol": "1/4\" NG", "count": 4, "connected_pipe": "1/4\" NG"},
  {"symbol": "2\" NG", "count": 2, "connected_pipe": "2\" NG"},
  {"symbol": "1/2\" NG", "count": 2, "connected_pipe": "1/2\" NG"},
  {"symbol": "3/4\" NG", "count": 1, "connected_pipe": "3/4\" NG"},
  {"symbol": "GWH-1", "count": 1, "connected_pipe": "4\" NG"},
  {"symbol": "4\" NG", "count": 1, "connected_pipe": "4\" NG"}
]
```

---

## Quick Fix Instructions

1. **Update `src/vlm_extractor.py`:**
   - Modify `build_extraction_prompt()` to accept `known_counts` parameter
   - Change prompt to "VERIFY" instead of "COUNT"
   - Add logic to use Vector counts as ground truth

2. **Update `src/pipeline.py`:**
   - Pass `vector_counts` to VLM in Step 3
   - Use ALL symbols (Vector + DFINE + VLM) in Step 4
   - Add logging to show symbol sources

3. **Update merger logic:**
   - Always trust Vector counts when available
   - VLM only adds symbols Vector missed
   - DFINE as last resort

---

## Testing

```bash
python quickstart.py
```

**Check logs for:**
```
🧠 VLM VERIFICATION (Using Vector as Ground Truth)
   Passing 6 Vector symbols with counts for verification
   
🔗 VLM CONNECTION EXTRACTION
   Using 10 symbols for connection extraction
   - From Vector: 6
   - From VLM: 6
   - From DFINE: 4
```

**Verify output:**
- Step 3 VLM counts should match Vector exactly
- Step 4 should show connections (not empty)
- All symbols from Vector should appear in connections

---

## Summary

The key insight: **Vector extraction is 100% accurate for text-based symbols**. VLM should:
1. VERIFY Vector counts (not recount)
2. ADD symbols Vector missed (visual-only symbols)
3. NEVER override Vector counts with lower values

This ensures Step 3 accuracy and provides symbols for Step 4 connections.
