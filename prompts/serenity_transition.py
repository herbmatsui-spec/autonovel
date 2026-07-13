"""
Serenity Transition Logic: From Tension to Stillness

Goal:
Prevent jarring shifts when moving from high-tension states (Hegemony/Conflict) to low-tension states (Serenity). 
The goal is a 'deceleration curve' that mimics the natural calming of the human nervous system.

Transition Path (The Deceleration Curve):

1. The Immediate Aftermath (The Sigh):
- Trigger: Conflict ends or a major tension point is released.
- Action: The first beat must be a physical release (a deep sigh, shoulders dropping, a long exhale).
- Focus: The transition from 'doing' to 'being'.

2. Sensory Re-engagement (The Grounding):
- Trigger: After the initial release.
- Action: Introduce one dominant sensory anchor from serenity_anchors.json.
- Focus: Pulling the character's attention away from the conflict and back into the immediate physical environment.

3. The Shared Silence (The Synchronization):
- Trigger: Once grounded.
- Action: A moment of shared silence between characters. No dialogue.
- Focus: Establishing a mutual state of peace before speaking.

4. Entry into Serenity (The Arrival):
- Trigger: After the shared silence.
- Action: Transition to Level 1 or 2 Serenity.
- Focus: Low-tension dialogue or slow, mundane actions.

Implementation Guidelines:
- Avoid: Jumping directly from a shout to a peaceful tea scene.
- Requirement: At least two beats of 'deceleration' (Physical Release $\rightarrow$ Sensory Grounding) must occur before full Serenity is reached.
- Pacing: Each transition step should feel like a slow exhale.
"""

TRANSITION_LOGIC = {
    "path": ["Physical Release", "Sensory Grounding", "Shared Silence", "Serenity Arrival"],
    "required_beats": 2,
    "recommended_levels": "Start at Level 1, gradually increase as the scene deepens."
}

