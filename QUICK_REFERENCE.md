# 🚀 Quick Reference - Grounded VLM System

## What Was Fixed

❌ **Before**: VLM hallucinated symbols and connections that don't exist
✅ **After**: VLM only extracts symbols confirmed by Vector/DFINE

---

## How It Works (Simple)

```
Step 1: Vector finds symbols → [WC-1, AC-1, LAV]
Step 2: DFINE finds symbols → [ball_valve, gate_valve, elbow]
                                      ↓
                            GROUNDING LIST
                    [WC-1, AC-1, LAV, ball_valve, gate_valve, elbow]
                                      ↓
Step 3: VLM verifies → "Only look for these symbols"
                    → [WC-1, AC-1, ball_valve, gate_valve]
                                      ↓
Step 4: VLM connects → "Only find connections for these symbols"
                    → ball_valve → 1 1/2" CW
                    → gate_valve → 3/4" HW
                    → WC-1 → 1/2" CW, 2" SAN
```

---

## Files Changed

1. **`src/vlm_extractor.py`** - Added grounding parameters to all functions
2. **`src/pipeline.py`** - Passes detected symbols to VLM for grounding

---

## How to Test

```bash
# Run the pipeline
python quickstart.py

# Or use Streamlit
streamlit run app.py
```

**Check logs for:**
```
Grounding VLM with 15 symbols from Vector+DFINE
Grounding connections with 18 confirmed symbols
```

---

## What to Verify

### ✅ Good Output:

**Step 3 (VLM Symbols):**
- All symbols should be in Vector or DFINE output
- No random symbols like "RTU-3", "CHILLER-1"

**Step 4 (Connections):**
- Table shows connections
- All symbols match Steps 1-3
- Connections visible in drawing

### ❌ Bad Output (Old System):

**Step 3:**
```json
{
  "WC-1": 5,        ✅ Real
  "RTU-3": 1,       ❌ Hallucination
  "CHILLER-1": 2    ❌ Hallucination
}
```

**Step 4:**
```
⚠️ No symbol-pipe connections detected
```

---

## Troubleshooting

### Issue: VLM returns fewer symbols

**This is expected!** Grounded approach is conservative.

**Check:**
- Were "missing" symbols hallucinations?
- Do they exist in Vector/DFINE output?

### Issue: Step 4 returns empty

**Solutions:**
1. Increase DPI: `Config.VLM_DPI_LIST = [600, 800]`
2. Increase timeout: `Config.VLM_TIMEOUT = 900`
3. Check drawing quality manually

---

## Configuration

```python
# In src/config.py

# Enable VLM
VLM_ENABLED = True

# Adjust DPI for better quality
VLM_DPI_LIST = [400, 500, 600]  # Or [600, 800] for higher quality

# Increase timeout for large images
VLM_TIMEOUT = 600  # seconds

# Consensus threshold
VLM_MIN_COUNT_THRESHOLD = 2  # Symbol must appear in 2+ DPIs
```

---

## Expected Streamlit UI

### New Table: Symbol-to-Pipe Connections (Step 4)

| Symbol | Count | Connected Pipe |
|--------|-------|----------------|
| Ball valve | 2 | 1 1/2" CW |
| Ball valve | 5 | 3/4" HW |
| Gate valve | 5 | 1 3/4" CA |
| Standard Water Closet | 5 | 1/2" CW |
| Standard Water Closet | 5 | 2" SAN |

**Info:**
```
✅ Found 25 symbol-pipe connection mappings across 12 unique symbols
```

---

## Key Benefits

✅ **No Hallucination** - VLM cannot invent symbols
✅ **Grounded Reasoning** - Each step builds on previous
✅ **Higher Accuracy** - Conservative approach
✅ **Reliable Connections** - Only for confirmed symbols
✅ **Transparent** - Logs show grounding process

---

## Documentation

- **`GROUNDED_VLM_EXTRACTION.md`** - Full technical details
- **`IMPLEMENTATION_SUMMARY.md`** - Complete summary
- **`EXPECTED_OUTPUT_EXAMPLE.md`** - Output examples
- **`QUICK_REFERENCE.md`** - This file

---

## Summary

**Before**: VLM hallucinated → unreliable output
**After**: VLM grounded → reliable, accurate output

**The system now provides trustworthy symbol-to-pipe connections!** 🎯
