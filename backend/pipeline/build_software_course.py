"""Bundle editable journal lessons. Never reads or executes a work repository."""
import json
from pathlib import Path

APP = Path(__file__).resolve().parents[2]
JOURNAL = APP.parent / 'swe-mastery-journal'


def build(journal=JOURNAL, course_directory="software-learnings"):
    if course_directory not in ("software-learnings", "ai-learnings"):
        raise ValueError("Unknown course directory")
    source = journal / course_directory
    manifest = json.loads((source / 'course-index.json').read_text())
    labs = {}
    lab_manifest = json.loads((source / 'labs.json').read_text())
    for item in lab_manifest:
        folder = (journal / item['directory']).resolve()
        if not folder.is_relative_to(journal.resolve()):
            raise ValueError('Lab path leaves journal')
        if item['id'] in labs:
            raise ValueError('Duplicate lab ID')
        files = []
        for relative in item['files']:
            path = (folder / relative).resolve()
            if not path.is_relative_to(folder) or path.name.startswith('.env') or path.stat().st_size > 60000:
                raise ValueError('Invalid lab file')
            language = {'.rb':'ruby','.py':'python','.json':'json','.yml':'yaml','.yaml':'yaml','.ts':'typescript','.vue':'vue','.md':'markdown'}.get(path.suffix, 'text')
            files.append({'path': relative, 'language': language, 'content': path.read_text()})
        guide = next(f['content'] for f in files if f['path'] == item.get('guide', 'README.md'))
        labs[item['id']] = {'id': item['id'], 'title': item['title'], 'version': item['version'], 'journalPath': item['directory'], 'files': files, 'guide': guide}
    modules = []
    seen = set()
    for entry in manifest['modules']:
        folder = (journal / entry['directory']).resolve()
        if not folder.is_relative_to(journal.resolve()):
            raise ValueError('Module path leaves journal')
        module = json.loads((folder / 'module.json').read_text())
        if module['id'] != entry['id'] or module['id'] in seen:
            raise ValueError('Duplicate or mismatched module ID')
        if module['track'] not in {t['id'] for t in manifest['tracks']}:
            raise ValueError('Unknown module track')
        seen.add(module['id'])
        if module.get('level') not in (('beginner', 'intermediate', 'advanced') if course_directory=='ai-learnings' else ('beginner', 'intermediate')):
            raise ValueError('Unknown learning level')
        if module.get('lab') and module['lab'] not in labs:
            raise ValueError('Missing lab')

        def read(relative):
            path = (folder / relative).resolve()
            if not path.is_relative_to(folder):
                raise ValueError('Content path leaves module')
            return path.read_text()

        module['sections'] = [{**s, 'content': read(s['file'])} for s in module['sections']]
        module['exercises'] = [{**e, 'prompt': read(e['file']), 'solution': read(e['solutionFile'])} for e in module['exercises']]
        questions = json.loads(read('quiz.json'))
        keys = json.loads(read('answers/quiz.json'))
        module['questions'] = [{**q, **keys[q['id']]} for q in questions]
        if len({q['id'] for q in questions}) != len(questions):
            raise ValueError('Duplicate quiz ID')
        for q in module['questions']:
            if not 0 <= q['correctIndex'] < len(q['options']):
                raise ValueError('Quiz key outside options')
        readings = []
        for relative in module['reading']:
            path = (journal / relative).resolve()
            if not path.is_relative_to(journal.resolve()) or 'answers' in str(path):
                raise ValueError('Invalid deeper reading')
            readings.append({'title': path.stem.replace('-', ' '), 'path': relative, 'content': path.read_text()})
        module['reading'] = readings
        module['journalPath'] = entry['directory']
        modules.append(module)
    for module in modules:
        if module['prerequisite'] and module['prerequisite'] not in seen:
            raise ValueError('Missing prerequisite')
    for track in manifest['tracks']:
        ordered = [m for m in modules if m['track'] == track['id']]
        if [m['sequence'] for m in ordered] != list(range(1, len(ordered) + 1)):
            raise ValueError('Invalid track sequence')
        reached = set()
        for module in ordered:
            if module['prerequisite'] and module['prerequisite'] not in reached:
                raise ValueError('Prerequisite must precede module in track')
            reached.add(module['id'])
    return {**manifest, 'modules': modules, 'labs': labs,
            'guide': (source / 'README.md').read_text(),
            'versions': (source / 'versions-and-sources.md').read_text()}


if __name__ == '__main__':
    course = build()
    text = json.dumps(course, ensure_ascii=False, indent=2) + '\n'
    for path in [APP / 'frontend/public/software-course.json', APP / 'backend/pipeline/data/software-course.json']:
        path.write_text(text)
    print(f"Built {len(course['modules'])} modules across {len(course['tracks'])} tracks")
