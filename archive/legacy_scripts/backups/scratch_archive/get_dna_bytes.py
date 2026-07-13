with open('agents/writing.py', 'rb') as f:
    content = f.read()

# Let's find 'dna_locker_inst' in bytes
pos = content.find(b'dna_locker_inst')
if pos != -1:
    start = max(0, pos - 100)
    end = min(len(content), pos + 500)
    snippet = content[start:end]
    with open('scratch/dna_locker.txt', 'wb') as out:
        out.write(snippet)

