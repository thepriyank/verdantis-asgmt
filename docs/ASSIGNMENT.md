<!-- Brief as received (converted from the .docx, wording unchanged). Received: ____  Deadline: ____ -->

# Agentic Coding Lead — Candidate Assignment

## Overview

You are participating in an interview round for the role of **Agentic Coding Lead**.

This round is designed to evaluate how you use AI coding tools in a realistic engineering situation. We are not only interested in whether you can generate code quickly. We want to understand how you think, how you decompose ambiguous requirements, how you guide AI tools, how you verify generated output, and how you ensure the final solution is safe, maintainable, and reviewable.

You may use AI coding tools such as Cursor, Claude Code, Codex, Copilot, or similar tools during the exercise.

You are expected to explain:

- How you plan the work

- What you delegate to AI

- What you personally verify

- What assumptions you make

- How you test and validate the result

- What tradeoffs you choose within the time available

## Assignment Scenario

A company is building an internal enterprise data-quality assistant.

Business users upload item master records from multiple systems. The records are often inconsistent, incomplete, duplicated, or poorly described.

The goal of the assistant is to identify records that may need cleanup and generate structured review candidates for a human data steward.

The system should not automatically modify production data. It should produce suggestions that can be reviewed, approved, rejected, or investigated further by a human user.

## Data Model

Each uploaded record may contain fields such as:

```json

{

"item_id": "1001",

"item_description": "bearing",

"manufacturer": "SKF",

"manufacturer_part_number": "",

"category": "Mechanical",

"unit_of_measure": "EA",

"source_system": "ERP-A"

}

```

You may assume the input is a list of records in JSON, CSV, or another format supported by the starter project.

Typical fields:

- `item_id`

- `item_description`

- `manufacturer`

- `manufacturer_part_number`

- `category`

- `unit_of_measure`

- `source_system`

Some values may be missing, blank, malformed, duplicated, or inconsistent.

## Your Task

Build, modify, or review a small working slice of the data-quality assistant.

Your solution should identify data-quality review candidates from uploaded item records.

A review candidate is a structured finding that tells a human reviewer:

- Which item may have an issue

- What type of issue was detected

- Why it was detected

- How severe or confident the system is

- What action the reviewer may take

- Whether the finding came from a deterministic rule, heuristic, or AI-assisted suggestion

You do not need to integrate with a real LLM. You may stub, mock, or simulate the AI-assisted layer. However, your design should make it clear how a real AI service could be introduced safely later.

---

## Example Input

```json

[

{

"item_id": "1001",

"item_description": "bearing",

"manufacturer": "SKF",

"manufacturer_part_number": "",

"category": "Mechanical",

"unit_of_measure": "EA",

"source_system": "ERP-A"

},

{

"item_id": "1002",

"item_description": "SKF Bearing 6205 ZZ",

"manufacturer": "SKF",

"manufacturer_part_number": "6205-ZZ",

"category": "Electrical",

"unit_of_measure": "EA",

"source_system": "ERP-B"

}

]

```

---

## Example Output

```json

[

{

"item_id": "1001",

"issue_type": "missing_part_number",

"severity": "medium",

"confidence": 0.95,

"explanation": "Manufacturer is present but manufacturer part number is missing.",

"suggested_action": "Request manufacturer part number from the source owner.",

"source": "deterministic_rule"

},

{

"item_id": "1002",

"issue_type": "category_mismatch_candidate",

"severity": "low",

"confidence": 0.70,

"explanation": "Description suggests a mechanical bearing, but category is Electrical.",

"suggested_action": "Review category assignment before approval.",

"source": "ai_or_heuristic_candidate"

}

]

```

Your exact output shape may differ, but it should be structured, explainable, and suitable for a human-review workflow.

---

## Functional Requirements

Implement or improve at least three of the following checks:

1. Missing manufacturer part number when manufacturer is present

2. Weak or vague item description detection

3. Possible duplicate record detection

4. Category mismatch candidate

5. Suspicious or unsupported unit of measure

6. Normalized description suggestion

7. Malformed or incomplete row detection

8. Confidence and severity assignment

9. Explanation generation for each finding

---

## Important Product Behavior

