import json

log_path = r'C:\Users\keide\.gemini\antigravity\brain\952bd84d-f99e-49f0-bd70-1a11af31b2aa\.system_generated\logs\overview.txt'

with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        try:
            data = json.loads(line)
            if data.get('type') == 'PLANNER_RESPONSE':
                for tc in data.get('tool_calls', []):
                    args = tc.get('args', {})
                    # Some logs have args as strings, some as dicts
                    if isinstance(args, str):
                        try:
                            # The args might be double-escaped in the log
                            # Actually, let's just check the string
                            if 'sanitizer.py' in args:
                                print(f"Found tool call for sanitizer.py in step {data.get('step_index')}")
                                print(args)
                        except:
                            pass
                    else:
                        target = args.get('TargetFile') or args.get('AbsolutePath')
                        if target and 'sanitizer.py' in target:
                            print(f"Found tool call for sanitizer.py in step {data.get('step_index')}")
                            print(json.dumps(args, indent=2, ensure_ascii=False))
        except:
            continue

