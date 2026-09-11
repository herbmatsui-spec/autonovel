with open(r"E:\hhh\src\legacy\writing_agent_v1.py", "rb") as f:
    content = f.read()

# Fix pm property - def should be at 4 spaces, body at 8
content = content.replace(
    b"\r\n    @property\r\n    def pm(self):\r\n    return self.prompt_manager\r\n",
    b"\r\n    @property\r\n    def pm(self):\r\n        return self.prompt_manager\r\n"
)

# Fix planner property - def should be at 4 spaces, not 8
content = content.replace(
    b"\r\n    @property\r\n        def planner(self):\r\n        return getattr(self, \"_planner\", None)\r\n",
    b"\r\n    @property\r\n    def planner(self):\r\n        return getattr(self, \"_planner\", None)\r\n"
)

with open(r"E:\hhh\src\legacy\writing_agent_v1.py", "wb") as f:
    f.write(content)