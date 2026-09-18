"""一時修正スクリプト: branches テストの BranchRepository パッチをヘルパーに統一。"""
p = "tests/unit/routers/test_router_branches_coverage.py"
text = open(p, encoding="utf-8").read()

pairs = 0
singles = 0

# Pattern 1: branch_repo + chapter_repo pair
old1 = ('        m.setattr(branches_module, "BranchRepository", lambda s: branch_repo)\n'
        '        m.setattr(branches_module, "ChapterRepository", lambda s: chapter_repo)')
new1 = "        patch_branch_repo(m, branch_repo, chapter_repo)"
pairs += text.count(old1)
text = text.replace(old1, new1)

# Pattern 2: repo only
old2 = '        m.setattr(branches_module, "BranchRepository", lambda s: repo)'
new2 = "        patch_branch_repo(m, repo)"
singles += text.count(old2)
text = text.replace(old2, new2)

open(p, "w", encoding="utf-8", newline="").write(text)
print("pairs:", pairs, "singles:", singles)
