# Auto-generated lightweight glyphs data forwarder
import os
import json

def get_glyphs_data():
    try:
        from utils import get_glyphs_data as _get_data
        return _get_data()
    except Exception:
        return {}
