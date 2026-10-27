# Write so the learner wants to continue

This style applies to AI, Software, HLD, LLD, DSA, and their coaching responses.

## The default shape

One small idea. One or two short sentences.

Then a concrete example or a small text picture.

```text
Input → what changes → result
```

Finish with a useful memory cue and one question to predict.

## An example

Avoid: “A prompt is an input contract for a probabilistic component.”

Use: “A prompt tells the model what job to do. Say what evidence it may use and what the answer should look like.”

Then show: “If East matches two depots, ask which one. Do not guess.”

The shorter version still needs validation and permission checks. Plain language must not remove the rule that makes the design correct.

## Editing rules

- Prefer verbs such as use, check, save, send, and retry.
- Keep necessary technical terms. Explain each one with familiar words and an example.
- Put a blank line between small ideas. Aim for one or two sentences and about 32 words per block.
- Split a list of constraints into bullets. Keep commands, formulas, and code in fenced blocks.
- Use a tiny input and a visible result. Make the learner predict one changed input.
- Add headings that answer a real question: “What changes?”, “What can fail?”, or “Why this check?”
- Keep reference answers separate from practice. A writing edit must not change exercise IDs, quiz keys, saved progress keys, or runnable code.
- A memory cue helps recall. It is not a replacement for the full explanation or its limitations.

## Source and rendering

Editable AI/Software/HLD Markdown lives in the journal. The app also stores DSA pattern source in backend/pipeline/data/patterns.json, and LLD material in frontend/public/lld-db.json.

The shared Markdown reader displays short reading blocks and brief plain-word definitions. It clones DOM ranges so links, emphasis, and inline code remain intact. Fenced code, diagrams, tables, and explicit line breaks keep their original structure. Plain-text HLD/LLD descriptions use the same sentence grouping.

backend/pipeline/reading_style.py is a conservative editing helper. It reflows prose and replaces a small set of filler phrases. It does not invent examples or rewrite complex sentences for you. The foundation lessons and 17 DSA pattern introductions were rewritten separately with concrete examples and text diagrams.

After editing, rebuild Software, AI, and HLD catalogs. Check matching runtime copies, stable identifiers/quiz keys, and code preservation. Review actual screens at desktop and phone widths. Keep the existing progress namespaces.

## Checks for this readability update · 2026-10-27

The desktop navigation keeps labels on one line and shows LLD/HLD directly. Smaller screens use a second row with horizontal navigation; resizing keeps the active course visible. The phone lesson steps use two columns.

All course families use the spaced reader. The journal pass reflowed 1,660 Markdown documents, then refined chapter introductions and metadata. Sixteen foundation lessons, all 17 DSA introductions and worked examples, and the 12 LLD introductions received separate plain-language rewrites.

Validation: 40 frontend tests, 27 backend tests, TypeScript checking, and the production build passed. The existing bundle-size and test-client deprecation advisories remain. Software, AI, HLD, and DSA data builders were run. The DSA rebuild kept all 200 problem records unchanged.

Compatibility checks preserved module/section/exercise IDs, quiz options and keys, existing code templates, UML, and problem IDs. The 71 DSA subpattern lessons retain their distinct explanations. A fenced-example audit found changes only in the 16 intentionally rewritten introductions; existing runnable lab code was not edited.

Browser checks covered desktop, laptop, and phone navigation; AI and Ruby examples; DSA prose; HLD plain/deeper explanations; LLD descriptions; long-guide reflow; preserved links; and page overflow. Progress namespaces were not changed.
