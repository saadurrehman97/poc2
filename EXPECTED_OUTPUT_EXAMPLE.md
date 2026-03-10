# 📊 Expected Output Examples - Grounded VLM

## What You Should See After Running the Pipeline

---

## Console Output (Logs)

### Step 1: Vector Extraction
```
📝 VECTOR TEXT EXTRACTION
   📄 Processing 1 vector-based page(s): [1]
   ✓ Found 8 unique symbols (25 instances)
```

### Step 2: DFINE Detection
```
🔍 DFINE OBJECT DETECTION
   Page 1: detecting...
      Found 45 objects after NMS
      Saved 12 tiles with detections to: detected_tiles/
      Saved full image: full_image_detected_page_01.jpg

✅ DFINE total: 45 detections, 12 classes
```

### Step 3: VLM Extraction (GROUNDED)
```
🧠 VLM SYMBOL EXTRACTION (Grounded Multi-DPI)
   Grounding VLM with 15 symbols from Vector+DFINE
   
   Page 1/1:
     Rendering at 400DPI...
     400DPI: 12 symbols found
     Rendering at 500DPI...
     500DPI: 13 symbols found
     Rendering at 600DPI...
     600DPI: 12 symbols found
     Combined from 3 DPI(s): 12 symbols

✓ VLM extracted 12 unique symbols
  Total instances: 38
```

### Step 4: Connection Extraction (GROUNDED)
```
🔗 VLM SYMBOL-PIPE CONNECTION EXTRACTION (Step 4 - Grounded)
   Grounding connections with 18 confirmed symbols
   
   Page 1/1:
     Rendering at 400DPI...
     400DPI: 8 symbols with connections

✓ VLM extracted 25 symbol-pipe connections
```

---

## JSON Output (`results.json`)

### Complete Structure
```json
{
  "document": "/workspace/P1.1-PLUMBING-PLAN-Rev.1.pdf",
  "file_type": "PDF",
  "timestamp": "20260227_143022",
  "output_directory": "./outputs/P1.1-PLUMBING-PLAN-Rev.1_20260227_143022",
  
  "aggregated": {
    "vector": {
      "by_symbol": {
        "WC-1": 5,
        "AC-1": 2,
        "EWC-1": 3,
        "LAV": 4,
        "UR-1": 2,
        "MS-1": 1,
        "FD-1": 3,
        "HB-1": 5
      }
    },
    
    "dfine": {
      "by_class": {
        "ball_valve": 8,
        "gate_valve": 5,
        "check_valve": 3,
        "elbow": 15,
        "riser_down_elbow": 4,
        "riser_up_elbow": 6,
        "cleanout": 2,
        "floor_cleanout": 2,
        "hose_bibb": 5,
        "wall_hydrant": 3,
        "strainer": 2,
        "pressure_regulating_valve": 1
      },
      "total_detections": 45
    },
    
    "vlm": {
      "by_symbol": {
        "WC-1": 5,
        "AC-1": 2,
        "ball_valve": 8,
        "gate_valve": 5,
        "check_valve": 3,
        "elbow": 15,
        "EWC-1": 3,
        "LAV": 4,
        "UR-1": 2,
        "MS-1": 1,
        "FD-1": 3,
        "HB-1": 5
      },
      "total_symbols": 12,
      "total_instances": 38,
      
      "connections": [
        {
          "symbol": "ball_valve",
          "count": 2,
          "pipe": "1 1/2\" CW"
        },
        {
          "symbol": "ball_valve",
          "count": 5,
          "pipe": "3/4\" HW"
        },
        {
          "symbol": "ball_valve",
          "count": 1,
          "pipe": "1\" NG"
        },
        {
          "symbol": "gate_valve",
          "count": 5,
          "pipe": "1 3/4\" CA"
        },
        {
          "symbol": "check_valve",
          "count": 3,
          "pipe": "2\" SAN"
        },
        {
          "symbol": "pressure_regulating_valve",
          "count": 1,
          "pipe": "2\" SAN"
        },
        {
          "symbol": "WC-1",
          "count": 5,
          "pipe": "1/2\" CW"
        },
        {
          "symbol": "WC-1",
          "count": 5,
          "pipe": "2\" SAN"
        },
        {
          "symbol": "WC-1",
          "count": 5,
          "pipe": "4\" SAN"
        },
        {
          "symbol": "EWC-1",
          "count": 3,
          "pipe": "1/2\" CW"
        },
        {
          "symbol": "EWC-1",
          "count": 3,
          "pipe": "2/3\" HW"
        },
        {
          "symbol": "EWC-1",
          "count": 3,
          "pipe": "4\" CA"
        },
        {
          "symbol": "LAV",
          "count": 4,
          "pipe": "1/2\" CW"
        },
        {
          "symbol": "LAV",
          "count": 4,
          "pipe": "1/2\" HW"
        },
        {
          "symbol": "LAV",
          "count": 4,
          "pipe": "1 1/2\" SAN"
        },
        {
          "symbol": "UR-1",
          "count": 2,
          "pipe": "3/4\" CW"
        },
        {
          "symbol": "UR-1",
          "count": 2,
          "pipe": "2\" SAN"
        },
        {
          "symbol": "MS-1",
          "count": 1,
          "pipe": "1/2\" CW"
        },
        {
          "symbol": "MS-1",
          "count": 1,
          "pipe": "1/2\" HW"
        },
        {
          "symbol": "MS-1",
          "count": 1,
          "pipe": "2\" SAN"
        },
        {
          "symbol": "FD-1",
          "count": 3,
          "pipe": "2\" SAN"
        },
        {
          "symbol": "HB-1",
          "count": 5,
          "pipe": "3/4\" CW"
        },
        {
          "symbol": "elbow",
          "count": 8,
          "pipe": "1 1/2\" CW"
        },
        {
          "symbol": "elbow",
          "count": 7,
          "pipe": "3/4\" HW"
        },
        {
          "symbol": "riser_down_elbow",
          "count": 4,
          "pipe": "2\" SAN"
        }
      ]
    }
  },
  
  "final_best_estimates": {
    "Standard Water Closet (WC-1)": 5,
    "Air Conditioner (AC-1)": 2,
    "Single-Level Electric Water Cooler (EWC-1)": 3,
    "Lavatory (LAV)": 4,
    "Urinal (UR-1)": 2,
    "Mop Sink (MS-1)": 1,
    "DUCO Cast Iron Floor Drain (FD-1)": 3,
    "Hose Bibb (HB-1)": 5,
    "Ball valve (ball_valve)": 8,
    "Gate valve (gate_valve)": 5,
    "Check valve (check_valve)": 3,
    "Elbow (elbow)": 15,
    "Riser Down Elbow (riser_down_elbow)": 4,
    "Riser Up Elbow (riser_up_elbow)": 6,
    "Cleanout (cleanout)": 2,
    "Floor Cleanout (floor_cleanout)": 2,
    "Wall Hydrant (wall_hydrant)": 3,
    "Strainer (strainer)": 2,
    "Pressure Regulating Valve (pressure_regulating_valve)": 1
  }
}
```

