import re
import os
from datetime import datetime
from typing import List, Dict

def analyze_llm_latency(log_file: str) -> Dict:
    \"\"\"
    observability.py のログを解析して TTFT (Time to First Token) と Total Duration を抽出する
    \"\"\"
    ttfts = []
    durations = []
    
    if not os.path.exists(log_file):
        return {"error": f"Log file not found: {log_file}"}

    with open(log_file, "r", encoding="utf-8") as f:
        content = f.read()
        # 成功ログのパターン: ✅ Text API Success: model=..., len=..., dur=0.21s
        matches = re.findall(r"✅ Text API Success: model=.*, len=\d+, dur=([\d.]+)s", content)
        for m in matches:
            durations.append(float(m))

    return {
        "avg_duration": sum(durations) / len(durations) if durations else 0,
        "max_duration": max(durations) if durations else 0,
        "min_duration": min(durations) if durations else 0,
        "count": len(durations)
    }

def analyze_rerun_metrics(log_file: str) -> Dict:
    \"\"\"
    UIStateStore のリランカウント等のログを解析する
    \"\"\"
    # 実際の実装に合わせてログパターンを調整
    reruns = []
    if not os.path.exists(log_file):
        return {"error": f"Log file not found: {log_file}"}

    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            match = re.search(r"rerun_count: (\d+)", line)
            if match:
                reruns.append(int(match.group(1)))
    
    if not reruns:
        return {"error": "No rerun metrics found in logs"}
    
    return {
        "total_reruns": reruns[-1],
        "rerun_growth": reruns[-1] - reruns[0] if len(reruns) > 1 else 0,
        "samples": len(reruns)
    }

def main():
    print("--- Performance UX Report ---")
    
    # ログパスは環境に合わせて調整
    log_path = "logs/app.log" 
    
    llm_metrics = analyze_llm_latency(log_path)
    rerun_metrics = analyze_rerun_metrics(log_path)
    
    print("\n[LLM Latency]")
    if "error" in llm_metrics:
        print(llm_metrics["error"])
    else:
        print(f"  - Total Requests: {llm_metrics['count']}")
        print(f"  - Avg Duration: {llm_metrics['avg_duration']:.2f}s")
        print(f"  - Min/Max: {llm_metrics['min_duration']:.2f}s / {llm_metrics['max_duration']:.2f}s")
        
    print("\n[UI Rerun Metrics]")
    if "error" in rerun_metrics:
        print(rerun_metrics["error"])
    else:
        print(f"  - Final Rerun Count: {rerun_metrics['total_reruns']}")
        print(f"  - Growth during session: {rerun_metrics['rerun_growth']}")

if __name__ == \"__main__\":
    main()

