---
resource_type: spec
version: "1.0"
domain: agent-infrastructure
triggers:
  - new_spec_needed
  - tool_reverse_engineering
  - system_extension
inputs:
  - requirement_description
  - existing_tool_or_script
  - integration_context
outputs:
  - new_spec_file
  - updated_integration_points
  - skill_definition
governed_by: /constitution.md
standalone: true
---

# Spec Creation Spec
**Version:** 1.0
**Purpose:** Machine-executable guide for building new specs and skills. An LLM reading this spec can produce a fully compliant, integrated spec or skill from scratch. Also defines what requires a spec vs a skill, and every integration point in the pipeline that a new spec must update.
**Governed by:** `/constitution.md`
**Audience:** LLMs building new system components. Humans reviewing them.

---

## Step 1 — Skill or Spec?

Apply this decision in order. Stop at the first match.

**Build a skill if ALL of the following are true:**
- Single-purpose behavior executable in one pass
- No structured JSON input or output required
- Not invoked by other specs
- No constitutional alignment check needed
- Not reused across multiple programs or contexts

**Build a spec if ANY of the following are true:**
- Requires constitutional alignment checks before output delivery
- Reused across programs, contexts, or sessions
- Requires multiple processing passes to produce output
- Produces artifacts written to disk (JSON, .ics, .md, .jsonl)
- Will be invoked by or invokes other specs

**When uncertain:** default to skill. Promote to spec only when the system actually needs the structure.

---

## Step 2 — If Skill: Define It

A skill is a concise behavioral instruction. It lives in the constitution (Article IV), `.cursorrules`, or the relevant spec's persona/behavioral section. It does not get its own file.

**Skill format:**
```
### [Skill Name]
[One to three sentences. Imperative voice. States exactly what the agent does,
when it does it, and what it produces or notes. No preamble.]
```

**Examples of correct skill placement:**
- Agent behavior during all sessions → Article IV of `constitution.md`
- Behavior specific to a session type → behavioral section of `weekly-session-spec.md`
- Behavior specific to a pipeline pass → relevant pass in `program-pipeline-orchestrator.md`
- Cursor-specific behavior → `.cursorrules`

Write the skill. Insert it at the correct location. Done — no new file needed.

---

## Step 3 — If Spec: Gather Requirements

Before writing any spec content, resolve these fields. If building from an existing tool, reverse engineer them from the tool's behavior.

```
SPEC_NAME:          [descriptive-kebab-case-name]
DOMAIN:             [program-management | compliance | vendor | communications |
                     calendar | session-management | agent-infrastructure]
PURPOSE:            [one sentence — what work pattern this encodes]
TRIGGER:            [what condition causes this spec to be invoked]
INPUTS:             [what the spec needs to run — list each]
OUTPUTS:            [what the spec produces — list each]
PASSES:             [how many processing passes, and what each does]
STANDALONE:         [true if invokable directly | false if only called by orchestrator]
ENTRY_POINT:        [true if principal-facing | false if internal only]
INVOKED_BY:         [which specs call this one, if any]
INVOKES:            [which specs this one calls, if any]
CONSTITUTIONAL_ARTICLES: [list articles from constitution.md that actively govern this spec]
```

**Reverse engineering an existing tool:**
If a script or tool already exists, extract requirements by answering:
- What does it accept as input? → `INPUTS`
- What does it produce? → `OUTPUTS`
- What decisions does it make? → `PASSES`
- What could go wrong and what should it do? → error handling in each pass
- Does it need to know about program state, prior runs, or memory? → `INVOKED_BY`, `INPUTS`
- Would it benefit from constitutional alignment checks on its output? → `CONSTITUTIONAL_ARTICLES`

---

## Step 4 — Build the Spec

Produce the spec file using this structure. Every section is required unless marked optional.

### 4.1 YAML Frontmatter

```yaml
---
resource_type: spec
version: "1.0"
domain: [DOMAIN]
triggers:
  - [TRIGGER]
inputs:
  - [each INPUT]
outputs:
  - [each OUTPUT]
governed_by: /constitution.md
standalone: [true|false]
entry_point: [true|false]
invoked_by:
  - [spec filenames, if any]
invokes:
  - [spec filenames, if any]
depends_on:
  - [spec filenames, if any]
---
```

### 4.2 Header Block

```markdown
# [Spec Title]
**Version:** 1.0
**Purpose:** [PURPOSE — one sentence]
**Governed by:** `/constitution.md`
**Portability:** Executable by any capable LLM (Claude, Gemini, GPT, Ollama)
**Maintainer:** `[your name/handle]`
```

### 4.3 Constitutional Guidance

List only the articles that actively govern this spec's behavior. Do not list all articles. Each entry states the article, the specific mandate, and why it applies here.

```markdown
## Constitutional Guidance

- **[Article name]** ([Article reference]) — [why it applies to this spec specifically]
```

Minimum one article. Maximum what is genuinely relevant. If constitutional alignment produces a gate check on output, name the specific check here.

### 4.4 Persona Definition

One paragraph. Defines the agent's role, expertise, and behavioral constraints while executing this spec. Written in second person ("You are..."). Includes what the agent does not do as well as what it does.

### 4.5 Parameters Block

All inputs the spec needs to run. Use this structure:

```markdown
## Parameters

PARAM_NAME: [type and description]
PARAM_NAME: [type and description]
```

### 4.6 Processing Passes

One section per pass. Each pass has: a trigger condition, explicit instructions, and defined output. Use imperative voice. Write for an LLM audience — precise and unambiguous.

