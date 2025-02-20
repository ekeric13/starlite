from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Set, Tuple, Type, Union, cast

from starlite.asgi.routing_trie.types import (
    ASGIHandlerTuple,
    PathParameterSentinel,
    create_node,
)
from starlite.asgi.utils import wrap_in_exception_handler
from starlite.types.internal_types import PathParameterDefinition

if TYPE_CHECKING:
    from starlite.app import Starlite
    from starlite.asgi.routing_trie.types import RouteTrieNode
    from starlite.routes import ASGIRoute, HTTPRoute, WebSocketRoute
    from starlite.types import ASGIApp, RouteHandlerType


def add_mount_route(
    current_node: "RouteTrieNode",
    mount_routes: Dict[str, "RouteTrieNode"],
    root_node: "RouteTrieNode",
    route: "ASGIRoute",
) -> "RouteTrieNode":
    """Add a node for a mount route.

    Args:
        current_node: The current trie node that is being mapped.
        mount_routes: A dictionary mapping static routes to trie nodes.
        root_node: The root trie node.
        route: The route that is being added.

    Returns:
        A trie node.
    """

    # we need to ensure that we can traverse the map both through the full path key, e.g. "/my-route/sub-path" and
    # via the components keys ["my-route, "sub-path"]
    if route.path not in current_node.children:
        root_node = current_node
        for component in route.path_components:
            if component not in current_node.children:
                current_node.children[component] = create_node()  # type: ignore[index]
            current_node = current_node.children[component]  # type: ignore[index]

    current_node.is_mount = True
    current_node.is_static = route.route_handler.is_static

    if route.path != "/":
        mount_routes[route.path] = root_node.children[route.path] = current_node
    else:
        mount_routes[route.path] = current_node

    return current_node


def add_route_to_trie(
    app: "Starlite",
    mount_routes: Dict[str, "RouteTrieNode"],
    plain_routes: Set[str],
    root_node: "RouteTrieNode",
    route: Union["HTTPRoute", "WebSocketRoute", "ASGIRoute"],
) -> "RouteTrieNode":
    """Add a new route path (e.g. '/foo/bar/{param:int}') into the route_map tree.

    Inserts non-parameter paths ('plain routes') off the tree's root
    node. For paths containing parameters, splits the path on '/' and
    nests each path segment under the previous segment's node (see
    prefix tree / trie).

    Args:
        app: The Starlite app instance.
        mount_routes: A dictionary mapping static routes to trie nodes.
        plain_routes: A set of routes that do not have path parameters.
        root_node: The root trie node.
        route: The route that is being added.

    Returns:
        A RouteTrieNode instance.
    """
    current_node = root_node

    is_mount = hasattr(route, "route_handler") and getattr(route.route_handler, "is_mount", False)  # pyright: ignore
    has_path_parameters = bool(route.path_parameters)

    if is_mount:  # pyright: ignore
        current_node = add_mount_route(
            current_node=current_node,
            mount_routes=mount_routes,
            root_node=root_node,
            route=cast("ASGIRoute", route),
        )

    elif not has_path_parameters:
        plain_routes.add(route.path)
        if route.path not in root_node.children:
            current_node.children[route.path] = create_node()
        current_node = root_node.children[route.path]

    else:
        for component in route.path_components:
            if isinstance(component, PathParameterDefinition):
                current_node.is_path_param_node = True
                next_node_key: Union[Type[PathParameterSentinel], str] = PathParameterSentinel

            else:
                next_node_key = component

            if next_node_key not in current_node.children:
                current_node.children[next_node_key] = create_node()

            current_node.child_keys = set(current_node.children.keys())
            current_node = current_node.children[next_node_key]

            if isinstance(component, PathParameterDefinition) and component.type is Path:
                current_node.is_path_type = True

    configure_node(route=route, app=app, node=current_node)
    return current_node


def configure_node(
    app: "Starlite",
    route: Union["HTTPRoute", "WebSocketRoute", "ASGIRoute"],
    node: "RouteTrieNode",
) -> None:
    """Set required attributes and route handlers on route_map tree node.

    Args:
        app: The Starlite app instance.
        route: The route that is being added.
        node: The trie node being configured.

    Returns:
        None
    """
    from starlite.routes import HTTPRoute, WebSocketRoute

    if not node.path_parameters:
        node.path_parameters = {}

    if isinstance(route, HTTPRoute):
        for method, handler_mapping in route.route_handler_map.items():
            handler, _ = handler_mapping
            node.asgi_handlers[method] = ASGIHandlerTuple(
                asgi_app=build_route_middleware_stack(app=app, route=route, route_handler=handler),
                handler=handler,
            )
            node.path_parameters[method] = route.path_parameters

    elif isinstance(route, WebSocketRoute):
        node.asgi_handlers["websocket"] = ASGIHandlerTuple(
            asgi_app=build_route_middleware_stack(app=app, route=route, route_handler=route.route_handler),
            handler=route.route_handler,
        )
        node.path_parameters["websocket"] = route.path_parameters

    else:
        node.asgi_handlers["asgi"] = ASGIHandlerTuple(
            asgi_app=build_route_middleware_stack(app=app, route=route, route_handler=route.route_handler),
            handler=route.route_handler,
        )
        node.path_parameters["asgi"] = route.path_parameters
        node.is_asgi = True


def build_route_middleware_stack(
    app: "Starlite",
    route: Union["HTTPRoute", "WebSocketRoute", "ASGIRoute"],
    route_handler: "RouteHandlerType",
) -> "ASGIApp":
    """Construct a middleware stack that serves as the point of entry for each route.

    Args:
        app: The Starlite app instance.
        route: The route that is being added.
        route_handler: The route handler that is being wrapped.

    Returns:
        An ASGIApp that is composed of a "stack" of middlewares.
    """
    from starlite.middleware.allowed_hosts import AllowedHostsMiddleware
    from starlite.middleware.compression import CompressionMiddleware
    from starlite.middleware.csrf import CSRFMiddleware

    # we wrap the route.handle method in the ExceptionHandlerMiddleware
    asgi_handler = wrap_in_exception_handler(
        debug=app.debug, app=route.handle, exception_handlers=route_handler.resolve_exception_handlers()  # type: ignore[arg-type]
    )

    if app.csrf_config:
        asgi_handler = CSRFMiddleware(app=asgi_handler, config=app.csrf_config)

    if app.compression_config:
        asgi_handler = CompressionMiddleware(app=asgi_handler, config=app.compression_config)
    if app.allowed_hosts:
        asgi_handler = AllowedHostsMiddleware(app=asgi_handler, config=app.allowed_hosts)

    for middleware in route_handler.resolve_middleware():
        if hasattr(middleware, "__iter__"):
            handler, kwargs = cast("Tuple[Any, Dict[str, Any]]", middleware)
            asgi_handler = handler(app=asgi_handler, **kwargs)
        else:
            asgi_handler = middleware(app=asgi_handler)  # type: ignore

    # we wrap the entire stack again in ExceptionHandlerMiddleware
    return wrap_in_exception_handler(
        debug=app.debug,
        app=cast("ASGIApp", asgi_handler),
        exception_handlers=route_handler.resolve_exception_handlers(),
    )  # pyright: ignore
