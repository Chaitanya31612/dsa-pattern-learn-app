import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pipeline.reading_style import format_markdown,prose_beats

def test_splits_prose_without_altering_code_or_markdown_structure():
    code='```ruby\nmessage = "Prior to. Utilize."\n\nputs message\n```\n'
    source='# A heading\n\n'+('One short idea. Another idea. A final idea.\n\n')+code+'\n- Keep this list item intact.\n'
    output=format_markdown(source)
    assert code in output
    assert 'One short idea. Another idea.\n\nA final idea.' in output
    assert output.startswith('# A heading\n\n') and '- Keep this list item intact.' in output
    assert format_markdown(output)==output

def test_keeps_urls_inline_code_emphasis_versions_and_negation():
    source='Use `settings[:enabled] || true`. See [the version](https://example.com/v3.3.6). Ruby 3.3.6 does not change that rule. **Do not retry. Ask first.**'
    output=format_markdown(source)
    for fragment in ['`settings[:enabled] || true`','[the version](https://example.com/v3.3.6)','Ruby 3.3.6 does not change that rule.','**Do not retry. Ask first.**']:
        assert fragment in output

def test_changes_filler_words_only_in_prose():
    assert prose_beats('Utilize a queue in order to buffer work.')==['Use a queue to buffer work.']
    assert '`utilize()`' in format_markdown('Use `utilize()`.')
    assert format_markdown('    utilize()\n')=='    utilize()\n'

def test_dsa_subpattern_lessons_keep_their_own_explanations():
    import json
    source=Path(__file__).resolve().parents[1]/'pipeline/data/patterns.json'
    patterns=json.loads(source.read_text())
    parents={p['pattern_id']:p for p in patterns if not p.get('sub_pattern_id')}
    children=[p for p in patterns if p.get('sub_pattern_id')]
    assert len(parents)==17 and len(children)==71
    assert all(p['explanation']!=parents[p['pattern_id']]['explanation'] for p in children)
    assert len({p['explanation'] for p in children})==len(children)
