"""
Mock Interview API (V2)
=======================

This module provides runtime endpoints used by the frontend interview workspace.

Why this exists:
- V1 was fully offline and deterministic.
- V2 adds an AI interviewer that can respond to clarifications/hint requests.
- We still keep graceful fallback behavior when provider calls fail.

Primary endpoint:
- POST /api/mock-interview/respond

Data flow (high level):
1) Frontend sends session context + recent chat + problem metadata.
2) Backend merges that payload with db.json problem info (if available).
3) Backend builds a constrained interviewer prompt and calls Groq smart model.
4) Backend sanitizes potentially leaky responses (no full code in interview mode).
5) Frontend receives reply + intent + safety flags.
"""

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Literal, Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ai.base import AIProvider
from ai.factory import AIAnalyzerFactory

# Load .env once at import time so provider credentials are available.
load_dotenv()


# ---------------------------------------------------------------------------
# Request/response contracts
# ---------------------------------------------------------------------------


class ChatMessagePayload(BaseModel):
    """
    A single chat message in the interview transcript.

    Example:
      {"role": "user", "content": "Need a hint, I am stuck.", "ts": "..."}
    """

    role: Literal['user', 'assistant']
    content: str = Field(min_length=1, max_length=4000)
    ts: Optional[str] = None


class ProblemContextPayload(BaseModel):
    """
    Problem context optionally supplied by frontend.

    We accept these fields so frontend can enrich backend context immediately,
    even when backend db.json is stale or missing some data.
    """

    title: Optional[str] = None
    difficulty: Optional[str] = None
    pattern_name: Optional[str] = None
    pattern_hint: Optional[str] = None
    key_insight: Optional[str] = None
    description_html: Optional[str] = None
    description_text: Optional[str] = None
    topic_tags: list[str] = Field(default_factory=list)


class DebriefProblemAttemptPayload(BaseModel):
    """
    Per-problem attempt context for AI debrief generation.

    Example:
      {
        "slug": "two-sum",
        "title": "Two Sum",
        "thoughts": ["Use hash map in one pass"],
        "code": "class Solution { ... }",
        "chat": [{"role":"user","content":"Need hint","ts":"..."}],
        "hint_count": 1,
        "submitted": true
      }
    """

    slug: str = Field(min_length=1, max_length=200)
    title: Optional[str] = None
    difficulty: Optional[str] = None
    pattern_name: Optional[str] = None
    description_text: Optional[str] = None
    stored_note: Optional[str] = None
    thoughts: list[str] = Field(default_factory=list)
    code: str = ''
    chat: list[ChatMessagePayload] = Field(default_factory=list)
    hint_count: int = Field(default=0, ge=0, le=20)
    submitted: bool = False
    heuristic_score: Optional[int] = Field(default=None, ge=0, le=100)
    heuristic_reasoning: list[str] = Field(default_factory=list)


class DebriefRecommendationCandidatePayload(BaseModel):
    """
    Candidate recommendation item frontend provides so AI stays grounded in
    known local problems and avoids inventing unseen slugs.
    """

    slug: str = Field(min_length=1, max_length=200)
    title: Optional[str] = None
    difficulty: Optional[str] = None
    pattern_name: Optional[str] = None


class DebriefContextPayload(BaseModel):
    """
    Session-level context used only in debrief mode.
    """

    session_status: Literal['completed', 'abandoned']
    total_questions: int = Field(ge=1, le=20)
    total_time_minutes: int = Field(ge=1, le=240)
    remaining_time_sec: int = Field(ge=0)
    language: str = Field(default='java')
    total_score_heuristic: Optional[int] = Field(default=None, ge=0, le=100)
    attempts: list[DebriefProblemAttemptPayload] = Field(default_factory=list)
    candidate_recommendations: list[DebriefRecommendationCandidatePayload] = Field(default_factory=list)


class MockInterviewRespondRequest(BaseModel):
    """
    Payload used by /api/mock-interview/respond.

    Example (trimmed):
      {
        "session_id": "mi_abc123",
        "problem_slug": "two-sum",
        "hint_level": 1,
        "mode": "interview",
        "messages": [...]
      }
    """

    session_id: str = Field(min_length=1, max_length=200)
    problem_slug: str = Field(min_length=1, max_length=200)
    messages: list[ChatMessagePayload] = Field(default_factory=list)
    hint_level: int = Field(default=0, ge=0, le=5)
    mode: Literal['interview', 'debrief'] = 'interview'
    problem: Optional[ProblemContextPayload] = None
    debrief_context: Optional[DebriefContextPayload] = None


class DebriefPerProblemResult(BaseModel):
    """AI-generated per-problem evaluation for final report."""

    score: int = Field(ge=0, le=100)
    reasoning: list[str] = Field(default_factory=list)


