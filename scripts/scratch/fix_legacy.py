with open(r"E:\hhh\src\legacy\writing_agent_v1.py", "rb") as f:
    content = f.read()

old = b'        return result.artifacts.get("writing_context", {})\r\n    async def write_episode'
new = b'        return result.artifacts.get("writing_context", {})\r\n\r\n    async def write_episode'

content = content.replace(old, new)

with open(r"E:\hhh\src\legacy\writing_agent_v1.py", "wb") as f:
    f.write(content)