import sys
from functools import wraps
import traceback
from typing import Callable, Any

def log(msg: str) -> None:
    # get current frame
    try:
        raise Exception
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        f = exc_traceback.tb_frame.f_back # type: ignore

    co = f.f_code # type: ignore
    sys.stderr.write("%s:%s :: %s : %s\n" %
                     (co.co_filename, f.f_lineno, co.co_name, msg)) # type: ignore
    sys.stderr.flush()

def catch_err(f: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(f)
    def __try(*args: Any, **kwargs: Any) -> Any:
        try:
            return f(*args, **kwargs)
        except BaseException:
            log("caught exception in function %s:\n %s" % \
                  (f.__name__, traceback.format_exc()))
    return __try

def main() -> None:
    log("test message")

if __name__ == "__main__":
    main()
