import schemathesis.openapi
from src.backend.server import app

print("Creating schema from WSGI app...")
schema = schemathesis.openapi.from_wsgi(app)
print(f"Schema type: {type(schema)}")
print(f"Schema attributes: {[x for x in dir(schema) if not x.startswith('_')]}")
