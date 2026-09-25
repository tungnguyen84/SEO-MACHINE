import os
import re

PATTERNS = [
    re.compile(r'(?i)(api_key|app_password|secret_key|private_key|aws_access|aws_secret)\s*[:=]\s*["\'][a-zA-Z0-9_\-]{16,}["\']'),
    re.compile(r'ghp_[a-zA-Z0-9]{36}'),
    re.compile(r'sk-[a-zA-Z0-9]{32,}'),
    re.compile(r'AKIA[0-9A-Z]{16}')
]

violations = []
for root, dirs, files in os.walk('.'):
    if any(k in root for k in ['.git', '__pycache__', 'node_modules', '.pytest_cache', 'brain']):
        continue
    for f in files:
        if f.endswith(('.py', '.json', '.md', '.ini', '.mako')):
            path = os.path.join(root, f)
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
                    for idx, line in enumerate(fh, 1):
                        for p in PATTERNS:
                            if p.search(line):
                                violations.append((path, idx, line.strip()[:40]))
            except Exception:
                pass

print(f"SECRET_SCAN_RESULT: {'PASS' if len(violations) == 0 else 'FAIL'}")
print(f"Total potential secret violations: {len(violations)}")
for v in violations:
    print(f"  File: {v[0]} Line: {v[1]} Preview: {v[2]}")
