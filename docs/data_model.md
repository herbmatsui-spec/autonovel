# データモデル図

```mermaid
erDiagram
    Book ||--o{ Chapter : contains
    Book ||--o{ Character : features
    Book ||--o{ Plot : has
    Plot ||--o{ Episode : contains
    Character ||--o{ Plot : participates
```