---

## Streamlit UI Display

### 📊 Extraction Summary (Top Metrics)

```
┌─────────────┬──────────────────┬────────────────┬─────────────┐
│ Total Pages │ DFINE Detections │ Vector Symbols │ VLM Symbols │
├─────────────┼──────────────────┼────────────────┼─────────────┤
│      1      │        45        │       25       │     38      │
└─────────────┴──────────────────┴────────────────┴─────────────┘
```

### 🏆 Final Best Estimates

| Symbol | Count |
|--------|-------|
| Standard Water Closet (WC-1) | 5 |
| Elbow (elbow) | 15 |
| Ball valve (ball_valve) | 8 |
| Riser Up Elbow (riser_up_elbow) | 6 |
| Gate valve (gate_valve) | 5 |
| Hose Bibb (HB-1) | 5 |
| Lavatory (LAV) | 4 |
| Riser Down Elbow (riser_down_elbow) | 4 |
| Single-Level Electric Water Cooler (EWC-1) | 3 |
| DUCO Cast Iron Floor Drain (FD-1) | 3 |
| Check valve (check_valve) | 3 |
| Wall Hydrant (wall_hydrant) | 3 |
| Air Conditioner (AC-1) | 2 |
| Urinal (UR-1) | 2 |
| Cleanout (cleanout) | 2 |
| Floor Cleanout (floor_cleanout) | 2 |
| Strainer (strainer) | 2 |
| Mop Sink (MS-1) | 1 |
| Pressure Regulating Valve (pressure_regulating_valve) | 1 |

### 🔗 Symbol-to-Pipe Connections (Step 4)

**This is the NEW table showing relationships:**

| Symbol | Count | Connected Pipe |
|--------|-------|----------------|
| Ball valve | 2 | 1 1/2" CW |
| Ball valve | 5 | 3/4" HW |
| Ball valve | 1 | 1" NG |
| Gate valve | 5 | 1 3/4" CA |
| Check valve | 3 | 2" SAN |
| Pressure Regulating Valve | 1 | 2" SAN |
| Standard Water Closet | 5 | 1/2" CW |
| Standard Water Closet | 5 | 2" SAN |
| Standard Water Closet | 5 | 4" SAN |
| Single-Level Electric Water Cooler | 3 | 1/2" CW |
| Single-Level Electric Water Cooler | 3 | 2/3" HW |
| Single-Level Electric Water Cooler | 3 | 4" CA |
| Lavatory | 4 | 1/2" CW |
| Lavatory | 4 | 1/2" HW |
| Lavatory | 4 | 1 1/2" SAN |
| Urinal | 2 | 3/4" CW |
| Urinal | 2 | 2" SAN |
| Mop Sink | 1 | 1/2" CW |
| Mop Sink | 1 | 1/2" HW |
| Mop Sink | 1 | 2" SAN |
| DUCO Cast Iron Floor Drain | 3 | 2" SAN |
| Hose Bibb | 5 | 3/4" CW |
| Elbow | 8 | 1 1/2" CW |
| Elbow | 7 | 3/4" HW |
| Riser Down Elbow | 4 | 2" SAN |

