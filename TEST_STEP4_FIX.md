# Testing Step 4 Fixture Filter Fix

## Quick Test

### 1. Run the pipeline
```bash
python app.py your_plumbing_drawing.pdf
```

### 2. Check the console output for Step 4

Look for this section:
```
🔗 VLM SYMBOL-PIPE CONNECTION EXTRACTION (Step 4)
   📋 Analyzing connections for X FIXTURE symbols (from SYMBOL_DB)
      - From Vector: X fixtures (filtered from Y total)
      - From DFINE: X fixtures (filtered from Y total)
      ℹ️  Excluded: pipe sizes (1/2" NG, etc.) and DFINE classes (Riser Up Elbow, etc.)
```

### 3. Check the results.json file

Open `output_directory/results.json` and look at the `vlm.connections` section:

**✅ GOOD - Should see:**
```json
"connections": [
  {"symbol": "EWS-1", "count": 1, "pipe": "1 1/2\" CW"},
  {"symbol": "EWS-1", "count": 1, "pipe": "2\" SAN"},
  {"symbol": "GWH-1", "count": 1, "pipe": "4\" NG"},
  {"symbol": "MS-1", "count": 2, "pipe": "1/2\" CW"}
]
```

**❌ BAD - Should NOT see:**
```json
"connections": [
  {"symbol": "1/2\" NG", "count": 2, "pipe": "1/2\" NG"},  // Pipe to itself
  {"symbol": "Riser Up Elbow", "count": 1, "pipe": "4\" NG"},  // DFINE class
  {"symbol": "ball_valve", "count": 2, "pipe": "1 1/2\" CW"}  // DFINE class
]
```

### 4. Check the app.py table output

The Step 4 table should only show fixture symbols:

**✅ GOOD:**
```
Symbol-to-Pipe Connections (Step 4):
Symbol    Count  Connection
--------  -----  ------------
EWS-1     1      1 1/2" CW
EWS-1     1      2" SAN
GWH-1     1      4" NG
MS-1      2      1/2" CW
```

**❌ BAD:**
```
Symbol-to-Pipe Connections (Step 4):
Symbol           Count  Connection
---------------  -----  ------------
1/2" NG          2      1/2" NG        ← Should NOT appear
Riser Up Elbow   1      4" NG          ← Should NOT appear
ball_valve       2      1 1/2" CW      ← Should NOT appear
```

## What Changed?

### Before Fix:
- Step 4 received ALL symbols (Vector + DFINE)
- Included pipe sizes: 1/2" NG, 3/4" CW, 2" SAN, etc.
- Included DFINE classes: ball_valve, gate_valve, Riser Up Elbow, etc.
- VLM tried to find connections for everything → hallucinations

### After Fix:
- Step 4 receives ONLY fixture symbols from SYMBOL_DB
- Filters out pipe sizes (1/2" NG, etc.)
- Filters out DFINE classes (ball_valve, etc.)
- VLM only analyzes real fixtures → accurate results

## Fixture Symbols (from SYMBOL_DB)

These are the ONLY symbols that should appear in Step 4:

```
AC-1, DN-1, EWC-1, EWC-2, EWS-1, FCO-1, FD-1, FD-2, GWH-1, HB-1,
MS-1, RP-1, S-1, S-2, SS-1, SS-2, UR-1, WC-1, WC-2, WCO-1, WF-1,
WF-2, WH-1, WH-2, HR-1, LAV
```

## Debugging

If you still see pipe sizes or DFINE classes in Step 4:

1. **Check the console logs** - Look for filter messages:
   ```
   ✗ Filtered out non-fixture symbol: 1/2" NG
   ✗ Filtered out pipe-to-pipe connection: 1/2" NG → 1/2" NG
   ```

2. **Verify SYMBOL_DB** - Make sure `data/symbol_database.py` has all your fixtures

3. **Check VLM model** - Ensure you're using qwen3-vl:30b:
   ```bash
   ollama list | grep qwen
   ```

4. **Increase VLM timeout** - In `src/config.py`:
   ```python
   VLM_TIMEOUT = 300  # Increase from 180 to 300 seconds
   ```

## Expected Performance

- **Vector extraction**: 100% accurate (unchanged)
- **DFINE detection**: Good for visual symbols (unchanged)
- **VLM Step 3**: Skipped (using Vector counts directly)
- **VLM Step 4**: Now focused on fixtures only → better accuracy

## Success Criteria

✅ Step 4 table shows ONLY fixture symbols from SYMBOL_DB
✅ No pipe-to-pipe connections (e.g., "1/2" NG → 1/2" NG")
✅ No DFINE classes (e.g., "Riser Up Elbow", "ball_valve")
✅ Connections make sense (e.g., "EWS-1 → 1 1/2" CW")
✅ No hallucinated symbols that don't exist in the drawing