class DebriefReportPayload(BaseModel):
    """
    Structured AI debrief consumed by frontend.

    Field names follow snake_case because request/response payloads are JSON and
    frontend maps these into its camelCase session model.
    """

    total_score: int = Field(ge=0, le=100)
    per_problem: Dict[str, DebriefPerProblemResult] = Field(default_factory=dict)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    recommended_problems: list[str] = Field(default_factory=list)


class MockInterviewRespondResponse(BaseModel):
    """Normalized response contract returned to frontend."""

    reply: str
    intent: Literal['clarification', 'hint', 'reinforcement', 'guidance']
    safety_flags: list[str]
    provider: str
    model: str
    debrief: Optional[DebriefReportPayload] = None


# ---------------------------------------------------------------------------
# Loading/caching helpers
# ---------------------------------------------------------------------------


def _db_path() -> Path:
    """Return canonical db.json path used by this service."""
    return Path(__file__).resolve().parent / 'pipeline' / 'data' / 'db.json'


@lru_cache(maxsize=1)
def load_db() -> Dict[str, Any]:
    """
    Load db.json once and cache it.

    Why cache:
    - Avoid disk IO on every chat turn.
    - db.json is static during a local dev session in most cases.

    If file is missing/corrupt, return an empty dictionary so endpoint still works
    with frontend-supplied context.
    """

    path = _db_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


@lru_cache(maxsize=1)
def get_analyzer():
    """
    Resolve AI provider analyzer once.

    Current policy:
    - V2 default is Groq smart model (`DEFAULT_AI_MODEL`, default="smart").
    - If Groq creation fails, fall back to factory default chain.

    Example env:
      DEFAULT_AI_PROVIDER=groq
      DEFAULT_AI_MODEL=smart
    """

    groq_model = os.getenv('DEFAULT_AI_MODEL', 'smart').strip() or 'smart'
    try:
        return AIAnalyzerFactory.create(AIProvider.GROQ, model=groq_model)
    except Exception:
        return AIAnalyzerFactory.create_default()


# ---------------------------------------------------------------------------
# Interview behavior helpers
# ---------------------------------------------------------------------------


def infer_intent(last_user_message: str, hint_level: int) -> Literal['clarification', 'hint', 'reinforcement', 'guidance']:
    """
    Classify user turn into a coarse intent.

    This is lightweight and regex-based by design.

    Examples:
    - "Can you clarify constraints?" -> clarification
    - "Need hint" -> hint
    - "Am I on right track?" -> reinforcement
    - Everything else -> guidance
    """

    lower = last_user_message.lower()
    if re.search(r'clarify|constraint|assume|edge|what if|\?', lower):
        return 'clarification'
    if re.search(r'hint|stuck|nudge|help', lower) or hint_level > 0:
        return 'hint'
    if re.search(r'right|correct|direction|does this make sense', lower):
        return 'reinforcement'
    return 'guidance'


def sanitize_reply(reply: str, mode: str) -> tuple[str, list[str]]:
    """
    Prevent obvious solution leakage in interview mode.

    Guardrail examples:
    - Blocks fenced code blocks (``` ... ```)
    - Blocks typical full-solution signatures (`class Solution`, `public static`)

    If flagged, we replace output with a strict non-leaky nudge.
    """

    safety_flags: list[str] = []
    if mode == 'interview':
        if '```' in reply or re.search(r'\bclass\s+Solution\b|\bpublic\s+static\b|\bdef\s+\w+\(', reply):
            safety_flags.append('possible_solution_leak')
            return (
                'I can help with direction, but I will not provide full code during interview mode. '
                'Share your current approach and I will nudge the next step.',
                safety_flags,
            )
    return reply.strip(), safety_flags


def build_prompt(mode: str, intent: str, hint_level: int) -> str:
    """
    Build system prompt used for model call.

    We keep this concise to reduce noise and enforce style constraints.
    """

    if mode == 'debrief':
        return (
            'You are a senior DSA interviewer producing a personalized debrief from an actual session.\n'
            'Return ONLY valid JSON (no markdown fences, no prose outside JSON).\n'
            'Required JSON schema:\n'
            '{\n'
            '  "total_score": integer 0..100,\n'
            '  "per_problem": {\n'
            '    "<slug>": {\n'
            '      "score": integer 0..100,\n'
            '      "reasoning": ["specific bullet referencing observed code/thought/chat"]\n'
            '    }\n'
            '  },\n'
            '  "strengths": ["specific session strengths"],\n'
            '  "weaknesses": ["specific gaps from this session"],\n'
            '  "next_steps": ["actionable practice step tied to observed behavior"],\n'
            '  "recommended_problems": ["slug"]\n'
            '}\n'
            'Rules:\n'
            '- Personalize using attempt code, thoughts, stored notes, and user questions in chat.\n'
            '- Mention concrete evidence (e.g., "you asked about edge cases", "your code lacked null guard").\n'
            '- If candidate_recommendations are provided, choose recommended_problems only from those slugs.\n'
            '- Keep strengths/weaknesses/next_steps concise (3-6 items each).\n'
            '- Do not invent unseen problems or constraints.'
        )

    return (
        'You are a technical interviewer in a live coding interview.\n'
        'Rules:\n'
        '- Keep responses concise (2-5 sentences).\n'
        '- Never provide full solution code or full final algorithm.\n'
        '- Ask one probing question or give one focused nudge.\n'
        '- If user asks for hints, use progressive hinting based on hint level.\n'
        '- Stay grounded in provided problem and pattern context.\n'
        f'- Current intent type: {intent}.\n'
        f'- Current hint level: {hint_level}.\n'
    )


