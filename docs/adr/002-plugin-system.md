# ADR-002: Plugin System Architecture

**Date:** 2026-07-07
**Status:** Accepted
**Decider(s):** Zoo (Software Engineer)

### 1. Context and Problem Statement
The "Hegemony Novel Engine" is designed to be highly flexible, allowing for various narrative engineering techniques, prompt modifications, and utility tools to be added without modifying the core engine logic. Adding every possible feature to the core would lead to a "monolithic" codebase that is hard to maintain, test, and evolve. 

There was a need for a mechanism to:
- Decouple core services from optional extensions.
- Allow developers to add new functionality by simply dropping a file into a directory.
- Avoid hard-coded import lists that need updating every time a new feature is added.

### 2. Decision to be Made
Define a mechanism for dynamic discovery and loading of external modules (plugins) that can extend the application's behavior.

### 3. Considered Options
- **Option 1: Manual Registration**
  - Pros: Explicit, easy to trace via static analysis.
  - Cons: High maintenance overhead; every plugin must be manually imported and registered in a central list.
- **Option 2: Configuration-based Loading (YAML/JSON)**
  - Pros: Controlled loading; can enable/disable plugins via config.
  - Cons: Requires a separate config file to be kept in sync with the filesystem.
- **Option 3: Dynamic Filesystem Discovery (`PluginLoader`)**
  - Pros: Zero-config extension; just add a `.py` file to the `plugins/` folder.
  - Cons: Implicit behavior; harder to trace "what is running" without looking at the filesystem; potential for loading unwanted scripts if not properly filtered.

### 4. Decision Outcome
**Chosen Option: Option 3 (Dynamic Filesystem Discovery)**

**Justification:**
Given the rapid prototyping nature of narrative engineering, the friction of manual registration (Option 1) or config management (Option 2) is too high. The `PluginLoader` provides a "plug-and-play" experience. By utilizing `importlib` and `pathlib`, the system can automatically incorporate new logic at startup, supporting a highly agile development cycle.

### 5. Consequences
- **Positive:**
  - **Extensibility:** Extremely low barrier to entry for adding new utilities or prompt modifiers.
  - **Decoupling:** Core logic remains lean and focused on orchestration.
- **Negative/Trade-offs:**
  - **Implicit Loading:** It's not immediately obvious from `app.py` which plugins are active.
  - **Error Isolation:** A syntax error in a single plugin could potentially crash the loader or the application if not wrapped in robust try-except blocks.
- **Risks:**
  - **Namespace Pollution:** Plugins could potentially overwrite core functions if not carefully namespaced.

### 6. Alternatives’ Trade-offs
Option 1 and 2 were rejected because they introduce "registration friction," which slows down the experimental nature of the tool's development.

### 7. Notes/References
- Implementation: [`src/core/plugin_loader.py`](src/core/plugin_loader.py)
- Plugin Location: `/plugins/*.py`
