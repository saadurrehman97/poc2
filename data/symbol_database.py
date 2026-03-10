"""
Symbol Database and Mappings for Plumbing Engineering Drawings
"""

# Complete symbol database
SYMBOL_DB = {

    # PLUMBING FIXTURE SCHEDULE

    "AC-1":"Air Conditioner",
    "DN-1":"Downspout Nozzle",
    "EWC-1":"BI-Level Electric Water Cooler",
    "EWC-2":"Single-Level Electric Water Cooler",
    "EWS-1":"Eye/Face Wash & Drench Shower",
    "FCO-1":"Floor Cleanout",
    "FD-1":"DUCO Cast Iron Floor Drain",
    "FD-2":"Medium Duty DUCO Cast Iron Floor Drain",
    "GWH-1":"Gas Water Heater",
    "HB-1":"Hose Bibb",
    "MS-1":"Mop Sink",
    "RP-1":"Recirculation Pump",
    "S-1":"Standard Drop-In Sink",
    "S-2":"Sink with Hair Interceptor",
    "SS-1":"Single Compartment Service Sink-21",
    "SS-2":"Heavy-Duty Service Sink-48",
    "UR-1":"Urinal",
    "WC-1":"Standard Water Closet",
    "WC-2":"Handicap Water Closet",
    "WCO-1":"Wall Cleanout",
    "WF-1":"ADA Multi-Station Lavatory",	
    "WF-2":"Standard Circular Wash Fountain",
    "WH-1":"Standard Wall Hydrant",
    "WH-2":"Non-Freeze Wall Hydrant",
    "HR-1":"Compressed Air Hose Reel",
    "LAV":"Lavatory",


}

# Noise words to filter out
NOISE_WORDS = {
    "A", "B", "C", "D", "E", "F", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "T", "U", "X", "Y", "Z",
    "THE", "AND", "OR", "OF", "TO", "IN", "FOR", "ON", "AT", "BY", "WITH", "FROM", "AS", "IS", "ARE", "WAS", "BE",
    "AN", "IT", "ALL", "ANY", "THIS", "THAT", "NOT", "BUT", "CAN", "HAS", "HAD", "HAVE", "BEEN", "WILL", "SHALL",
    "ROOM", "AREA", "SPACE", "FLOOR", "LEVEL", "ZONE", "WOMEN", "MEN", "TOOL", "CRIB", "OFFICE", "RESTROOM",
    "KITCHEN", "LOBBY", "CORRIDOR", "PLAN", "SHEET", "DRAWING", "DETAIL", "SECTION", "ELEVATION", "VIEW",
    "NORTH", "SOUTH", "EAST", "WEST", "SCALE", "DATE", "REVISION", "NOTES", "TITLE", "BLOCK", "PROJECT",
    "LEGEND", "PAGE", "SEE", "REFER", "NOTE", "TYPICAL", "VERIFY", "COORDINATE", "UNLESS", "NOTED", "OTHERWISE",
    "FIELD", "PRIOR", "SHOWN", "USED", "MUST", "DOES", "ALLOW", "WHERE", "VIA", "PER", "EACH", "OTHER", "EXACT",
    "UP", "DOWN", "ABOVE", "BELOW", "ALONG", "ROUTE", "MOUNT", "INSTALL", "WORK", "STOP", "SHUT", "OFF", "OPEN", "CLOSE",
    "PIPE", "PIPES", "PIPING", "PIPED", "PIPED.", "LINE", "LINES", "LINING", "LINED",
    "MAIN", "MAINS", "WALL", "WALLS", "ROOF", "ROOFS", "BASE", "BASES", "PANEL", "PANELS",
    "CAST", "CASTS", "IRON", "IRONS", "PVC", "PVCs", "COPPER", "COPPERS", "STEEL", "STEELS",
    "DROPS", "DROP", "DROPPING", "DROPPED", "RISER", "RISERS", "TRUSS", "TRUSSES",
    "DIRT", "DIRTS", "UNION", "UNIONS", "DRAIN", "DRAINS", "DRAINING", "DRAINED",
    "VENT", "VENTS", "VENTING", "VENTED", "SEWER", "SEWERS",
    "FLOW", "FLOWS", "FULL", "AIR", "WATER", "GAS", "HOT", "COLD", "FIRE",
    "HOSE", "REEL", "HAND", "QUICK", "POWER", "DRYER", "LOSS", "ZERO", "PRIME",
    "CODE", "CODES", "STATE", "LOCAL", "ADA", "OSFC", "OHIO", "CFM", "GPM", "PSI", "RATED", "DRAFT",
    "JOB", "GROUP", "OLD", "OAK", "OH", "AM", "PM", "ERA", "FAX",
    "PLANS", "AREAS", "APART", "CNC", "GLA", "PYLE", "RNS", "AKRON", "BID", "TRUE",
    "VALVE", "VALVES", "VALVING", "VALVED", "LEG", "CORES",
    "REE", "NO", "TECH", "FALSE", "SIGN", "APPROVAL", "NEW", "HIGH",
    "OWNER", "OWNER.", "SERVE", "ROAD", "FIRST", "STAIR",
    "PREP", "ELEC.", "ELEC", "FUCHS", "CHASE", "LAB", "TABLE", "TAP", "SET", "FLEX",
    "BAKER", "MASON", "CONCRETE", "CONC.", "CONC", "REBAR", "REINFORCING",
    "STL.", "STL", "WELD", "WELDED", "SHEET", "METAL",
    "SUPPLY", "SUPPLIES", "DISCHARGE", "DISCHARGES", "DISCHARGING", "DISCHARGED",
    "RETURN", "RETURNS", "RETURNING", "RETURNED",
    "EXHAUST", "EXHAUSTED", "EXHAUSTING", "EXHAUSTS",
    "SEAL:", "SEAL", "SEALS", "SEALING", "SEALED",
    "DRAWN", "CHECKED", "APPROVED", "DESIGNED", "BY", "OF", "REVISIONS", "REVISION", "DESCRIPTION",
    "REVIEWED", "REVIEW", "REVIEWER", "REVIEWED BY",
}

