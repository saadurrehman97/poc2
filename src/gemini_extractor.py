"""
Gemini-based Symbol-Pipe Relationship Extraction (Step 5)

Uses Google Gemini's vision capabilities to analyze DFINE-annotated 
engineering drawings and extract relational connections between 
plumbing symbols and pipes.

Flow:
1. DFINE detects symbols → draws bounding boxes on image
2. Annotated image sent to Gemini
3. Gemini reads pipe size labels + traces connections
4. Returns structured connection data with relational nodes
"""

import json
import re
import os
from typing import Dict, List, Optional
from pathlib import Path
from PIL import Image
from collections import defaultdict

from config import Config
from logger_setup import get_logger, log_section

import sys
sys.path.insert(0, '..')
from data.symbol_database import SYMBOL_DB, DFINE_TO_SYMBOL_MAP

logger = get_logger(__name__)


class GeminiRelationExtractor:
    """
    Extracts symbol-to-pipe relational connections using Google Gemini Vision.
    
    Takes DFINE-annotated images (with bounding boxes + class labels) and 
    uses Gemini's OCR + reasoning to identify pipe connections.
    """
    
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or Config.GEMINI_API_KEY
        self.model_name = model or Config.GEMINI_MODEL
        self.model = None
        self._init_client()
    
    def _init_client(self):
        if not self.api_key:
            logger.error("Gemini API key not set. Set GEMINI_API_KEY in config or environment.")
            return
        
        try:
            from google import genai
            
            self.client = genai.Client(api_key=self.api_key)
            self.model = self.model_name  # Model name string used in generate_content
            logger.info(f"   ✓ Gemini initialized: {self.model_name}")
            
        except ImportError:
            logger.error("google-genai not installed. Run: pip install google-genai")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
    
    def build_relationship_prompt(self, detected_classes: Dict[str, int],
                                   fixture_symbols: List[str] = None) -> str:
        """Build prompt for Gemini to extract symbol-pipe relationships."""
        
        symbols_list = []
        for cls_name, count in detected_classes.items():
            display = DFINE_TO_SYMBOL_MAP.get(cls_name, cls_name.replace('_', ' ').title())
            symbols_list.append(f"  - {display} ({cls_name}): {count} detected")
        symbols_formatted = "\n".join(symbols_list)
        
        fixture_info = ""
        if fixture_symbols:
            fixture_lines = [f"  - {sym}: {SYMBOL_DB.get(sym, sym)}" for sym in fixture_symbols]
            fixture_info = f"""
=== FIXTURE SYMBOLS (from engineering schedule) ===
These fixture labels may appear in the drawing:
{chr(10).join(fixture_lines)}
"""
        
        prompt = f"""You are an expert plumbing engineering drawing analyst with OCR capabilities.

=== YOUR TASK ===
Analyze this DFINE-annotated engineering drawing. The colored bounding boxes with labels 
show detected plumbing symbols. Your job is to:

1. IDENTIFY what pipe sizes and types are written near each detected symbol
2. TRACE the pipe connections from each symbol
3. REPORT which symbols connect to which pipes
4. BUILD a pipe network showing how symbols and pipes relate

=== DETECTED SYMBOLS (bounding boxes in the image) ===
{symbols_formatted}
{fixture_info}
=== COMMON PIPE TYPE ABBREVIATIONS ===
CW = Cold Water, HW = Hot Water, HWR = Hot Water Return,
NG = Natural Gas, SAN = Sanitary, V/VENT = Vent pipe,
ST/STM = Steam, CD = Condensate Drain, CA = Compressed Air,
FP = Fire Protection, GW = Grey Water, SD = Storm Drain

=== WHAT TO LOOK FOR ===
1. Near each bounding box, find pipe size labels like "1/2\\" CW", "3/4\\" HW", "1\\" NG", "2\\" SAN"
2. Pipe sizes are written along pipe lines near symbols
3. For fixture symbols (WC-1, LAV, etc.), identify ALL connected pipes
4. For inline symbols (valves, strainers), identify the pipe they are installed on
5. If a pipe changes size at a symbol, note both sides

=== OUTPUT FORMAT ===
Return ONLY a JSON object with this structure:
{{
  "symbol_connections": [
    {{
      "symbol_class": "gate_valve",
      "display_name": "Gate Valve",
      "instance_count": 5,
      "connections": [
        {{
          "pipe_size": "1 1/4\\"",
          "pipe_type": "CW",
          "full_label": "1 1/4\\" CW",
          "connection_count": 3,
          "connection_role": "inline"
        }}
      ]
    }}
  ],
  "pipe_network": [
    {{
      "pipe_label": "1 1/4\\" CW",
      "pipe_size": "1 1/4\\"",
      "pipe_type": "CW",
      "connected_symbols": [
        {{"symbol": "gate_valve", "count": 3}},
        {{"symbol": "check_valve", "count": 2}}
      ],
      "total_symbol_connections": 5
    }}
  ],
  "fixture_connections": [
    {{
      "fixture_id": "WC-1",
      "fixture_name": "Standard Water Closet",
      "supply_pipes": ["1/2\\" CW"],
      "waste_pipes": ["4\\" SAN"],
      "vent_pipes": ["2\\" V"]
    }}
  ],
  "summary": {{
    "total_symbols_analyzed": 15,
    "total_pipe_types_found": 5,
    "total_connections_found": 25
  }}
}}

=== CRITICAL RULES ===
1. ONLY report connections you can CLEARLY see in the drawing
2. Read pipe size labels carefully - distinguish 1/2" from 1/4" from 1 1/2"
3. A single symbol can connect to multiple pipes of different sizes/types
4. DO NOT guess or hallucinate - if you cannot read a label, skip it
5. Use "inline" for valves/fittings on a pipe, "terminal" for fixture endpoints, "branch" for branches
6. Return ONLY valid JSON, no other text"""
        
        return prompt
    
    def extract_from_image(self, image_path: str,
                           detected_classes: Dict[str, int],
                           fixture_symbols: List[str] = None,
                           page_num: int = None) -> Dict:
        """Extract relationships from a single DFINE-annotated image."""
        
        if not self.model:
            logger.error("Gemini not initialized.")
            return self._empty_result()
        
        page_label = f" (Page {page_num})" if page_num else ""
        logger.info(f"   📸 Sending annotated image to Gemini{page_label}...")
        
        try:
            from google.genai import types
            
            img = Image.open(image_path)
            logger.info(f"      Image: {img.size[0]}x{img.size[1]}")
            
            prompt = self.build_relationship_prompt(
                detected_classes=detected_classes,
                fixture_symbols=fixture_symbols
            )
            
            logger.info(f"      Calling {self.model_name}...")
            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt, img],
                config=types.GenerateContentConfig(
                    temperature=Config.GEMINI_TEMPERATURE,
                    top_p=0.95,
                    max_output_tokens=8192,
                )
            )
            
            result = self._parse_response(response.text)
            
            if result:
                sc = len(result.get('symbol_connections', []))
                pn = len(result.get('pipe_network', []))
                fc = len(result.get('fixture_connections', []))
                logger.info(f"      ✅ Gemini: {sc} symbol groups, {pn} pipe types, {fc} fixture mappings")
            else:
                logger.warning("      ⚠️ Empty or invalid Gemini response")
            
            return result or self._empty_result()
            
        except Exception as e:
            logger.error(f"   ❌ Gemini failed{page_label}: {e}")
            
            # Retry once
            try:
                logger.info("      Retrying...")
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=[prompt, img],
                    config=types.GenerateContentConfig(
                        temperature=Config.GEMINI_TEMPERATURE,
                        max_output_tokens=8192,
                    )
                )
                result = self._parse_response(response.text)
                return result or self._empty_result()
            except Exception as retry_e:
                logger.error(f"      Retry failed: {retry_e}")
            
            return self._empty_result()
    
    def extract_from_pages(self, page_image_paths: List[str],
                           detected_classes: Dict[str, int],
                           fixture_symbols: List[str] = None) -> Dict:
        """Extract relationships from multiple annotated page images and aggregate."""
        
        all_sym_conns = defaultdict(lambda: defaultdict(lambda: {"count": 0, "role": "unknown"}))
        all_pipe_net = defaultdict(lambda: defaultdict(int))
        all_fixture_conns = {}
        
        for idx, img_path in enumerate(page_image_paths, 1):
            logger.info(f"\n   Page {idx}/{len(page_image_paths)}:")
            
            page_result = self.extract_from_image(
                image_path=img_path,
                detected_classes=detected_classes,
                fixture_symbols=fixture_symbols,
                page_num=idx
            )
            
            # Aggregate symbol connections
            for sc in page_result.get('symbol_connections', []):
                symbol = sc.get('symbol_class', '')
                for conn in sc.get('connections', []):
                    pipe = conn.get('full_label', '')
                    count = conn.get('connection_count', 1)
                    role = conn.get('connection_role', 'unknown')
                    all_sym_conns[symbol][pipe]["count"] += count
                    all_sym_conns[symbol][pipe]["role"] = role
            
            # Aggregate pipe network
            for pn in page_result.get('pipe_network', []):
                pipe = pn.get('pipe_label', '')
                for sym_info in pn.get('connected_symbols', []):
                    sym = sym_info.get('symbol', '')
                    cnt = sym_info.get('count', 1)
                    all_pipe_net[pipe][sym] += cnt
            
            # Aggregate fixture connections
            for fc in page_result.get('fixture_connections', []):
                fid = fc.get('fixture_id', '')
                if fid and fid not in all_fixture_conns:
                    all_fixture_conns[fid] = fc
                elif fid:
                    existing = all_fixture_conns[fid]
                    for pk in ['supply_pipes', 'waste_pipes', 'vent_pipes']:
                        existing[pk] = list(set(existing.get(pk, []) + fc.get(pk, [])))
        
        return self._build_aggregated(all_sym_conns, all_pipe_net, all_fixture_conns)
    
    def _build_aggregated(self, sym_conns, pipe_net, fixture_conns) -> Dict:
        """Build final aggregated result."""
        sc_list = []
        for symbol, pipes in sym_conns.items():
            display = DFINE_TO_SYMBOL_MAP.get(symbol, symbol.replace('_', ' ').title())
            conns = []
            for pipe, info in pipes.items():
                parts = pipe.rsplit(' ', 1)
                conns.append({
                    "pipe_size": parts[0] if len(parts) > 1 else pipe,
                    "pipe_type": parts[1] if len(parts) > 1 else "",
                    "full_label": pipe,
                    "connection_count": info["count"],
                    "connection_role": info["role"]
                })
            sc_list.append({
                "symbol_class": symbol,
                "display_name": display,
                "instance_count": sum(c["connection_count"] for c in conns),
                "connections": conns
            })
        
        pn_list = []
        for pipe, symbol_counts in pipe_net.items():
            parts = pipe.rsplit(' ', 1)
            pn_list.append({
                "pipe_label": pipe,
                "pipe_size": parts[0] if len(parts) > 1 else pipe,
                "pipe_type": parts[1] if len(parts) > 1 else "",
                "connected_symbols": [{"symbol": s, "count": c} for s, c in symbol_counts.items()],
                "total_symbol_connections": sum(symbol_counts.values())
            })
        
        fc_list = list(fixture_conns.values())
        
        total_conns = sum(
            sum(c["connection_count"] for c in sc["connections"])
            for sc in sc_list
        )
        
        return {
            "symbol_connections": sc_list,
            "pipe_network": pn_list,
            "fixture_connections": fc_list,
            "summary": {
                "total_symbols_analyzed": len(sc_list),
                "total_pipe_types_found": len(pn_list),
                "total_connections_found": total_conns
            }
        }
    
    def _parse_response(self, response_text: str) -> Optional[Dict]:
        """Parse Gemini's JSON response."""
        cleaned = re.sub(r'```json\s*|\s*```', '', response_text).strip()
        
        try:
            data = json.loads(cleaned)
            return self._validate(data)
        except json.JSONDecodeError:
            pass
        
        # Fallback: find JSON block
        match = re.search(r'\{[\s\S]*\}', cleaned)
        if match:
            try:
                data = json.loads(match.group())
                return self._validate(data)
            except json.JSONDecodeError:
                pass
        
        logger.warning(f"Could not parse Gemini response: {cleaned[:300]}")
        return None
    
    def _validate(self, data: Dict) -> Optional[Dict]:
        if not isinstance(data, dict):
            return None
        return {
            "symbol_connections": data.get("symbol_connections", []),
            "pipe_network": data.get("pipe_network", []),
            "fixture_connections": data.get("fixture_connections", []),
            "summary": data.get("summary", {
                "total_symbols_analyzed": 0,
                "total_pipe_types_found": 0,
                "total_connections_found": 0
            })
        }
    
    def _empty_result(self) -> Dict:
        return {
            "symbol_connections": [],
            "pipe_network": [],
            "fixture_connections": [],
            "summary": {
                "total_symbols_analyzed": 0,
                "total_pipe_types_found": 0,
                "total_connections_found": 0
            }
        }


