from backend.sanitizer import OutputSanitizer

print(OutputSanitizer.parse_llm_json('{"key": "value"}'))
print(OutputSanitizer._clean_story('```markdown\nHello\n```'))

