from dependency_injector import providers

obj = providers.Object("test")
print("Class name:", type(obj).__name__)
print("Callable:", hasattr(obj, "__call__"))