The assistant should produce review candidates, not final automatic corrections.

Avoid language such as:

- “Fixed record”

- “Corrected data”

- “Auto-approved”

Prefer language such as:

- “Candidate issue detected”

- “Suggested action”

- “Needs review”

- “Potential duplicate”

- “Review before approval”

The human reviewer should remain the final decision-maker.

---

## Engineering Expectations

Your solution should demonstrate:

- Clear separation between deterministic validation and AI-assisted or heuristic suggestions

- Simple, maintainable code structure

- Meaningful function/module boundaries

- Handling of missing, blank, null, or malformed values

- Explainable output

- No mutation of original records unless explicitly approved by the workflow

- Tests or repeatable verification

- Thoughtful assumptions and tradeoffs

---

## AI Usage Expectations

You may use AI tools freely during the round, but you should be prepared to explain your usage.

We may ask:

- What did you ask the AI tool to do?

- Why did you delegate that part?

- How did you verify the AI-generated code?

- What did you reject or change from the AI output?

- What risks do you see in the generated solution?

- How would you make this workflow repeatable for a team?

We are not evaluating whether you can hide AI usage. We are evaluating whether you can use AI responsibly as an engineering lead.

---

## Suggested Approach

You may use the following approach, but you are free to choose your own.

### 1. Understand the requirement

Spend a few minutes identifying:

- Expected input and output

- Required checks

- Edge cases

- What should be deterministic

- What could be AI-assisted

- What should require human approval

### 2. Create a short implementation plan

Before coding, prepare a short plan:

- What you will build or change

- Which files/modules you will touch

- Which checks you will implement

- What tests you will add

- What you will defer due to time

### 3. Use AI tools deliberately

Good examples of AI delegation:

- Generate a first draft of a parser or validator

- Suggest test cases

- Refactor repetitive code

- Generate schema examples

- Review for edge cases

Poor examples of AI delegation:

- Ask AI to build the entire solution without review

- Accept code you cannot explain

- Skip tests because AI produced plausible output

- Let AI decide product behavior without your judgment

### 4. Verify the result

At minimum, show repeatable verification such as:

- Unit tests

- A sample command that processes input

- A before/after explanation

- A test fixture with expected output

- Error handling demonstration

---

## Edge Cases to Consider

You do not need to handle all of these, but you should be aware of them:

- Empty input file

- Missing required fields

- Blank strings with whitespace

- Null values

- Duplicate `item_id`

- Same item from different source systems

- Same manufacturer part number written in different formats

- Very short descriptions such as “bearing” or “valve”

- Descriptions containing useful attributes but wrong category

- Unsupported unit of measure

- Conflicting source-system values

- Non-English or abbreviation-heavy descriptions

## Discussion Topics After the Exercise

After the coding/review portion, we may discuss:

1. How would you introduce a real LLM into this workflow safely?

2. What data would you avoid sending to an external AI service?

3. How would you validate AI output before showing it to users?

4. How would you prevent AI-generated code from reducing code quality?

5. What CI checks would you require before merging?

6. How would you decide whether something should be a deterministic rule or AI-assisted suggestion?

7. How would you track confidence, explanation, and audit history?

8. How would you guide a team of developers using AI coding tools?

## Timebox Guidance

This is a timeboxed exercise. You are not expected to build a complete production system.

Prioritize:

1. Correctness over breadth

2. Explainability over cleverness

3. Human-review safety over automatic changes

4. Tests and verification over extra features

5. Clean boundaries over large generated code

If you cannot complete everything, clearly explain:

- What works now

- What is incomplete

- What risks remain

- What you would do next

## Deliverables During the Interview

By the end of the exercise, be ready to show:

1. Your implementation or code changes

2. How to run or test it

3. Sample input and output

4. Any tests you added or ran

5. Your assumptions and tradeoffs

6. How you used AI tools

7. What you would improve next

## Final Reminder

This round is not about generating the largest amount of code.

It is about demonstrating that you can lead AI-assisted software engineering responsibly:

- Think clearly

- Use AI tools effectively

- Verify output rigorously

- Protect product correctness

- Keep humans in control of sensitive decisions

- Build maintainable systems

- Help a team adopt agentic coding practices safely
