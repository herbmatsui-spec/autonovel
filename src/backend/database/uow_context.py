import contextvars

current_uow = contextvars.ContextVar('current_uow', default=None)