def make_description_excerpt(description_text: str, max_chars: int = 2400) -> str:
    """
    Keep prompt context bounded to avoid token bloat.

    Example:
    - Input: very long LeetCode prompt + examples + constraints
    - Output: first ~2400 chars, normalized whitespace
    """

    compact = re.sub(r'\s+', ' ', description_text or '').strip()
    if len(compact) <= max_chars:
        return compact
    return compact[:max_chars].rstrip() + ' ...'


def make_code_excerpt(code_text: str, max_chars: int = 2800) -> str:
    """
    Keep user code bounded in prompt context.

    Why:
    - Prevent token blow-up in long sessions.
    - Preserve enough detail for specific feedback.
    """

    if not code_text:
        return ''
    compact = code_text.strip()
    if len(compact) <= max_chars:
        return compact
    return compact[:max_chars].rstrip() + '\n// ... truncated for context'


def normalize_debrief_context(payload: MockInterviewRespondRequest) -> Dict[str, Any]:
    """
    Convert debrief_context payload into model-friendly compact JSON.

    Examples of retained personalized signals:
    - stored_note + thoughts
    - user chat questions and hint asks
    - submitted flag + hint_count
    - actual code excerpt
    """

    if not payload.debrief_context:
        return {}

    context = payload.debrief_context
    attempts: list[Dict[str, Any]] = []
    for attempt in context.attempts:
        recent_chat = attempt.chat[-12:]
        attempts.append(
            {
                'slug': attempt.slug,
                'title': attempt.title,
                'difficulty': attempt.difficulty,
                'pattern_name': attempt.pattern_name,
                'description_excerpt': make_description_excerpt(attempt.description_text or '', max_chars=900),
                'stored_note': (attempt.stored_note or '')[:800],
                'thoughts': [thought[:400] for thought in attempt.thoughts[:8]],
                'code_excerpt': make_code_excerpt(attempt.code, max_chars=2800),
                'hint_count': attempt.hint_count,
                'submitted': attempt.submitted,
                'heuristic_score': attempt.heuristic_score,
                'heuristic_reasoning': [item[:280] for item in attempt.heuristic_reasoning[:6]],
                'recent_chat': [{'role': m.role, 'content': m.content[:420]} for m in recent_chat],
            }
        )

    candidates = [
        {
            'slug': candidate.slug,
            'title': candidate.title,
            'difficulty': candidate.difficulty,
            'pattern_name': candidate.pattern_name,
        }
        for candidate in context.candidate_recommendations[:20]
    ]

    return {
        'session_status': context.session_status,
        'total_questions': context.total_questions,
        'total_time_minutes': context.total_time_minutes,
        'remaining_time_sec': context.remaining_time_sec,
        'language': context.language,
        'total_score_heuristic': context.total_score_heuristic,
        'attempts': attempts,
        'candidate_recommendations': candidates,
    }


def parse_json_object(text: str) -> Optional[Dict[str, Any]]:
    """
    Parse first JSON object from raw model text.

    Handles common model outputs:
    - pure JSON
    - fenced JSON (```json ... ```)
    - explanatory text wrapped around one JSON object
    """

    if not text:
        return None

    cleaned = text.strip()
    if cleaned.startswith('```'):
        # Common model artifact: fenced JSON.
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r'\s*```$', '', cleaned).strip()

    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        pass

    # Fallback for responses that wrap JSON in extra prose.
    start = cleaned.find('{')
    end = cleaned.rfind('}')
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        parsed = json.loads(cleaned[start:end + 1])
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def parse_debrief_report(raw_text: str) -> Optional[DebriefReportPayload]:
    """
    Convert model JSON into validated DebriefReportPayload.
    Returns None when parsing or validation fails.
    """

    payload = parse_json_object(raw_text)
    if not payload:
        return None
    try:
        return DebriefReportPayload.model_validate(payload)
    except Exception:
        return None


