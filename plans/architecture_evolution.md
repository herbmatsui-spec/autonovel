# PlotEpisode Architecture Evolution Plan

## 1. Goal: Type Safety (Step 4.2)
Enhance type safety for `PlotEpisodeBase` and its engine composition using Python Generics.

### Strategy
- Define a generic base class for engines: `BaseEngine[T]`.
- Update `PlotEpisodeBase` to accept a generic configuration type, allowing IDEs to infer engine attributes.
- Use `TypeVar` to constrain engine models.

### Proposed Structure
```python
from typing import TypeVar, Generic

T = TypeVar("T", bound=BaseEngine)

class EngineWrapper(Generic[T], BaseModel):
    engine: T

# Example for Episode
class PlotEpisodeBase(FlatModelMixin, CoreEngineMixin, Generic[T]):
    ...
```

## 2. Goal: ECS Pattern Transition (Step 5.3)
Transform `PlotEpisode` from Composition-based (fixed engines) to Entity-Component-System (dynamic components).

### Phase 1: Interface Decoupling
- Extract logic from `PlotEpisodeBase` (e.g., `unwrap_plot_metadata`) into a `PlotSystem` class.
- Standardize engine classes as `Component` data containers.

### Phase 2: Component Registry
- Implement an `EntityManager` that allows dynamic attachment of components (Engines) to a `PlotEpisode` entity at runtime.

### Phase 3: System Execution
- Separate `System` processors that iterate over entities and apply logic based on attached components.
