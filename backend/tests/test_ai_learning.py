import json
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ai_learning_api import ai_catalog, build_ai_learning_router
from software_api import catalog,build_software_router,context_for_chat,ChatRequest
from pipeline.build_software_course import build
APP=Path(__file__).resolve().parents[2]
def payload():
    return {'module_id':'ai-boundary','exercise_id':'repair','attempt':{'phases':{'predict':'The model proposes a filter','change':'Scope and validate in code','verify':'Not run','explain':'A schema is not permission'},'diagram':'','assisted':False}}
def client(reply='Short teaching reply',success=True):
    calls=[]
    class Fake:
        def analyze(self,content,prompt,json_mode=False):
            calls.append((content,prompt,json_mode))
            return SimpleNamespace(success=success,content=reply)
    app=FastAPI();app.include_router(build_ai_learning_router(lambda:Fake()));app.include_router(build_software_router(lambda:Fake()))
    return TestClient(app),calls

def test_ai_course_is_reproducible_complete_and_separate():
    built=build(course_directory='ai-learnings')
    assert built==ai_catalog()==json.loads((APP/'frontend/public/ai-course.json').read_text())
    assert build()==catalog() # shared builder did not change the existing course
    assert len(built['modules'])==56 and len(built['tracks'])==8
    assert {m['level'] for m in built['modules']}=={'beginner','intermediate','advanced'}
    assert sum(m['hours'] for m in built['modules'])==114.5
    assert set(built['labs'])=={'dispatch-desk','retrieval-lab'}
    assert not ({m['id'] for m in built['modules']}&{m['id'] for m in catalog()['modules']})
    for m in built['modules']:
        assert len(m['sections'])==4 and len(m['exercises'])==2 and len(m['questions'])>=3
        assert len(m['visuals'])>=2 and m['sources']
        assert all('/answers/' not in s['file'] for s in m['sections'])
        assert all(e['prompt']!=e['solution'] and e['solution'].strip() for e in m['exercises'])
    for track in built['tracks']:
        ms=[m for m in built['modules'] if m['track']==track['id']]
        assert sum(m['hours'] for m in ms)==track['hours']
        covers={q['covers'] for q in ms[-1]['questions'] if q.get('covers')}
        assert {m['id'] for m in ms[:-1]}<=covers
    assert len(built['modules'][-1]['questions'])==58
    serialized=json.dumps(built)
    for private in ['/home/chaitanya/Desktop/Work','healthmatters','KIPU','product-1-features']:
        assert private not in serialized

def test_teaching_context_uses_only_selected_lesson_or_lab():
    data={**payload(),'mode':'learn','section_id':'example','messages':[{'role':'user','content':'Explain this'}]}
    content,rules=context_for_chat(ChatRequest(**data),ai_catalog)
    assert 'do not invent executable APIs' in rules
    m=ai_catalog()['modules'][0]
    assert json.loads(content)['reference']==m['sections'][1]['content']
    data.update(module_id='ai-mcp-ruby-tool',file_path='app/mcp/read_shipment_facts_tool.rb')
    content,_=context_for_chat(ChatRequest(**data),ai_catalog)
    assert 'MCP::Tool' in content and '1.8.2' in content
    data['file_path']='../../Work/private.rb'
    with pytest.raises(HTTPException) as e:context_for_chat(ChatRequest(**data),ai_catalog)
    assert e.value.status_code==404

def test_practice_hides_reference_and_review_includes_it():
    data={**payload(),'mode':'practice','file_path':'README.md','messages':[{'role':'user','content':'Solve it'}]}
    content,rules=context_for_chat(ChatRequest(**data),ai_catalog)
    m=ai_catalog()['modules'][0]
    assert json.loads(content)['reference']==m['exercises'][0]['prompt']
    assert 'Do not reveal the answer' in rules
    data['mode']='review'
    content,_=context_for_chat(ChatRequest(**data),ai_catalog)
    assert json.loads(content)['reference']['reference']==m['exercises'][0]['solution']

def test_course_routes_cannot_mix_module_ids():
    c,calls=client();data=payload();data['module_id']='ruby-values'
    assert c.post('/api/ai-course/evaluate',json=data).status_code==404
    assert c.post('/api/software/evaluate',json=payload()).status_code==404
    assert not calls
    data={**payload(),'mode':'learn','messages':[{'role':'user','content':'Explain'}]}
    assert c.post('/api/ai/ai-course-chat',json=data).json()['reply']=='Short teaching reply'

def test_ai_review_requires_evidence_and_validates_json_scores():
    report={'summary':'Partial design','next_exercise':'Run the failure case','dimensions':[{'id':id,'score':1,'evidence':'Not run' if id=='verify' else 'The submitted boundary','feedback':'Add one counterexample'} for id in ['predict','change','verify','explain']]}
    c,calls=client(json.dumps(report))
    assert c.post('/api/ai-course/evaluate',json=payload()).json()['source']=='ai'
    assert calls[0][2] is True
    assert 'proposed tests without observed results are at most 1' in calls[0][1]
    assert json.loads(calls[0][0])['reference']==ai_catalog()['modules'][0]['exercises'][0]['solution']
    report['dimensions'][0]['score']=True
    c,_=client(json.dumps(report));assert c.post('/api/ai-course/evaluate',json=payload()).status_code==502
    c,_=client(success=False);assert c.post('/api/ai-course/evaluate',json=payload()).status_code==503

def test_unknown_source_directory_rejected():
    with pytest.raises(ValueError,match='Unknown course directory'):build(course_directory='../Work')
