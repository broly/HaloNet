import sys
from aiohttp import web
from Core.JinjaEnvironment import jrender


async def web_run_app(app, *, host='0.0.0.0', port=None,
                      shutdown_timeout=60.0, ssl_context=None,
                      print=print, backlog=128):
    """ Just run an web app locally """
    if port is None:
        if not ssl_context:
            port = 8080
        else:
            port = 8443

    loop = app.loop

    handler = app.make_handler()
    srv = await loop.create_server(handler, host, port, ssl=ssl_context)

    scheme = 'https' if ssl_context else 'http'
    prompt = '127.0.0.1' if host == '0.0.0.0' else host
    print("======== Running on {scheme}://{prompt}:{port}/ ========\n"
          "(Press CTRL+C to quit)".format(
              scheme=scheme, prompt=prompt, port=port))

    return srv, handler


def from_file(path, *args, **kwargs):
    return jrender(path, *args, **kwargs)


def route(route_path=None, route_page=None, method_type='GET'):
    def decorator(method):
        nonlocal route_path
        nonlocal route_page

        if route_path is None:
            route_path = f"/{method.__name__}"

        if route_page is None:
            route_page = f"Site/{method.__name__}.html"

        async def decorated(*args):
            dictionary = await method(*args)
            return web.Response(body=from_file(route_page, **dictionary),
                                headers={'Content-Type': 'text/html'})

        frame_locals = sys._getframe(1).f_locals
        if '__routes__' not in frame_locals:
            frame_locals['__routes__'] = list()
        frame_locals['__routes__'].append(dict(method=method.__name__,
                                               path=route_path,
                                               page=route_page,
                                               method_type=method_type))
        return decorated
    return decorator
