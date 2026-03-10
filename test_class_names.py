# test_class_names.py
import sys
sys.path.insert(0, '/workspace/D-FINE-master')
from src.core import YAMLConfig

config_path = '/workspace/D-FINE-master/configs/dfine/custom/dfine_hgnetv2_l_custom.yml'
cfg = YAMLConfig(config_path)

# Try different ways to access names
print("=== Checking for class names ===")

if hasattr(cfg, 'yaml_cfg'):
    if 'names' in cfg.yaml_cfg:
        print("Found 'names' in yaml_cfg:", cfg.yaml_cfg['names'])
    if 'class_names' in cfg.yaml_cfg:
        print("Found 'class_names' in yaml_cfg:", cfg.yaml_cfg['class_names'])

if hasattr(cfg, 'class_names'):
    print("Found cfg.class_names:", cfg.class_names)

print("\nTotal classes found:", len(cfg.yaml_cfg.get('names', {})))