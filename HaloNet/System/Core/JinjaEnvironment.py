from jinja2 import Template, Environment, FileSystemLoader
from Core.Type import TypeBase, ArrayBase, MapBase, SubclassBase, AssetPtrBase, MailboxProxyDatatype, SetBase
import flask

jfilters = list()


def jfilter(func):
    jfilters.append(func)
    return func

broken_decorators = "", ""
broken_mb_decorators = "", ""


@jfilter
def set_broken_decorators(self, left, right):
    global broken_decorators
    broken_decorators = left, right


@jfilter
def set_broken_mb_decorators(self, left, right):
    global broken_mb_decorators
    broken_mb_decorators = left, right

@jfilter
def to_string(self, dt):
    return dt.to_string()


@jfilter
def break_type(self, typename):
    T = TypeBase.find_type(typename)
    if T is not None:
        if issubclass(T, ArrayBase):
            return f"TArray&lt;{broken_decorators[0] % T.base.__name__}{T.base.__name__}{broken_decorators[1]}&gt;"
        elif issubclass(T, SetBase):
            return f"TSet&lt;{broken_decorators[0] % T.base.__name__}{T.base.__name__}{broken_decorators[1]}&gt;"
        elif issubclass(T, MapBase):
            return f"TMap&lt;{broken_decorators[0] % T.base_key.__name__}{T.base_key.__name__}{broken_decorators[1]}, {broken_decorators[0] % T.base_value.__name__}{T.base_value.__name__}{broken_decorators[1]}&gt;"
        elif issubclass(T, SubclassBase):
            return f"TSubclassOf&lt;<tt><i>{T.class_name}</i></tt>&gt;"
        elif issubclass(T, AssetPtrBase):
            return f"TAssetPtr&lt;<tt><i>{T.class_name}</i></tt>&gt;"
        elif issubclass(T, MailboxProxyDatatype):
            return f"[Mailbox ({T.meta_context_name}) of {broken_mb_decorators[0] % T.meta_class_name}{T.meta_class_name}{broken_mb_decorators[1]}]"
    return f"{broken_decorators[0] % typename}{typename}{broken_decorators[1]}"

@jfilter
def parse_comments(self, comments):
    return "<br>".join([comment.lstrip("#").strip() for comment in comments.split("\n")]) if comments is not None else ""

@jfilter
def url_for(self, endpoint, **values):
    return flask.url_for(endpoint, **values)

jenv = Environment(loader=FileSystemLoader(''))

for jf in jfilters:
    jenv.filters[jf.__name__] = jf


def jrender(path, *args, **kwargs):
    templ = jenv.get_template(path)
    return templ.render(*args, **kwargs).encode()