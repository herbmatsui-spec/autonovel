# 例外階層図

```mermaid
graph TD
    Exception --> APIException
    Exception --> DatabaseException
    Exception --> WorkflowException
    Exception --> EngineException
    
    APIException --> RateLimitError
    APIException --> AuthError
    
    DatabaseException --> ConnectionError
    DatabaseException --> IntegrityError
    
    WorkflowException --> StepExecutionError
    WorkflowException --> ValidationError
```
