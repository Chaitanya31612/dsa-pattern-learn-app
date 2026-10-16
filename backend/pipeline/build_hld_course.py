"""Build the interactive HLD catalog from the journal; no AI regeneration."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from hld_diagrams import VISUALS
from hld_plain_language import CARDS
from hld_volume2 import volume2_modules, VOLUME2_SOURCES

APP_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = APP_ROOT.parent / 'swe-mastery-journal/HLD/21-volume-1-architect-course'


def sections(text: str) -> list[dict]:
    headings = list(re.finditer(r'^## (.+)$', text, re.M))
    result = []
    for i, heading in enumerate(headings):
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        result.append({'id': f'section-{i}', 'title': heading[1], 'content': text[heading.end():end].strip()})
    return result


def practice_blocks(text: str) -> list[dict]:
    headings = list(re.finditer(r'^## (P\d+[A-Z]?)\s*[—-]\s*(.+)$', text, re.M))
    result = []
    for i, heading in enumerate(headings):
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        body = text[heading.end():end].split('\n## ')[0].strip()
        result.append({'key': heading[1], 'title': heading[2], 'content': body})
    return result


def build(source: Path) -> dict:
    modules = []
    for meta in json.loads((source / 'course-index.json').read_text()):
        folder = source / meta['slug']
        answers = (folder / 'answers/01-solutions.md').read_text()
        solutions = {b['key']: b['content'] for b in practice_blocks(answers)}
        practices = practice_blocks((folder / '02-practice.md').read_text())
        if meta['slug'] == '16-final-assessment':
            first = practices.pop(0)
            rounds = list(re.finditer(r'\*\*Round ([ABC]): (.*?)\.\*\*', first['content']))
            for i, match in reversed(list(enumerate(rounds))):
                end = rounds[i + 1].start() if i + 1 < len(rounds) else len(first['content'])
                body = first['content'][match.end():end].split('\n\nRecord prior exposure.')[0].strip()
                practices.insert(0, {'key': 'P1' + match[1], 'title': match[2], 'content': body})
        exercises = []
        for p in practices:
            assert p['key'] in solutions, (meta['slug'], p['key'])
            exercises.append({'id': p['key'].lower(), 'title': p['title'],
                              'kind': 'repair' if p['key'] == 'P3' else 'transfer' if p['key'] == 'P2' else 'design',
                              'prompt': p['content'], 'solution': solutions[p['key']],
                              'minutes': 20 if p['key'] == 'P3' else 30 if p['key'] == 'P2' else 45})
        quiz_text = (folder / '03-checkpoint.md').read_text()
        quiz_matches = list(re.finditer(r'^(\d+)\. (.+)$', quiz_text, re.M))
        keys = {m[1]: (m[2], m[3].strip()) for m in re.finditer(r'^(\d+)\. \*\*([ABCD])\.\*\* (.+)$', answers, re.M)}
        questions = []
        for i, m in enumerate(quiz_matches):
            end = quiz_matches[i + 1].start() if i + 1 < len(quiz_matches) else len(quiz_text)
            options = re.findall(r'^   - [ABCD]\. (.+)$', quiz_text[m.end():end], re.M)
            letter, explanation = keys[m[1]]
            assert len(options) == 4
            questions.append({'id': f'q{m[1]}', 'prompt': m[2], 'options': options,
                              'correctIndex': 'ABCD'.index(letter), 'explanation': explanation})
        lesson = (folder / '01-lesson.md').read_text()
        lesson_sections = sections(lesson)
        plain = CARDS[meta['slug']]
        assert len(plain['rows']) == len(lesson_sections) - 1, meta['slug']
        for section, row in zip(lesson_sections, plain['rows']):
            section['quick'] = dict(zip(['title', 'explanation', 'example', 'tip'], row))
        lesson_sections[-1]['quick'] = {
            'title': 'Close the lesson. Explain it yourself.',
            'explanation': 'Try before you look back. Use the recap picture to tell the story. Then change one rule and explain what must change.',
            'example': 'Ask: what if two users act together, a machine crashes, or the data is old? Pick the risk that fits this module.',
            'tip': 'Recall → compare → repair → try later.',
        }
        recall = next((s['content'] for s in lesson_sections if 'Retrieve before practicing' in s['title']), meta['outcome'])
        examples_path = folder / 'worked-examples.md'
        modules.append({'id': meta['slug'], 'number': int(meta['slug'][:2]), 'title': plain['title'],
                        'track': 'volume-1', 'hours': meta['hours'], 'prerequisites': meta['prerequisite'], 'book': meta['book'],
                        'outcome': plain['rows'][0][1], 'sections': lesson_sections,
                        'examples': sections(examples_path.read_text()) if examples_path.exists() else [],
                        'exercises': exercises, 'questions': questions, 'recallPrompt': recall, 'visuals': VISUALS[meta['slug']]})
    assert len(modules) == 17 and sum(len(m['questions']) for m in modules) == 68
    materials = {name: (source / filename).read_text() for name, filename in
                 [('protocol', 'learning-protocol.md'), ('rubric', 'assessment-rubric.md'), ('sources', 'sources.md')]}
    modules.extend(volume2_modules())
    validate_modules(modules)
    materials['sources'] += VOLUME2_SOURCES
    materials['protocol'] = '# Use one learning loop across both volumes\n\nVolume 1 has 72 planned hours; Volume 2 adds 64. At 7 hours/week the full track is about 20 weeks, including review time within your weekly budget. This is a planning estimate, not a mastery guarantee. The original 12-week outline below applies to Volume 1 only.\n\nStart with a short lesson and diagram. Study an example, then solve a new prompt before opening its reference. Request AI feedback, compare, repair one gap, and return after a delay. Try the visual labs to test races, retries, overload, and search borders.\n\n' + materials['protocol']
    payload = {'schemaVersion': 1, 'title': 'HLD Architecture Lab', 'tracks': [
        {'id': 'volume-1', 'title': 'Volume 1 · Foundations', 'description': 'Build the framework and core mechanisms. Start here or test your existing knowledge.'},
        {'id': 'volume-2', 'title': 'Volume 2 · Deeper systems', 'description': 'Apply the framework to location, streams, scarce inventory, money, and ordered systems.'}], 'modules': modules, 'materials': materials}
    payload['contentVersion'] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:12]
    return payload


def validate_modules(modules):
    assert len({m['id'] for m in modules}) == len(modules), 'Duplicate module IDs'
    assert [m['number'] for m in modules] == list(range(len(modules))), 'Broken module order'
    for m in modules:
        assert len(m['visuals']) == 2 and {v['placement'] for v in m['visuals']} == {'overview', 'recap'}
        assert m['sections'] and all(s.get('quick') and s['content'] for s in m['sections']), m['id']
        assert len({e['id'] for e in m['exercises']}) == len(m['exercises'])
        assert all(e['prompt'] and e['solution'] for e in m['exercises'])
        assert len({q['id'] for q in m['questions']}) == len(m['questions'])
        assert all(len(q['options']) == 4 and 0 <= q['correctIndex'] < 4 and q['explanation'] for q in m['questions'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args()
    payload = build(args.source)
    for output in [APP_ROOT / 'frontend/public/hld-course.json', APP_ROOT / 'backend/pipeline/data/hld-course.json']:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n')
    print(f"Imported {len(payload['modules'])} modules, {sum(len(m['questions']) for m in payload['modules'])} questions, {sum(len(m['exercises']) for m in payload['modules'])} exercises.")


if __name__ == '__main__':
    main()
