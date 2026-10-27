"""AI course coach: only published synthetic lessons enter provider context."""
import json
from functools import lru_cache
from pathlib import Path
from software_api import build_software_router

@lru_cache(maxsize=1)
def ai_catalog():
    return json.loads((Path(__file__).parent/'pipeline/data/ai-course.json').read_text())

def build_ai_learning_router(get_analyzer):
    return build_software_router(get_analyzer,course_loader=ai_catalog,namespace='ai-course')