**Info Message:**
```
✅ Found 25 symbol-pipe connection mappings across 12 unique symbols
```

### 🔍 Detailed Comparison

| Category | Symbol | Vector Count | VLM Count | DFINE Count | Best Estimate |
|----------|--------|--------------|-----------|-------------|---------------|
| Standard Water Closet | Standard Water Closet (WC-1) | 5 | 5 | 0 | 5 |
| Air Conditioner | Air Conditioner (AC-1) | 2 | 2 | 0 | 2 |
| Ball Valve | Ball valve (ball_valve) | 0 | 8 | 8 | 8 |
| Gate Valve | Gate valve (gate_valve) | 0 | 5 | 5 | 5 |
| Check Valve | Check valve (check_valve) | 0 | 3 | 3 | 3 |
| Elbow | Elbow (elbow) | 0 | 15 | 15 | 15 |
| ... | ... | ... | ... | ... | ... |

---

## What Changed from Before

### Before (With Hallucination):

**Step 3 VLM Output:**
```json
{
  "WC-1": 5,           ✅ Real
  "AC-1": 2,           ✅ Real
  "ball_valve": 8,     ✅ Real
  "RTU-3": 1,          ❌ HALLUCINATION (not in drawing)
  "1 1/2\" CW": 10,    ❌ HALLUCINATION (not in drawing)
  "CHILLER-1": 2,      ❌ HALLUCINATION (not in drawing)
  "AHU-5": 3           ❌ HALLUCINATION (not in drawing)
}
```

**Step 4 Connections:**
```
⚠️ No symbol-pipe connections detected. This may indicate that:
- VLM connection extraction is disabled
- The drawing clarity or quality is low
- Symbols and pipes are not clearly connected/labeled in the drawing
```

### After (Grounded - No Hallucination):

**Step 3 VLM Output:**
```json
{
  "WC-1": 5,           ✅ Real (confirmed by Vector)
  "AC-1": 2,           ✅ Real (confirmed by Vector)
  "ball_valve": 8,     ✅ Real (confirmed by DFINE)
  "gate_valve": 5,     ✅ Real (confirmed by DFINE)
  "check_valve": 3,    ✅ Real (confirmed by DFINE)
  "elbow": 15          ✅ Real (confirmed by DFINE)
}
```
✅ **No hallucinated symbols!**

**Step 4 Connections:**
```json
[
  {"symbol": "ball_valve", "count": 2, "pipe": "1 1/2\" CW"},
  {"symbol": "ball_valve", "count": 5, "pipe": "3/4\" HW"},
  {"symbol": "gate_valve", "count": 5, "pipe": "1 3/4\" CA"},
  {"symbol": "WC-1", "count": 5, "pipe": "1/2\" CW"},
  {"symbol": "WC-1", "count": 5, "pipe": "2\" SAN"},
  ...
]
```
✅ **Real connections detected!**

---

## Key Indicators of Success

### ✅ Good Signs:

1. **Log shows grounding:**
   ```
   Grounding VLM with 15 symbols from Vector+DFINE
   Grounding connections with 18 confirmed symbols
   ```

2. **All VLM symbols match Vector/DFINE:**
   - Every symbol in VLM output should appear in Vector or DFINE
   - No random symbols like "RTU-3", "CHILLER-1", etc.

3. **Step 4 connections are populated:**
   - Table shows multiple connections
   - All symbols in connections match Step 1-3 symbols

4. **Reasonable connection counts:**
   - Connections make sense (e.g., WC-1 connected to CW, HW, SAN pipes)
   - Counts match or are close to symbol counts

### ❌ Warning Signs:

1. **VLM extracts symbols not in Vector/DFINE:**
   - Check if grounding is working
   - Verify logs show "Grounding VLM with X symbols"

2. **Step 4 returns empty:**
   - Check drawing quality
   - Increase DPI: `VLM_DPI_LIST = [600, 800]`
   - Increase timeout: `VLM_TIMEOUT = 900`

3. **Connections for non-existent symbols:**
   - Verify grounding is working
   - Check logs show "Grounding connections with X confirmed symbols"

---

## Summary

With the grounded approach, you should see:

✅ **Step 3**: Only symbols confirmed by Vector/DFINE
✅ **Step 4**: Connections only for confirmed symbols
✅ **No hallucinations**: VLM cannot invent symbols or connections
✅ **Reliable output**: Every symbol and connection is grounded in reality

**The system now provides accurate, trustworthy symbol-to-pipe connection extraction!** 🎯
