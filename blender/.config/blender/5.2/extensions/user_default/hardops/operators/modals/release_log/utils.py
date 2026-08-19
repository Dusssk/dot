import traceback


def safe_call(func):
    def wrapper(self, context=None, event=None, *args, **kwargs):
        try:
            _args = [a for a in [context, event] if a]
            return func(self, *_args, *args, **kwargs)

        except Exception:
            print(traceback.format_exc())

            try:
                return self.remove(force=True)

            except Exception:
                print(traceback.format_exc())
                return {'CANCELLED'}
    return wrapper

