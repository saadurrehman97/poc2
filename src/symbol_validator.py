"""
Symbol validation and cleaning utilities
"""
import re
import unicodedata
from typing import List, Dict, Tuple
from collections import defaultdict
from difflib import get_close_matches

import sys
sys.path.append('..')
from data.symbol_database import SYMBOL_DB, NOISE_WORDS, SYMBOL_KEYS, NORMALIZE_MAP

# Symbol validation regexes
SYMBOL_REGEXES = [
    re.compile(r'^[A-Z]{1,5}-\d+[A-Z]?$'),
    re.compile(r'^\d+(\s\d+/\d+|/\d+)?\"\s?[A-Z]{1,5}$'),
    re.compile(r'^[A-Z]{2,4}-\d{2,4}$'),
    re.compile(r'^[A-Z]{1,5}$'),
    re.compile(r'^[A-Z]{1,5}\d+$'),
    re.compile(r'^[0-9/\\\s]+"$'),
]

def normalize_token(t: str) -> str:
    """Normalize a text token"""
    t = t.strip()
    t = t.replace('"', '"').replace('"', '"').replace('′', "'").replace('—', '-').replace('–', '-')
    t = unicodedata.normalize("NFKC", t)
    t = re.sub(r'^[\(\[«]+|[\)\]\.,;:»]+$', '', t)
    return t

def normalize_symbol_key(k: str) -> str:
    """Normalize a symbol key"""
    k = k.strip().upper()
    k = k.replace('IN', '"').replace('"', '"')
    k = NORMALIZE_MAP.get(k, k)
    return k

def is_valid_symbol(text: str) -> bool:
    """Check if a text string is a valid plumbing symbol"""
    text = normalize_token(text).upper()
    text = normalize_symbol_key(text)
    
    if not text or len(text) > 30:
        return False
    
    if len(text) == 1:
        return text in SYMBOL_KEYS and text not in NOISE_WORDS
    
    text = text.strip(',. ')
    
    if text and text[-1] in ',.;:':
        return False
    
    if any(c.islower() for c in text.replace('"', '').replace('/', '').replace('-', '')):
        return False
    
    if not re.match(r'^[A-Z0-9\"/\\\-\s\']+$', text):
        return False
    
    for rx in SYMBOL_REGEXES:
        if rx.match(text):
            if text in NOISE_WORDS:
                return False
            return True
    
    if text in SYMBOL_KEYS and text not in NOISE_WORDS:
        return True
    
    close = get_close_matches(text, SYMBOL_KEYS, n=1, cutoff=0.85)
    if close:
        return True
    
    return False

def merge_adjacent_tokens(tokens: List[str]) -> List[str]:
    """Merge adjacent tokens that form valid symbols"""
    merged = []
    i = 0
    
    while i < len(tokens):
        t = tokens[i].strip()
        
        # measurement + abbreviation
        if re.match(r'^\d+(\s\d+/\d+|/\d+)?\"?$', t) and i + 1 < len(tokens):
            nxt = tokens[i + 1].strip()
            if re.match(r'^[A-Za-z]{1,5}$', nxt):
                merged.append(f'{t} {nxt}')
                i += 2
                continue
        
        # WC - 1
        if (re.match(r'^[A-Za-z]{1,5}$', t) and i + 2 < len(tokens) and
            tokens[i + 1].strip() in ['-', '–', '—'] and
            re.match(r'^\d+$', tokens[i + 2].strip())):
            merged.append(f'{t}-{tokens[i + 2].strip()}')
            i += 3
            continue
        
        # W C -> WC
        if (re.match(r'^[A-Za-z]$', t) and i + 1 < len(tokens) and
            re.match(r'^[A-Za-z]$', tokens[i + 1].strip())):
            merged.append(t + tokens[i + 1].strip())
            i += 2
            continue
        
        merged.append(t)
        i += 1
    
    return merged

def classify_and_count_symbols(lines: List[str], symbol_db: Dict = SYMBOL_DB, 
                               use_merge: bool = True) -> Tuple[Dict, Dict, Dict]:
    """
    Classify and count symbols from text lines
    
    Returns:
        counts: Dictionary of valid symbol counts
        validated_unknowns: Unknown but valid symbols
        rejected: Rejected text
    """
    counts = defaultdict(int)
    validated_unknowns = defaultdict(int)
    rejected = defaultdict(int)
    
    for line in lines:
        tokens = re.split(r'\s+', line)
        if use_merge:
            tokens = merge_adjacent_tokens(tokens)
        
        for token in tokens:
            token = token.strip().upper()
            token = normalize_symbol_key(token)
            
            if not token:
                continue
            
            if is_valid_symbol(token):
                counts[token] += 1
                base = token.split("-")[0].split('"')[0].strip()
                if base not in symbol_db:
                    validated_unknowns[token] += 1
            else:
                if len(token) > 1 and token.replace('"', '').replace('/', '').replace('-', '').isalpha():
                    rejected[token] += 1
    
    return dict(counts), dict(validated_unknowns), dict(rejected)

def clean_vlm_symbols(vlm_json: Dict[str, int]) -> Dict[str, int]:
    """Clean VLM output by filtering invalid symbols"""
    cleaned = {}
    for sym, count in vlm_json.items():
        sym = sym.strip().upper()
        sym = normalize_symbol_key(sym)
        if is_valid_symbol(sym):
            cleaned[sym] = int(count)
    return cleaned
