"""Build only the synthetic AI learning source; never reads the work repository."""
import json
try:
    from .build_software_course import APP, build
except ImportError:  # direct script invocation
    from build_software_course import APP, build

if __name__ == '__main__':
    course = build(course_directory='ai-learnings')
    output = json.dumps(course,ensure_ascii=False,indent=2)+'\n'
    for path in [APP/'frontend/public/ai-course.json',APP/'backend/pipeline/data/ai-course.json']:
        path.write_text(output)
    print(f"Built {len(course['modules'])} AI chapters")
