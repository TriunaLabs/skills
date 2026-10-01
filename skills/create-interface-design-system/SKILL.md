---
name: create-interface-design-system
description: "Generate, validate, or evolve a coherent interface design system from a product brief, existing brand evidence, or interface constraints. Use for semantic color and type tokens, component states, layout, elevation, responsive behavior, guardrails, agent prompts, and an HTML specimen; not for logo creation or unsupported claims about user outcomes."
license: MIT
---

# Create an interface design system

Turn a brief or existing interface evidence into an inspectable design contract that another agent can apply consistently. The default deliverable is a system JSON plus CSS tokens, a design guide, an agent prompt, and a standalone HTML specimen.

The nine required domains are visual atmosphere, semantic color, typography, component styling, layout, elevation, guardrails, responsive behavior, and agent guidance. Do not call a palette accessible until its measured text pairings pass the declared contrast targets. Do not infer a brand identity from an industry label alone.

## Choose the workflow

- **Generate:** create a new system from a brief. Read [generation rules](references/generation-rules.md).
- **Extract:** inspect supplied screenshots, markup, or tokens; distinguish observed values from recommendations. Read [evidence and provenance](references/evidence-and-provenance.md).
- **Evolve:** preserve established tokens and change only the requested domains. Record replacements and migration notes.
- **Validate:** validate a system JSON and its contrast pairs before implementation.
- **Specimen:** render a standalone page that demonstrates tokens, components, states, density, and responsive behavior.
- **Audit:** use `laws-of-ux` after rendering when the user asks for a usability review or when the specimen is a significant deliverable.

## Workflow

1. Establish the product, users, primary tasks, platform, brand evidence, tone, density, and constraints. If some are absent, state conservative assumptions in the artifact.
2. Write a brief matching `assets/sample-brief.json`. Treat supplied brand values as constraints, not suggestions.
3. Run the generator. Its local profiles provide a reproducible starting point; the agent may revise the result when evidence supports the change.
4. Validate semantic completeness and contrast. Fix failures before using the output.
5. Inspect the specimen at narrow and wide widths. Check keyboard focus, reduced motion, target size, text wrapping, and component states.
6. Return the generated directory and summarize the selected direction, assumptions, exceptions, and validation results.

```bash
python scripts/generate_system.py brief.json --out design-system
python scripts/validate_system.py design-system/design-system.json
```

The generator writes `design-system.json`, interoperable `tokens.json`, `tokens.css`, `DESIGN-GUIDE.md`, `agent-prompt.md`, and `specimen.html`.

## Decision rules

- Choose one visual direction and explain why it fits the tasks and evidence. Avoid mixing named styles for novelty.
- Use semantic roles such as `text`, `surface`, `primary`, `danger`, and `focus`; raw color names are implementation details.
- Define typography by function and readable fallback stacks. A remote font is optional enhancement, never a rendering dependency.
- Specify default, hover, active, focus-visible, disabled, loading, error, and success states where they apply.
- Base spacing on a small scale. Exceptions need a named component or layout reason.
- Use elevation to communicate containment or temporary layering, not decoration.
- Make responsive rules describe behavior. Breakpoints alone are insufficient.
- Put prohibitions beside the rule they protect. Keep the final do/don't list short enough for an agent to follow.
- Keep the generated agent prompt operational: source order, invariants, allowed variation, verification, and handoff.

Read [system schema](references/system-schema.md) when editing artifacts manually. Read [decision adapters](references/decision-adapters.md) only when Laya, Jev, or OpenAI Decisions is available and the user wants model-assisted selection.

The package's external research and licensing boundary is recorded in [sources and license audit](references/sources-and-license-audit.md).

## Boundaries

This skill produces an interface system, not a logo, corporate identity program, image library, or claim that a design will improve conversion. Image generation and Figma export require separate tools. `laws-of-ux` evaluates interaction principles; this skill owns the visual and implementation contract.