def build_content(payload: MockInterviewRespondRequest, db_problem: Dict[str, Any]) -> str:
    """
    Merge request payload + db context into a single JSON string for model input.

    Merge precedence (highest first):
    1) Frontend payload problem fields
    2) db.json problem fields

    Why merge this way:
    - Frontend may carry fresher context than local backend db.
    - Backend still has fallback context even if frontend sends minimal data.
    """

    problem_payload = payload.problem.model_dump() if payload.problem else {}

    # Prefer clean text description if present; fallback to backend db text.
    # We avoid sending HTML to model prompts to reduce noise/tokens.
    description_text = (
        problem_payload.get('description_text')
        or db_problem.get('description_text')
        or ''
    )

    merged_problem = {
        'slug': payload.problem_slug,
        'title': problem_payload.get('title') or db_problem.get('title'),
        'difficulty': problem_payload.get('difficulty') or db_problem.get('difficulty'),
        'pattern_name': problem_payload.get('pattern_name') or db_problem.get('pattern_name'),
        'pattern_hint': problem_payload.get('pattern_hint') or db_problem.get('pattern_hint'),
        'key_insight': problem_payload.get('key_insight') or db_problem.get('key_insight'),
        # We keep an excerpt instead of full prompt to limit context size.
        'description_excerpt': make_description_excerpt(description_text),
        'topic_tags': problem_payload.get('topic_tags') or db_problem.get('topic_tags') or [],
    }

    # Only send recent turns to keep response focused and avoid context explosion.
    # Example: if full chat has 40 turns, we include the last 8 here.
    recent_chat = payload.messages[-8:]
    chat_serialized = [{'role': m.role, 'content': m.content} for m in recent_chat]

    content: Dict[str, Any] = {
        'session_id': payload.session_id,
        'mode': payload.mode,
        'hint_level': payload.hint_level,
        'problem': merged_problem,
        'recent_chat': chat_serialized,
    }

    if payload.mode == 'debrief':
        content['debrief_context'] = normalize_debrief_context(payload)

    return json.dumps(content, ensure_ascii=False)


# ---------------------------------------------------------------------------
# FastAPI app + endpoints
# ---------------------------------------------------------------------------

app = FastAPI(title='DSA Pattern Lab API', version='0.1.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=False,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/api/health')
def health():
    """Simple health probe including selected provider/model."""

    analyzer = get_analyzer()
    return {
        'status': 'ok',
        'provider': analyzer.provider.value,
        'model': analyzer.model_name,
    }


@app.post('/api/mock-interview/respond', response_model=MockInterviewRespondResponse)
def mock_interview_respond(payload: MockInterviewRespondRequest):
    """
    Generate interviewer reply for one chat turn.

    Failure behavior:
    - If provider call fails, return a deterministic fallback guidance message.
    - Endpoint still returns HTTP 200 so frontend can continue session flow.
    """

    # 1) Load static problem DB context (cached).
    db = load_db()
    db_problem = ((db.get('problems') or {}).get(payload.problem_slug) or {})

    # Last user message drives intent classification.
    last_user_message = ''
    for message in reversed(payload.messages):
        if message.role == 'user':
            last_user_message = message.content
            break

    # 2) Derive coarse intent used to steer interviewer style.
    intent = infer_intent(last_user_message, payload.hint_level)
    # 3) Build provider prompt + bounded content payload.
    prompt = build_prompt(payload.mode, intent, payload.hint_level)
    content = build_content(payload, db_problem)

    # 4) Execute provider call through the cached analyzer client.
    analyzer = get_analyzer()
    response = analyzer.analyze(content=content, prompt=prompt)

    if not response.success:
        # Failure is non-fatal by design: frontend continues session with fallback text.
        fallback = (
            'I could not reach the interviewer model right now. '
            'Continue with your current approach and explain your next invariant.'
        )
        return MockInterviewRespondResponse(
            reply=fallback,
            intent=intent,
            safety_flags=['provider_error'],
            provider=analyzer.provider.value,
            model=analyzer.model_name,
            debrief=None,
        )

    parsed_debrief: Optional[DebriefReportPayload] = None
    if payload.mode == 'debrief':
        # Debrief is best-effort. Parsing failure should not block response.
        parsed_debrief = parse_debrief_report(response.content)

    reply, safety_flags = sanitize_reply(response.content, payload.mode)
    if payload.mode == 'debrief' and not parsed_debrief:
        # Frontend interprets this flag and keeps deterministic heuristic report.
        safety_flags = [*safety_flags, 'debrief_parse_failed']

    return MockInterviewRespondResponse(
        reply=reply,
        intent=intent,
        safety_flags=safety_flags,
        provider=response.provider.value,
        model=response.model,
        debrief=parsed_debrief,
    )