def run_gemini_extraction(image_paths: List[str] = None,
                          single_image_path: str = None,
                          detected_classes: Dict[str, int] = None,
                          fixture_symbols: List[str] = None,
                          api_key: str = None) -> Dict:
    """
    Main entry point for Gemini relationship extraction (Step 5).
    
    Args:
        image_paths: List of annotated page images (multi-page PDF)
        single_image_path: Single annotated image path
        detected_classes: DFINE counts {class_name: count}
        fixture_symbols: Fixture symbols from SYMBOL_DB
        api_key: Optional API key override
    
    Returns:
        Dict with symbol_connections, pipe_network, fixture_connections, summary
    """
    if not Config.GEMINI_ENABLED:
        logger.info("Gemini extraction disabled")
        return GeminiRelationExtractor()._empty_result()
    
    extractor = GeminiRelationExtractor(api_key=api_key)
    
    if not extractor.model:
        logger.error("Gemini not available. Skipping.")
        return extractor._empty_result()
    
    if image_paths and len(image_paths) > 0:
        return extractor.extract_from_pages(
            page_image_paths=image_paths,
            detected_classes=detected_classes or {},
            fixture_symbols=fixture_symbols
        )
    elif single_image_path:
        return extractor.extract_from_image(
            image_path=single_image_path,
            detected_classes=detected_classes or {},
            fixture_symbols=fixture_symbols
        )
    else:
        logger.warning("No image provided for Gemini extraction")
        return extractor._empty_result()
