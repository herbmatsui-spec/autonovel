import ast
import glob
from dataclasses import dataclass


@dataclass
class Finding:
    file: str
    line: int
    type: str
    message: str
    severity: str

findings = []

def analyze_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        tree = ast.parse(content)
    except Exception:
        return

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if len(node.body) > 50:
                findings.append(Finding(filepath, node.lineno, "Maintainability", f"Function '{node.name}' is too long (>50 lines)", "MEDIUM"))
            if len(node.args.args) > 5:
                findings.append(Finding(filepath, node.lineno, "Maintainability", f"Function '{node.name}' has too many arguments (>5)", "LOW"))
        elif isinstance(node, ast.ExceptHandler):
            if node.type is None or (isinstance(node.type, ast.Name) and node.type.id == 'Exception'):
                findings.append(Finding(filepath, node.lineno, "Error-prone", "Catching generic Exception", "MEDIUM"))
        # Add more checks as needed

for py_file in glob.glob("I:/claude2/**/*.py", recursive=True):
    analyze_file(py_file)

with open("I:/claude2/scratch/audit_results.txt", "w", encoding='utf-8') as f:
    for finding in findings:
        f.write(f"[{finding.severity}] {finding.file}:{finding.line} - {finding.type}: {finding.message}\n")