```markdown
## Pass [N] — [Pass Name]

**Trigger:** [when this pass runs]

[Instructions. Imperative. Specific. Include decision logic, flag conditions,
and what to do when data is missing or ambiguous.]

**Output:** [what this pass produces]
```

### 4.7 Output Assembly (optional)

Required if the spec produces a structured output format (JSON, markdown report, .ics, etc.). Define the exact schema or template.

### 4.8 Flags Section (optional)

Required if the spec can surface constitutional flags, inferred data warnings, or escalation triggers. Define each flag type and what triggers it.

### 4.9 Quality Gate Integration

Every spec that produces output for the principal must include this section:

```markdown
## Quality Gate

All outputs pass through `/specs/quality-gate-spec.md` before delivery.
Constitutional alignment check: [list which alignment checks apply]
Automatic REJECT triggers for this spec: [any spec-specific rejection criteria]
```

### 4.10 Suggested Repo Path and Companion Specs

```markdown
## Suggested Repo Path
`/specs/[spec-filename].md`

## Companion Specs
- Governed by: `/constitution.md`
- [other relationships]
```

---

## Step 5 — Update Integration Points

A new spec does not exist in isolation. Every integration point below must be evaluated and updated if the new spec touches that layer. For each point, the instruction is: read the current file, find the relevant section, add the new spec.

### 5.1 YAML Frontmatter of Calling Specs

If any existing spec invokes the new spec, add it to that spec's `invokes:` frontmatter list.
If the new spec is invoked by an existing spec, add the caller to `invoked_by:` in the new spec's frontmatter.

**Files to check:** all specs in `/specs/`

### 5.2 Program Pipeline Orchestrator

File: `/specs/program-pipeline-orchestrator.md`

If the new spec is part of the program management pipeline:
- Add it to the routing table under the correct intent
- Add it to the pipeline architecture diagram
- Add it to the `invokes:` frontmatter list
- If it produces calendar events, flags, or decisions, update the output assembly section to include its output fields in the run JSON schema

### 5.3 Session Init Spec

File: `/specs/session-init-spec.md`

If the new spec is principal-facing or produces deliverables a principal would request:
- Add a routing entry to the routing table: `| [trigger phrase] | [spec filename] | [notes] |`
- Add to the quick reference card under SPECS
- Update the `invokes:` frontmatter list

### 5.4 Weekly Session Spec

File: `/specs/weekly-session-spec.md`

If the new spec produces outputs that would appear in a weekly session (deliverables, pattern data, agenda items):
- Add it to the `depends_on:` frontmatter list
- If it produces staged deliverables, update the session close staging section

### 5.5 Quality Gate Spec

File: `/specs/quality-gate-spec.md`

If the new spec produces a new output type not currently covered by the quality gate:
- Add the output type to the output-type-specific checks section
- Define required sections and any spec-specific rejection criteria

### 5.6 Constitution

File: `/constitution.md`

If the new spec introduces a behavioral pattern that should apply system-wide:
- Add it as a new mandate in Article IV (behavioral mandates)
- Update the quick reference card
- Increment the constitution version and add an amendment note

### 5.7 .cursorrules

File: `/.cursorrules`

If the new spec changes session-start behavior or adds a new principal-facing capability the agent should be aware of without loading session-init-spec.md:
- Add a one-line note to the relevant section

### 5.8 README

File: `/README.md`

Always:
- Add the new spec to the Spec Reference table
- Add it to the architecture diagram if it is principal-facing or part of the pipeline
- If it introduces a new directory or file type, add to the repo structure section

### 5.9 Provenance Log Output Types

File: `/scripts/provenance_log.py`

If the new spec produces a new deliverable type not in the `OUTPUT_TYPES` list:
- Add the new type string to `OUTPUT_TYPES` in `provenance_log.py`

---

## Step 6 — Self-Check Before Delivery

Before presenting the new spec, verify:

```
SPEC SELF-CHECK

Frontmatter complete:
  □ resource_type, version, domain, triggers, inputs, outputs present
  □ governed_by set to /constitution.md
  □ standalone and entry_point correctly set
  □ invoked_by and invokes reflect actual relationships

Structure complete:
  □ All required sections present (4.1–4.4, 4.5 if inputs exist, 4.6, 4.9, 4.10)
  □ Constitutional guidance lists only genuinely active articles
  □ Each pass has trigger, instructions, and defined output
  □ Quality gate section present

Integration points updated:
  □ Orchestrator updated if pipeline spec
  □ Session init routing table updated if principal-facing
  □ README spec reference table updated
  □ Calling spec frontmatter updated
  □ Provenance log output types updated if new deliverable type

Format compliant (quality gate pre-check):
  □ No numbered headers
  □ No parenthetical subtitles
  □ No AI generation artifacts
  □ Imperative voice in processing instructions
  □ Written for LLM audience — precise, unambiguous, no padding
```

If any box is unchecked, resolve before delivery. Do not present an incomplete spec.

---

## Trigger

```
BEGIN SPEC CREATION
```

Provide `SPEC_NAME`, `PURPOSE`, and any existing tool or context to reverse engineer from. The agent executes Steps 1–6 and delivers: the new spec file, a list of integration points updated, and a summary of what was built and why.

---

## Suggested Repo Path

`/specs/spec-creation-spec.md`

## Companion Specs
- Governed by: `/constitution.md`
- Quality gate: `/specs/quality-gate-spec.md`
- References all specs in `/specs/` as integration targets