# DFINE class to symbol mapping - COMPREHENSIVE (covers all 36 DFINE classes)
DFINE_TO_SYMBOL_MAP = {
    # Meters and measuring devices
    "water_meter": "Water Meter",
    "thermometer": "Thermometer",
    "pressure_guage": "Pressure Guage",
    "meter": "Meter",

    # Fixtures and drains
    "cleanout": "Cleanout",

    # Valves
    "check_valve": "Check valve",
    "gate_valve": "Gate valve",
    "ball_valve": "Ball valve",
    "pressure_regulating_valve": "Pressure Regulating Valve",
    "pressure_relief_valve": "Pressure Relief Valve",
    "drip_leg_valve": "Drip Leg Valve",
    "two_way_modulating_valve": "Two Way Modulating Valve",
    "gas_cock": "Gas Cock",

    # Pipe fittings and elbows
    "elbow": "Elbow",
    "riser_down_elbow": "Riser Down Elbow",
    "riser_up_elbow": "Riser Up Elbow",
    "screwed_union": "Screwed Union",
    "pipe_endcap": "Pipe Endcap",
    "pipe_connection": "Pipe Connection",

    # Hose and bibs
    "hose_bibb": "Hose Bibb",
    "wall_hydrant": "Wall Hydrant",

    # Connection points
    "point_of_connection": "Point of Connection",
    "connect_to_existing": "Connect to Existing",
    "branch_bottom_connection": "Branch Bottom Connection",
    "branch_side_connection": "Branch Side Connection",
    "branch_top_connection": "Branch Top Connection",

    # Pipe routing and support
    "riser_up_in_piping": "Riser Up in Piping",
    "rise_or_drop_in_piping": "Rise or Drop in Piping",
    "drop_in_piping": "Drop in Piping",
    "pipe_anchor": "Pipe Anchor",
    "pipe_guide": "Pipe Guide",
    "piping_break": "Piping Break",

    # Flow and equipment
    "direction_of_flow": "Direction of Flow",
    "strainer": "Strainer",
    "aquastat": "Aquastat",

    # Sprinklers
    "concealed_type_sprinkler_head": "Concealed Type Sprinkler Head",
}

# DFINE class names (36 classes - from classes.txt annotation)
DFINE_CLASS_NAMES = {
    0: "aquastat",
    1: "ball_valve",
    2: "branch_bottom_connection",
    3: "branch_side_connection",
    4: "branch_top_connection",
    5: "check_valve",
    6: "cleanout",
    7: "concealed_type_sprinkler_head",
    8: "connect_to_existing",
    9: "direction_of_flow",
    10: "drip_leg_valve",
    11: "drop_in_piping",
    12: "elbow",
    13: "gas_cock",
    14: "gate_valve",
    15: "hose_bibb",
    16: "meter",
    17: "pipe_anchor",
    18: "pipe_connection",
    19: "pipe_endcap",
    20: "pipe_guide",
    21: "piping_break",
    22: "point_of_connection",
    23: "pressure_guage",
    24: "pressure_regulating_valve",
    25: "pressure_relief_valve",
    26: "rise_or_drop_in_piping",
    27: "riser_down_elbow",
    28: "riser_up_elbow",
    29: "riser_up_in_piping",
    30: "screwed_union",
    31: "strainer",
    32: "thermometer",
    33: "two_way_modulating_valve",
    34: "wall_hydrant",
    35: "water_meter"
}

# Normalization mappings
NORMALIZE_MAP = {
    'WC,': 'WC', 'W C': 'WC', 'V C': 'VC',
    '3/4IN': '3/4"', '1/2IN': '1/2"', 'IN': '"',
}

# Get symbol keys
SYMBOL_KEYS = set(SYMBOL_DB.keys())
