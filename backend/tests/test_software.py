import json
import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from software_api import build_software_router, ChatRequest, context_for_chat, catalog
from pipeline.build_software_course import build


def client(reply='A short explanation', success=True):
    calls=[]
    class Fake:
        def analyze(self, content, prompt, json_mode=False):
            calls.append({'content':content,'prompt':prompt,'json_mode':json_mode})
            return SimpleNamespace(success=success,content=reply)
    app=FastAPI();app.include_router(build_software_router(lambda:Fake()))
    return TestClient(app),calls


def payload():
    return {'module_id':'ruby-values','exercise_id':'repair','attempt':{'phases':{'predict':'False is lost','change':'Use fetch','verify':'Not run','explain':'A false value is a valid setting'},'diagram':'','assisted':False}}


def test_catalog_matches_both_runtime_copies_and_has_separate_answers():
    built=build()
    assert len(built['modules']) >= 130
    assert len({m['id'] for m in built['modules']}) == len(built['modules'])
    assert {t['id'] for t in built['tracks']} == {'spring','ruby','git','frontend','ux','cloud','ops','events'}
    assert all(len(m['visuals']) >= 2 and len(m['exercises']) == 2 and len(m['questions']) >= 2 for m in built['modules'])
    assert {'ruby-values','spring-transactions','git-staging','frontend-vue'}.issubset({m['id'] for m in built['modules']})
    assert set(built['labs']) == {'rails-kafka','aws-rails','redis','vue-workspace'}
    for track in built['tracks']:
        modules = [m for m in built['modules'] if m['track'] == track['id']]
        levels = [m['level'] for m in modules]
        assert levels == sorted(levels, key=lambda level: 0 if level == 'beginner' else 1)
        assert sum(m['hours'] for m in modules) == track['hours']
    for track,final in [('ops','ops-toolkit-capstone'),('cloud','cloud-architecture'),('events','events-replay-capstone')]:
        module = next(m for m in built['modules'] if m['id'] == final)
        assert {q.get('covers') for q in module['questions'] if q.get('covers')} == {m['id'] for m in built['modules'] if m['track']==track and m['id']!=final}
    assert built==catalog()
    frontend=Path(__file__).resolve().parents[2]/'frontend/public/software-course.json'
    assert json.loads(frontend.read_text())==built
    for m in built['modules']:
        assert all('/answers/' not in s['file'] for s in m['sections'])
        assert all(e['solution'].strip() and e['solution'] != e['prompt'] for e in m['exercises'])


def test_practice_context_does_not_include_answer_and_learning_uses_only_selected_step():
    data=payload();data.update(mode='practice',messages=[{'role':'user','content':'Give the answer'}])
    content,rules=context_for_chat(ChatRequest(**data))
    assert 'One valid repair' not in content
    assert 'Do not reveal the answer' in rules
    data.update(mode='learn',section_id='example')
    content,_=context_for_chat(ChatRequest(**data))
    assert 'buckets = Hash.new' in content
    assert 'One valid repair' not in content


def test_review_context_can_compare_reference():
    data=payload();data.update(mode='review',messages=[{'role':'user','content':'Compare my attempt'}])
    content,_=context_for_chat(ChatRequest(**data))
    assert 'One valid repair' in content


def test_unknown_module_and_bad_field_rejected_without_provider():
    c,calls=client()
    data=payload();data['module_id']='absent'
    assert c.post('/api/software/evaluate',json=data).status_code==404
    data=payload();data['attempt']['phases']['execute_shell']='rm -rf /'
    assert c.post('/api/software/evaluate',json=data).status_code==422
    assert not calls


def test_provider_failure_is_honest_and_does_not_fabricate_score():
    c,_=client(success=False)
    response=c.post('/api/software/evaluate',json=payload())
    assert response.status_code==503 and 'saved attempt' in response.json()['detail']


def test_evaluation_uses_reference_and_validates_all_dimensions():
    report={'summary':'Partial evidence','next_exercise':'Run the false-setting test','dimensions':[
      {'id':id,'score':1,'evidence':'Not run' if id=='verify' else 'Specific submitted work','feedback':'Test both values'} for id in ['predict','change','verify','explain']]}
    c,calls=client(json.dumps(report))
    response=c.post('/api/software/evaluate',json=payload())
    assert response.status_code==200 and response.json()['source']=='ai'
    assert calls[0]['json_mode'] is True
    assert 'One valid repair' in calls[0]['content']
    assert 'proposed tests without observed results are at most 1' in calls[0]['prompt']
    report['dimensions'][3]['id']='verify'
    c,_=client(json.dumps(report))
    assert c.post('/api/software/evaluate',json=payload()).status_code==502


def test_oversized_chat_rejected():
    c,calls=client()
    data=payload();data.update(mode='learn',messages=[{'role':'user','content':'x'*5000}]*3)
    assert c.post('/api/ai/software-chat',json=data).status_code==422
    assert not calls


def test_lab_chat_is_selected_versioned_file_and_cannot_escape_catalog():
    import pytest
    from fastapi import HTTPException
    data = {'module_id':'events-rails-lab','mode':'learn','file_path':'app/services/reporting_consumer.rb','messages':[{'role':'user','content':'Explain the next offset'}]}
    content,rules = context_for_chat(ChatRequest(**data))
    assert 'consumer.store_offset(message)' in content and '7.2.2.2' in content
    assert 'LOCAL CLIENT' in content
    assert 'One valid repair' not in content
    data['file_path']='../../../../Work/private.rb'
    with pytest.raises(HTTPException) as error:
        context_for_chat(ChatRequest(**data))
    assert error.value.status_code==404
    # A lab filename supplied during practice cannot leak the worked example.
    data.update(file_path='app/services/reporting_consumer.rb',mode='practice',exercise_id='repair')
    content,_=context_for_chat(ChatRequest(**data))
    assert 'consumer.store_offset(message)' not in content


def test_builder_rejects_lab_paths_outside_journal(tmp_path):
    import pytest
    (tmp_path/'software-learnings').mkdir()
    (tmp_path/'software-learnings/course-index.json').write_text('{"modules":[],"tracks":[]}')
    (tmp_path/'software-learnings/labs.json').write_text('[{"directory":"../private","files":[]}]')
    with pytest.raises(ValueError,match='Lab path leaves journal'):
        build(tmp_path)


def test_local_provider_without_json_mode_still_validates_feedback():
    report={'summary':'Evidence reviewed','next_exercise':'Run one failure case','dimensions':[{'id':id,'score':1,'evidence':'Proposed check','feedback':'Record actual results'} for id in ['predict','change','verify','explain']]}
    class Local:
        def analyze(self, content, prompt):
            return SimpleNamespace(success=True,content=json.dumps(report))
    app=FastAPI();app.include_router(build_software_router(lambda:Local()))
    assert TestClient(app).post('/api/software/evaluate',json=payload()).status_code==200
