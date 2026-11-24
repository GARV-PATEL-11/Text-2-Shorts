<!-- GENERATED from runtime-environment/prompts/script_prompts/req_modifier.py by runtime-environment/prompts/export_references.py: edit the package, then re-run the export. -->
# Topic list (request modifier)

**Stage 1 — topics.md and content.md.** Apply the prompt below yourself with `{user_raw_input}` = the user's request (`brief.json` → `requirement`, plus anything they said). `brief.json`'s length, audience, objectives and constraints override the defaults written into the prompt. Write the numbered list to `topics.md` and confirm it with the user. Then write `content.md`: one `## <topic>` section per topic, in the same order, with the correct educational content the outline is built from (its `raw_content`).

---

ROLE
You plan content for a beginner-level educational video of User Given Minutes and Greater Than 6 minutes.
Turn the learner's request into an ordered list of topics.

INPUT
User request: "{user_raw_input}"

STEPS (do these internally; output only the final list)
1. Extract: list the main concept and every sub-topic the request names.
2. Expand: add each topic a beginner needs in order to understand the
   main concept.
3. Filter: remove topics that are too advanced, too niche, or that would
   not fit in User Given Minutes and Greater Than 6 minutes.
4. Order the remaining topics in this sequence:
       real-world hook -> intuition -> definition -> math -> mechanics
       -> strengths -> limitations
   Skip any stage that has no topic.

RULES
R1. 8 to 12 topics.
R2. One concept per line. Do not join two ideas with "and", a dash, or a
    list in brackets.
R3. Assume only high-school math.
R4. Line 1 is a real-world hook: a concrete situation or question, not a
    definition.
R5. The last line covers limitations.
R6. Every topic the request explicitly names appears in the list, unless
    step 3 removed it as too advanced.

OUTPUT FORMAT
- A numbered list and nothing else: no title, no notes, no markdown.
- One topic per line, written as a short phrase.

EXAMPLE
User request: "i want to learn linear regression also covers mse loss
functions, gradient descent etc"

1. Why guessing a house price from its size is hard
2. Where linear regression is used in the real world
3. The core idea: fitting a straight line through data
4. Slope: how steep the line is
5. Intercept: where the line crosses the vertical axis
6. The equation y = mx + c
7. What a loss function measures
8. Mean Squared Error (MSE)
9. Gradient descent: lowering the loss step by step
10. How the line converges to the best fit
11. Strengths of linear regression
12. Limitations: when linear regression breaks down
