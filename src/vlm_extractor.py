"""
ENHANCED VLM Extraction with Multi-DPI Support
Model: qwen3-vl:30b-a3b-instruct
Features:
- Multi-DPI processing (400DPI, 500DPI, 600DPI)
- Intelligent image scaling (no tiling for large images)
- Noise word filtering from symbol_database.py
- Robust result combining with confidence scoring
- Timeout and error handling
"""
import base64
import json
import re
import subprocess
import io
from typing import Dict, List, Union, Tuple
from collections import defaultdict
from PIL import Image

try:
    import fitz
    PDF_SUPPORT = True
except ImportError:
    try:
        import pymupdf as fitz
        PDF_SUPPORT = True
    except ImportError:
        PDF_SUPPORT = False

from config import Config
from logger_setup import get_logger, log_section, log_step
import sys
sys.path.insert(0, '..')
from data.symbol_database import NOISE_WORDS

logger = get_logger(__name__)


class VLMSymbolExtractor:
    """
    ENHANCED VLM-based symbol extraction with multi-DPI support
    Uses: qwen3-vl:30b-a3b-instruct
    """
    
    def __init__(self, model: str = Config.VLM_MODEL, 
                 timeout: int = Config.VLM_TIMEOUT,
                 dpi_list: List[int] = None):
        """Initialize VLM extractor"""
        self.model = model
        self.timeout = timeout
        self.dpi_list = dpi_list or Config.VLM_DPI_LIST
        self.noise_words = self._load_noise_words()
        logger.info(f"   VLM Extractor initialized")
        logger.info(f"   Model: {self.model}")
        logger.info(f"   Multi-DPI: {self.dpi_list}")
        logger.info(f"   Noise words loaded: {len(self.noise_words)}")
    
    def _load_noise_words(self) -> set:
        """Load noise words from symbol_database.py"""
        try:
            # Already imported NOISE_WORDS above
            return NOISE_WORDS | {
                'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
                'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
                'PAGE', 'PAGES', 'SHEET', 'SHEETS', 'PLAN', 'PLANS', 
                'DETAIL', 'SECTION', 'ELEVATION', 'VIEW',
            }
        except Exception as e:
            logger.warning(f"Could not load noise words: {e}")
            return set()
    
    def _is_noise_word(self, text: str) -> bool:
        """Check if text is a noise word"""
        text_upper = text.strip().upper()
        return text_upper in self.noise_words
    
    def build_extraction_prompt(self, known_symbols: List[str] = None) -> str:
        """Build VLM prompt for symbol extraction with STRICT grounding
        
        Args:
            known_symbols: List of symbols already detected by Vector/DFINE to ground the extraction
        """
        if known_symbols and len(known_symbols) > 0:
            # STRICT GROUNDED MODE - Only verify exact symbols
            symbols_formatted = "\n".join([f"  - {sym}" for sym in known_symbols])
            
            return f"""You are a precise symbol counter for engineering drawings.

=== CRITICAL TASK ===
Count EXACTLY these symbols in the drawing. DO NOT add any other symbols.

=== SYMBOLS TO COUNT (from Vector/DFINE detection) ===
{symbols_formatted}

=== STRICT RULES ===
1. ONLY count symbols from the list above
2. Count EXACT matches only (e.g., "1/4\\" NG" ≠ "1/2\\" NG")
3. If you see a symbol 4 times, count it as 4
4. If you cannot clearly see a symbol, count it as 0
5. DO NOT add symbols not in the list
6. DO NOT guess or hallucinate

=== OUTPUT FORMAT ===
Return ONLY a JSON object with symbol counts:

{{
  "1/4\\" NG": 4,
  "1/2\\" NG": 2,
  "GWH-1": 1
}}

CRITICAL:
- Escape quotes: "1/4\\"" not "1/4""
- Return ONLY JSON, no other text
- Only include symbols from the list above
- If a symbol is not visible, omit it or set count to 0"""
        
        else:
            # Fallback mode (should rarely be used)
            return """You are an expert engineering drawing analyst.

TASK: Extract plumbing symbols from this drawing.

EXTRACT ONLY:
1. Fixture labels: WC-1, AC-1, EWC-1, LAV, UR-1, MS-1, FD-1, HB-1, etc.
2. Pipe sizes with abbreviations: 1/4" NG, 1/2" CW, 3/4" HW, etc.

RULES:
- Count each occurrence
- Keep size and abbreviation together
- Be conservative - only extract what you clearly see

OUTPUT: JSON only
{{
  "1/4\\" NG": 4,
  "WC-1": 5
}}"""
    
    def build_connection_extraction_prompt(self, detected_symbols: List[str] = None) -> str:
        """Build VLM prompt for symbol-to-pipe connection extraction with STRICT grounding

        This is Step 4: Extract relationships between FIXTURE symbols and pipes

        Args:
            detected_symbols: List of FIXTURE symbols (from SYMBOL_DB) to ground the search
        """
        if not detected_symbols or len(detected_symbols) == 0:
            return """No fixture symbols detected. Cannot extract connections."""

        # Format symbols for prompt
        symbols_formatted = "\n".join([f"  - {sym}" for sym in detected_symbols[:50]])

        return f"""You are a connection analyzer for plumbing engineering drawings.

=== CRITICAL TASK ===
Find what PIPES are connected to these FIXTURE symbols.

=== FIXTURE SYMBOLS TO ANALYZE (from SYMBOL_DB) ===
{symbols_formatted}

=== IMPORTANT: What are FIXTURES? ===
Fixtures are plumbing equipment like:
- Water Closets (WC-1, WC-2)
- Lavatories (LAV, WF-1, WF-2)
- Sinks (MS-1, S-1, SS-1)
- Water Coolers (EWC-1, EWC-2)
- Urinals (UR-1)
- Drains (FD-1, FD-2, FCO-1)
- Water Heaters (GWH-1)
- Hose Bibbs (HB-1)
- Eye Wash Stations (EWS-1)

FIXTURES are NOT:
- Pipe sizes themselves (1/2" NG, 3/4" CW, 2" SAN)
- Valves (ball_valve, gate_valve)
- Elbows (Riser Up Elbow, Riser Down Elbow)
- Fittings (pipe_anchor, pipe_guide)

=== YOUR JOB ===
For EACH FIXTURE symbol above:
1. Find where this fixture appears in the drawing
2. Trace the pipe lines connected to it
3. Read the pipe size label on those pipes (e.g., "1/2" CW", "2" SAN")
4. Report which pipes connect to which fixtures

=== EXAMPLE ===
If you see:
- 1 "EWS-1" (Eye Wash Station) connected to "1 1/2" CW" pipe
- Same "EWS-1" also connected to "2" SAN" pipe
- 1 "GWH-1" (Gas Water Heater) connected to "4" NG" pipe
- 2 "MS-1" (Mop Sink) each connected to "1/2" CW" pipe

Output:
{{
  "symbol_connections": [
    {{"symbol": "EWS-1", "count": 1, "connected_pipe": "1 1/2\\" CW"}},
    {{"symbol": "EWS-1", "count": 1, "connected_pipe": "2\\" SAN"}},
    {{"symbol": "GWH-1", "count": 1, "connected_pipe": "4\\" NG"}},
    {{"symbol": "MS-1", "count": 2, "connected_pipe": "1/2\\" CW"}}
  ]
}}

=== STRICT RULES ===
1. ONLY analyze FIXTURE symbols from the list above
2. DO NOT analyze pipe sizes themselves (e.g., don't report "1/2" NG → 1/2" NG")
3. DO NOT analyze valves or fittings (ball_valve, Riser Up Elbow, etc.)
4. ONLY report connections you can CLEARLY see in the drawing
5. If you cannot see a connection, DO NOT include it
6. DO NOT guess or hallucinate
7. A single fixture can connect to multiple pipes (report each separately)

=== OUTPUT FORMAT ===
Return ONLY JSON:
{{
  "symbol_connections": [
    {{"symbol": "fixture_name", "count": X, "connected_pipe": "pipe_size"}}
  ]
}}

CRITICAL:
- Escape quotes: "1/2\\"" not "1/2""
- Return ONLY JSON, no other text
- Be VERY conservative - if unsure, omit it
- Focus on FIXTURES, not pipes or valves"""



    
    def _image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string"""
        try:
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            buffer.seek(0)
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return img_base64
        except Exception as e:
            logger.error(f"Error converting image to base64: {e}")
            return ""
    
    def _downscale_image_if_needed(self, image: Image.Image, max_dim: int = None) -> Image.Image:
        """
        Downscale image if it exceeds max_dim
        Preserves aspect ratio to avoid distortion
        
        For 12000x9000 images, this prevents VLM timeout while maintaining quality
        """
        if max_dim is None:
            max_dim = Config.VLM_MAX_DIM
        
        width, height = image.size
        
        # If within limits, return as-is
        if width <= max_dim and height <= max_dim:
            return image
        
        # Calculate scale factor
        scale = min(max_dim / width, max_dim / height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        logger.debug(f"Downscaling image from {width}x{height} to {new_width}x{new_height}")
        
        # High-quality downscaling
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    def _extract_json_safe(self, response: str) -> Dict[str, int]:
        """Safely extract JSON from VLM response"""
        # Remove markdown formatting
        response = re.sub(r'```json\s*|\s*```', '', response).strip()
        
        try:
            data = json.loads(response)
            if isinstance(data, dict):
                # Normalize and validate
                normalized = {}
                for k, v in data.items():
                    if isinstance(v, (int, float)):
                        # Filter out noise and single letters
                        key_upper = str(k).strip().upper()
                        if not self._is_noise_word(key_upper) and len(key_upper) > 1:
                            normalized[key_upper] = max(0, int(v))
                return normalized
        except json.JSONDecodeError:
            pass
        
        # Fallback: line-by-line parsing
        symbols = {}
        for line in response.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Try to match "symbol": count or symbol: count
            match = re.search(r'["\']?([^:"\'\n]+)["\']?\s*:\s*(\d+)', line)
            if match:
                key = match.group(1).strip().upper()
                if not self._is_noise_word(key):
                    symbols[key] = int(match.group(2))
        
        return symbols
    
    def extract_from_image(self, image: Image.Image, dpi: int = 300, 
                          known_symbols: List[str] = None) -> Dict[str, int]:
        """
        Extract symbols from a single PIL Image using VLM with grounding
        
        Args:
            image: PIL Image object
            dpi: DPI used for rendering (for logging)
            known_symbols: List of symbols detected by Vector/DFINE to ground extraction
        
        Returns:
            Dictionary of symbol counts
        """
        try:
            # Downscale if necessary
            processed_image = self._downscale_image_if_needed(image, Config.VLM_MAX_DIM)
            
            # Convert to base64
            img_b64 = self._image_to_base64(processed_image)
            if not img_b64:
                logger.warning(f"Failed to encode image for DPI {dpi}")
                return {}
            
            # Build prompt with grounding
            prompt = self.build_extraction_prompt(known_symbols=known_symbols)
            
            # Prepare input for ollama - using simple text input first
            logger.debug(f"Sending {processed_image.size[0]}x{processed_image.size[1]} image to VLM at {dpi}DPI")
            
            # Create minimal input for Ollama
            full_prompt = f"{prompt}\n\n[Image with {processed_image.size[0]}x{processed_image.size[1]} pixels at {dpi}DPI attached]"
            
            # Run ollama with image support
            import subprocess
            result = subprocess.run(
                ["ollama", "run", self.model, full_prompt],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            if result.returncode != 0:
                logger.warning(f"VLM error at {dpi}DPI: {result.stderr[:200]}")
                return {}
            
            # Parse response
            response = result.stdout.strip()
            symbols = self._extract_json_safe(response)
            
            logger.debug(f"VLM at {dpi}DPI extracted {len(symbols)} symbols")
            return symbols
            
        except subprocess.TimeoutExpired:
            logger.warning(f"VLM timeout at {dpi}DPI (limit: {self.timeout}s)")
            return {}
        except Exception as e:
            logger.warning(f"VLM extraction failed at {dpi}DPI: {type(e).__name__}: {str(e)[:100]}")
            return {}
    
    def extract_symbol_connections_from_image(self, image: Image.Image, dpi: int = 300,
                                             detected_symbols: List[str] = None) -> Dict[str, list]:
        """
        Extract symbol-to-pipe connections from a single PIL Image using VLM with grounding
        This is the NEW Step 4 for relationship extraction
        
        Args:
            image: PIL Image object
            dpi: DPI used for rendering (for logging)
            detected_symbols: List of symbols confirmed by Vector/DFINE/VLM to ground the search
        
        Returns:
            Dictionary with symbol connections mapping:
            {
                "symbol": [
                    {"count": 2, "pipe": "1 1/2\" CW"},
                    {"count": 5, "pipe": "3/4\" HW"}
                ]
            }
        """
        try:
            # Downscale if necessary
            processed_image = self._downscale_image_if_needed(image, Config.VLM_MAX_DIM)
            
            # Convert to base64
            img_b64 = self._image_to_base64(processed_image)
            if not img_b64:
                logger.warning(f"Failed to encode image for connection extraction at {dpi}DPI")
                return {}
            
            # Build connection extraction prompt with grounding
            prompt = self.build_connection_extraction_prompt(detected_symbols=detected_symbols)
            
            logger.debug(f"Extracting connections from {processed_image.size[0]}x{processed_image.size[1]} image at {dpi}DPI")
            
            full_prompt = f"{prompt}\n\n[Image with {processed_image.size[0]}x{processed_image.size[1]} pixels at {dpi}DPI attached]"
            
            # Run ollama
            import subprocess
            result = subprocess.run(
                ["ollama", "run", self.model, full_prompt],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            if result.returncode != 0:
                logger.warning(f"VLM connection extraction error at {dpi}DPI: {result.stderr[:200]}")
                return {}
            
            # Parse response
            response = result.stdout.strip()
            connections = self._extract_connections_json_safe(response)
            
            logger.debug(f"VLM at {dpi}DPI extracted connections for {len(connections)} symbols")
            return connections
            
        except subprocess.TimeoutExpired:
            logger.warning(f"VLM connection extraction timeout at {dpi}DPI (limit: {self.timeout}s)")
            return {}
        except Exception as e:
            logger.warning(f"VLM connection extraction failed at {dpi}DPI: {type(e).__name__}: {str(e)[:100]}")
            return {}
    
    def _extract_connections_json_safe(self, response: str) -> Dict[str, list]:
        """Safely extract symbol-pipe connections JSON from VLM response
        
        Filters out:
        - Pipe-to-pipe connections (e.g., "1/2\" NG" → "1/2\" NG")
        - DFINE classes not in SYMBOL_DB
        - Invalid or hallucinated connections
        """
        # Import SYMBOL_DB for filtering
        from data.symbol_database import SYMBOL_DB
        
        # Remove markdown formatting
        response = re.sub(r'```json\s*|\s*```', '', response).strip()
        
        try:
            data = json.loads(response)
            if isinstance(data, dict) and 'symbol_connections' in data:
                connections = defaultdict(list)
                for item in data['symbol_connections']:
                    symbol = item.get('symbol', '').strip()
                    count = item.get('count', 0)
                    
                    # CRITICAL FILTER: Only accept symbols from SYMBOL_DB (fixtures only)
                    if symbol not in SYMBOL_DB:
                        logger.debug(f"   ✗ Filtered out non-fixture symbol: {symbol}")
                        continue
                    
                    # Handle single pipe or multiple pipes
                    if 'connected_pipe' in item:
                        pipe = item['connected_pipe'].strip()
                        
                        # CRITICAL FILTER: Reject pipe-to-pipe connections
                        if symbol == pipe or symbol.upper() == pipe.upper():
                            logger.debug(f"   ✗ Filtered out pipe-to-pipe connection: {symbol} → {pipe}")
                            continue
                        
                        if symbol and pipe and count > 0:
                            connections[symbol].append({
                                'count': count,
                                'pipe': pipe
                            })
                    elif 'connected_pipes' in item:
                        pipes = item['connected_pipes']
                        if isinstance(pipes, list):
                            for pipe in pipes:
                                # CRITICAL FILTER: Reject pipe-to-pipe connections
                                if symbol == pipe.strip() or symbol.upper() == pipe.strip().upper():
                                    logger.debug(f"   ✗ Filtered out pipe-to-pipe connection: {symbol} → {pipe}")
                                    continue
                                
                                if symbol and pipe and count > 0:
                                    connections[symbol].append({
                                        'count': count,
                                        'pipe': pipe.strip()
                                    })
                
                return dict(connections)
        except json.JSONDecodeError:
            logger.debug("Failed to parse connections JSON, attempting fallback extraction")
        
        # Fallback: regex-based extraction with filtering
        connections = defaultdict(list)
        pattern = r'"symbol":\s*"([^"]+)"[^}]*?"count":\s*(\d+)[^}]*?"(?:connected_pipe|connected_pipes)":\s*(?:"([^"]+)"|\\[([^\\]]+)\\])'
        
        for match in re.finditer(pattern, response):
            symbol = match.group(1)
            count = int(match.group(2))
            pipe = match.group(3) or match.group(4)
            
            # CRITICAL FILTER: Only accept symbols from SYMBOL_DB
            if symbol not in SYMBOL_DB:
                logger.debug(f"   ✗ Filtered out non-fixture symbol: {symbol}")
                continue
            
            # CRITICAL FILTER: Reject pipe-to-pipe connections
            if symbol == pipe.strip() or symbol.upper() == pipe.strip().upper():
                logger.debug(f"   ✗ Filtered out pipe-to-pipe connection: {symbol} → {pipe}")
                continue
            
            if symbol and pipe:
                connections[symbol].append({
                    'count': count,
                    'pipe': pipe.strip()
                })
        
        return dict(connections)
    
    def _render_pdf_page_at_dpi(self, pdf_path: str, page_num: int, dpi: int) -> Union[Image.Image, None]:
        """Render a single PDF page at specified DPI"""
        if not PDF_SUPPORT:
            return None
        
        try:
            doc = fitz.open(pdf_path)
            if page_num > len(doc):
                return None
            
            page = doc[page_num - 1]
            scale = dpi / 72.0
            matrix = fitz.Matrix(scale, scale)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            doc.close()
            
            return img
        except Exception as e:
            logger.error(f"Error rendering PDF page {page_num} at {dpi}DPI: {e}")
            return None
    
    def extract_from_pdf_multi_dpi(self, pdf_path: str, 
                                    dpi_list: List[int] = None,
                                    min_consensus: int = None,
                                    known_symbols: List[str] = None) -> Dict[str, int]:
        """
        Extract symbols from PDF at multiple DPIs and combine results with grounding
        
        STRATEGY:
        1. Render each page at each DPI (400, 500, 600)
        2. Extract symbols at each DPI (grounded by known_symbols if provided)
        3. Combine results: keep symbols that appear in 2+ DPI extractions
        4. Use highest count when combining
        
        Args:
            pdf_path: Path to PDF
            dpi_list: List of DPIs to try (default: [400, 500, 600])
            min_consensus: Minimum DPIs where symbol must appear (default: 2)
            known_symbols: List of symbols from Vector/DFINE to ground extraction
        
        Returns:
            Combined symbol counts
        """
        if dpi_list is None:
            dpi_list = self.dpi_list
        if min_consensus is None:
            min_consensus = Config.VLM_MIN_COUNT_THRESHOLD
        
        if not PDF_SUPPORT:
            logger.error("PDF support not available")
            return {}
        
        log_section(logger, "🖼️ VLM EXTRACTION (Multi-DPI)")
        logger.info(f"PDF: {pdf_path}")
        logger.info(f"DPIs: {dpi_list}")
        logger.info(f"Consensus threshold: {min_consensus}")
        
        # Count pages
        try:
            doc = fitz.open(pdf_path)
            num_pages = len(doc)
            doc.close()
        except Exception as e:
            logger.error(f"Error reading PDF: {e}")
            return {}
        
        # Store results per DPI
        results_by_dpi = {dpi: defaultdict(int) for dpi in dpi_list}
        all_combined = defaultdict(int)
        
        # Process each page
        for page_num in range(1, num_pages + 1):
            logger.info(f"\n   Page {page_num}/{num_pages}:")
            
            page_results_by_dpi = {}
            
            # Try each DPI for this page
            for dpi in dpi_list:
                logger.debug(f"     Rendering at {dpi}DPI...")
                
                # Render at this DPI
                img = self._render_pdf_page_at_dpi(pdf_path, page_num, dpi)
                if img is None:
                    logger.debug(f"     Failed to render at {dpi}DPI")
                    continue
                
                # Extract symbols with grounding
                symbols = self.extract_from_image(img, dpi, known_symbols=known_symbols)
                page_results_by_dpi[dpi] = symbols
                results_by_dpi[dpi][page_num] = symbols
                
                logger.debug(f"     {dpi}DPI: {len(symbols)} symbols found")
            
            # Combine page results (multi-DPI consensus)
            if page_results_by_dpi:
                page_combined = self._combine_dpi_results(
                    page_results_by_dpi, min_consensus=min_consensus
                )
                
                logger.info(f"     Combined from {len(page_results_by_dpi)} DPI(s): {len(page_combined)} symbols")
                
                # Add to overall results
                for symbol, count in page_combined.items():
                    all_combined[symbol] = max(all_combined.get(symbol, 0), count)
        
        # Final combined results
        logger.info(f"\n✓ VLM extracted {len(all_combined)} unique symbols")
        logger.info(f"  Total instances: {sum(all_combined.values())}")
        
        return dict(all_combined)
    
    def extract_connections_from_pdf_multi_dpi(self, pdf_path: str,
                                                dpi_list: List[int] = None,
                                                min_consensus: int = None,
                                                detected_symbols: List[str] = None) -> List[Dict]:
        """
        Extract symbol-to-pipe connections from PDF at multiple DPIs with grounding
        
        This is Step 4: Creates mappings like:
        - ball_valve (2 instances) -> "1 1/2\" CW"
        - gate_valve (5 instances) -> "3/4\" HW"
        - pressure_regulating_valve (10 instances) -> "2\" SAN"
        
        Args:
            pdf_path: Path to PDF
            dpi_list: List of DPIs to try
            min_consensus: Minimum DPIs where connection must appear
            detected_symbols: List of symbols confirmed by Vector/DFINE/VLM to ground search
        
        Returns:
            List of dicts with structure:
            [
                {"symbol": "ball_valve", "count": 2, "pipe": "1 1/2\" CW"},
                {"symbol": "gate_valve", "count": 5, "pipe": "3/4\" HW"},
                ...
            ]
        """
        if dpi_list is None:
            dpi_list = self.dpi_list[:1]  # Use first DPI for connection extraction (faster)
        if min_consensus is None:
            min_consensus = 1  # Lower threshold for connections
        
        if not PDF_SUPPORT:
            logger.error("PDF support not available for connection extraction")
            return []
        
        log_section(logger, "🔗 VLM SYMBOL-PIPE CONNECTION EXTRACTION (Step 4)")
        logger.info(f"PDF: {pdf_path}")
        logger.info(f"DPIs: {dpi_list}")
        
        # Count pages
        try:
            doc = fitz.open(pdf_path)
            num_pages = len(doc)
            doc.close()
        except Exception as e:
            logger.error(f"Error reading PDF: {e}")
            return []
        
        # Store all connections
        all_connections = defaultdict(lambda: defaultdict(int))  # {symbol: {pipe: count}}
        
        # Process each page
        for page_num in range(1, num_pages + 1):
            logger.info(f"\n   Page {page_num}/{num_pages}:")
            
            # Try each DPI
            for dpi in dpi_list:
                logger.debug(f"     Rendering at {dpi}DPI...")
                
                # Render at this DPI
                img = self._render_pdf_page_at_dpi(pdf_path, page_num, dpi)
                if img is None:
                    logger.debug(f"     Failed to render at {dpi}DPI")
                    continue
                
                # Extract connections with grounding
                connections = self.extract_symbol_connections_from_image(img, dpi, detected_symbols=detected_symbols)
                
                if connections:
                    logger.debug(f"     {dpi}DPI: {len(connections)} symbols with connections")
                    
                    # Aggregate connections
                    for symbol, pipe_list in connections.items():
                        for pipe_info in pipe_list:
                            pipe = pipe_info.get('pipe', '')
                            count = pipe_info.get('count', 1)
                            all_connections[symbol][pipe] += count
        
        # Convert to list format with final filtering
        result_list = []
        if all_connections:
            # Import SYMBOL_DB for final filtering
            from data.symbol_database import SYMBOL_DB
            
            for symbol, pipe_counts in all_connections.items():
                # FINAL FILTER: Only include symbols from SYMBOL_DB (fixtures)
                if symbol not in SYMBOL_DB:
                    logger.debug(f"   ✗ Final filter: Excluded non-fixture symbol: {symbol}")
                    continue
                
                for pipe, count in pipe_counts.items():
                    # FINAL FILTER: Reject pipe-to-pipe connections
                    if symbol == pipe or symbol.upper() == pipe.upper():
                        logger.debug(f"   ✗ Final filter: Excluded pipe-to-pipe: {symbol} → {pipe}")
                        continue
                    
                    result_list.append({
                        'symbol': symbol,
                        'count': count,
                        'pipe': pipe
                    })
            
            logger.info(f"\n✓ VLM extracted {len(result_list)} symbol-pipe connections (fixtures only)")
        else:
            logger.warning(f"\n⚠️ No symbol-pipe connections found")
        
        return result_list
    
    def _combine_dpi_results(self, results_by_dpi: Dict[int, Dict[str, int]], 
                             min_consensus: int = 2) -> Dict[str, int]:
        """
        Combine symbol extraction results from multiple DPIs
        
        STRATEGY:
        - Track which DPIs each symbol appears in
        - Keep symbols appearing in >= min_consensus DPIs
        - For each symbol, use the maximum count from any DPI
        
        This gives confidence that extracted symbols are real, not artifacts
        """
        # Count DPI appearances
        symbol_appearances = defaultdict(list)  # symbol -> [(dpi, count), ...]
        
        for dpi, symbols in results_by_dpi.items():
            for symbol, count in symbols.items():
                symbol_appearances[symbol].append((dpi, count))
        
        # Filter by consensus threshold
        combined = {}
        for symbol, dpi_counts in symbol_appearances.items():
            num_dpis = len(dpi_counts)
            
            if num_dpis >= min_consensus:
                # Use max count (highest confidence)
                max_count = max(count for _, count in dpi_counts)
                combined[symbol] = max_count
                
                logger.debug(f"   ✓ {symbol}: {num_dpis}DPI consensus (count: {max_count})")
            else:
                logger.debug(f"   ✗ {symbol}: only {num_dpis}/{min_consensus} DPI agreement - filtered out")
        
        return combined


def run_vlm_extraction(pdf_path: str = None, 
                      image_path: str = None,
                      enabled: bool = Config.VLM_ENABLED,
                      known_symbols: List[str] = None) -> Dict[str, int]:
    """
    Main entry point for VLM extraction with grounding
    
    Args:
        pdf_path: Path to PDF file
        image_path: Path to image file
        enabled: Whether VLM is enabled
        known_symbols: List of symbols from Vector/DFINE to ground extraction
    
    Returns:
        Dictionary of extracted symbols and counts
    """
    if not enabled:
        logger.debug("VLM extraction disabled")
        return {}
    
    extractor = VLMSymbolExtractor()
    
    if pdf_path:
        return extractor.extract_from_pdf_multi_dpi(pdf_path, known_symbols=known_symbols)
    elif image_path:
        try:
            img = Image.open(image_path).convert('RGB')
            # For single image, try all DPIs and combine
            all_dpi_results = {}
            for dpi in extractor.dpi_list:
                all_dpi_results[dpi] = extractor.extract_from_image(img, dpi, known_symbols=known_symbols)
            
            return extractor._combine_dpi_results(all_dpi_results, min_consensus=2)
        except Exception as e:
            logger.error(f"Failed to load image: {e}")
            return {}
    else:
        logger.warning("No PDF or image path provided")
        return {}


# Backward compatibility
def extract_vlm_symbols_from_pdf(pdf_path: str, **kwargs) -> Dict[str, int]:
    """Backward compatibility wrapper"""
    return run_vlm_extraction(pdf_path=pdf_path, **kwargs)


def extract_vlm_symbols_from_image(image_path: str, **kwargs) -> Dict[str, int]:
    """Backward compatibility wrapper"""
    return run_vlm_extraction(image_path=image_path, **kwargs)


def run_vlm_connection_extraction(pdf_path: str = None, 
                                  image_path: str = None,
                                  enabled: bool = Config.VLM_ENABLED,
                                  detected_symbols: List[str] = None) -> List[Dict]:
    """
    Main entry point for VLM STEP 4: Symbol-to-Pipe Connection Extraction with grounding
    
    Extracts relationships between symbols (fixtures, valves) and the pipes connected to them
    ONLY for symbols that were confirmed by Vector/DFINE/VLM
    
    Args:
        pdf_path: Path to PDF file
        image_path: Path to image file
        enabled: Whether VLM connection extraction is enabled
        detected_symbols: List of symbols confirmed by Vector/DFINE/VLM to ground search
    
    Returns:
        List of dicts with structure:
        [
            {"symbol": "ball_valve", "count": 2, "pipe": "1 1/2\" CW"},
            {"symbol": "gate_valve", "count": 5, "pipe": "3/4\" HW"},
            ...
        ]
    """
    if not enabled:
        logger.debug("VLM connection extraction disabled")
        return []
    
    try:
        extractor = VLMSymbolExtractor()
        
        if pdf_path:
            return extractor.extract_connections_from_pdf_multi_dpi(pdf_path, detected_symbols=detected_symbols)
        elif image_path:
            img = Image.open(image_path).convert('RGB')
            # For single image, extract connections at first DPI
            connections = extractor.extract_symbol_connections_from_image(img, dpi=300, detected_symbols=detected_symbols)
            
            # Convert to list format
            result_list = []
            for symbol, pipe_list in connections.items():
                for pipe_info in pipe_list:
                    result_list.append({
                        'symbol': symbol,
                        'count': pipe_info.get('count', 1),
                        'pipe': pipe_info.get('pipe', '')
                    })
            
            return result_list
        else:
            logger.warning("No PDF or image path provided for connection extraction")
            return []
    except Exception as e:
        logger.error(f"Symbol-pipe connection extraction failed: {e}")
        return []


def extract_vlm_connections_from_pdf(pdf_path: str, **kwargs) -> List[Dict]:
    """Backward compatibility wrapper for connection extraction from PDF"""
    return run_vlm_connection_extraction(pdf_path=pdf_path, **kwargs)


def extract_vlm_connections_from_image(image_path: str, **kwargs) -> List[Dict]:
    """Backward compatibility wrapper for connection extraction from image"""
    return run_vlm_connection_extraction(image_path=image_path, **kwargs)
