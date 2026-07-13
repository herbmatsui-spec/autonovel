# Comfort Engine Integration Test Scenarios

These scenarios are designed to verify the functionality of the Comfort Kernel, specifically its ability to detect tension, select patterns, apply costs, and deepen resonance through the afterglow polish and audit loop.

## Scenario 1: The Breaking Point (High Tension -> Physical Salvation)
- **Initial State**:
    - `tension`: 95
    - `tension_delta`: 10
    - `summary`: "The protagonist is trapped in a collapsing ruin, exhausted and out of options. Their last hope is a distant exit that seems unreachable. They are facing an immediate threat of death."
    - `target_character`: "Protagonist"
    - `lack`: "Safety and the will to survive"
- **Expected Outcome**:
    - Trigger: `should_intervene` returns `True` (High Tension).
    - Pattern: `physical_salvation` selected.
    - Cost: Some significant loss (e.g., a precious item left behind to escape).
    - Result: A dramatic rescue that feels earned, followed by a physical afterglow (e.g., the first breath of fresh air).

## Scenario 2: The Soul's Void (Moderate Tension -> Validation)
- **Initial State**:
    - `tension`: 60
    - `tension_delta`: 0
    - `summary`: "The protagonist has achieved a great victory, but everyone praises the wrong reason. They feel deeply misunderstood and alone in their true intention, feeling that their core values are rejected by the world."
    - `target_character`: "Protagonist"
    - `lack`: "Existential validation / Being seen for who they truly are"
- **Expected Outcome**:
    - Trigger: `should_intervene` returns `True` (Resolution Gap/Lack).
    - Pattern: `validation` selected.
    - Cost: Vulnerability (the character must admit their true feelings to someone).
    - Result: A quiet, intimate scene where another character recognizes the protagonist's true self.

## Scenario 3: The Irreversible Loss (Low Tension -> Sublimation)
- **Initial State**:
    - `tension`: 30
    - `tension_delta`: -40
    - `summary`: "The battle is over, but the protagonist's mentor has died. The tension has dropped because the conflict is gone, but a hollow grief remains."
    - `target_character`: "Protagonist"
    - `lack`: "Meaning in the face of loss"
- **Expected Outcome**:
    - Trigger: `should_intervene` returns `True` (Low tension but low catharsis).
    - Pattern: `sublimation` selected.
    - Cost: Acceptance of the pain.
    - Result: A scene where the protagonist finds a way to carry the mentor's legacy, transforming grief into strength.
