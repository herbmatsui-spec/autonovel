with open('agents/writing.py', 'rb') as f:
    content = f.read()

# Replace b'\x8c\xe7\x92\xa7' (corrupted "完璧") with b'\xe5\xae\x8c\xe7\x92\xa7' ("完璧" in UTF-8)
fixed_content = content.replace(b'\x8c\xe7\x92\xa7', b'\xe5\xae\x8c\xe7\x92\xa7')

with open('agents/writing.py', 'wb') as f:
    f.write(fixed_content)

print("Repair completed!")

