"""Reflow course prose without changing fenced examples, links, lists or keys.

This is an editing helper, not an AI rewrite. New lessons still need an author.
"""
import re

PLAIN_PHRASES = {
    'in order to': 'to',
    'prior to': 'before',
    'subsequent to': 'after',
    'at this point in time': 'now',
    'due to the fact that': 'because',
    'in the event that': 'if',
    'it is important to note that ': '',
    'it is worth noting that ': '',
    'utilizes': 'uses',
    'utilize': 'use',
    'utilizing': 'using',
    'leverages': 'uses',
    'leverage': 'use',
    'leveraging': 'using',
    'facilitates': 'helps',
    'facilitate': 'help',
    'ascertain': 'check',
    'aforementioned': 'earlier',
}

def prose_beats(value, max_words=32):
    protected=[]
    def protect(match):
        protected.append(match[0]);return f'\ue000{len(protected)-1}\ue001'
    # Keep inline expressions, links, URLs and emphasis intact while editing prose.
    text=re.sub(r'`+[^`\n]*`+|!?\[[^\]\n]+\]\([^\n]*?\)|https?://\S+|\*\*[^\n]+?\*\*',protect,value)
    for old,new in PLAIN_PHRASES.items():
        def replace(match):
            return new[:1].upper()+new[1:] if match[0][:1].isupper() else new
        text=re.sub(r'\b'+re.escape(old)+r'(?=\b|$)',replace,text,flags=re.I)
    # Do not mistake common abbreviations or version numbers for a full stop.
    text=re.sub(r'\b(?:e\.g\.|i\.e\.|Dr\.|Mr\.|Ms\.|vs\.)',protect,text)
    sentences=re.split(r'(?<=[.!?])\s+(?=[A-Z0-9“‘\ue000])',text.strip())
    beats=[];pending=[];words=0
    for sentence in sentences:
        size=len(sentence.split())
        if pending and (len(pending)==2 or words+size>max_words):
            beats.append(' '.join(pending));pending=[];words=0
        pending.append(sentence);words+=size
    if pending:beats.append(' '.join(pending))
    def restore(beat):
        return re.sub('\ue000(\\d+)\ue001',lambda m:protected[int(m[1])],beat)
    return [restore(beat) for beat in beats if beat]

def format_markdown(value):
    # Fenced blocks are copied byte-for-byte, including internal blank lines.
    chunks=re.split(r'(^[ \t]*(?:`{3,}|~{3,})[^\n]*\n[\s\S]*?^[ \t]*(?:`{3,}|~{3,})[^\n]*(?:\n|$))',value,flags=re.M)
    result=[]
    for i,chunk in enumerate(chunks):
        if i%2:result.append(chunk);continue
        paragraphs=re.split(r'(\n\s*\n)',chunk)
        for j,paragraph in enumerate(paragraphs):
            if j%2 or not paragraph.strip():continue
            first=paragraph.lstrip()
            if re.match(r'(?:#{1,6}\s|[-*+]\s|\d+[.)]\s|[>|<]|\[.+\]:)',first) or paragraph.startswith(('    ','\t')):
                continue
            paragraphs[j]='\n\n'.join(prose_beats(' '.join(paragraph.splitlines())))
        result.append(''.join(paragraphs))
    return ''.join(result)
