from typing import TYPE_CHECKING, Any, Tuple

from starlite import Controller, HttpMethod, Response, Router, Starlite, get
from starlite.testing import create_test_client

if TYPE_CHECKING:
    from starlite.types import Serializer


def create_mock_encoder(name: str) -> Tuple[type, "Serializer"]:
    mock_type = type(name, (type,), {})

    def mock_encoder(obj: Any) -> Any:
        return name

    return mock_type, mock_encoder


handler_type, handler_encoder = create_mock_encoder("HandlerType")
router_type, router_encoder = create_mock_encoder("RouterType")
controller_type, controller_encoder = create_mock_encoder("ControllerType")
app_type, app_encoder = create_mock_encoder("AppType")


class MyController(Controller):
    type_encoders = {controller_type: controller_encoder}

    @get("/", type_encoders={handler_type: handler_encoder})
    def handler(self) -> Any:
        ...


router = Router("/router", type_encoders={router_type: router_encoder}, route_handlers=[MyController])
app = Starlite([router], type_encoders={app_type: app_encoder})


def test_resolve_type_encoders() -> None:
    route_handler = app.routes[0].route_handler_map[HttpMethod.GET][0]  # type: ignore
    assert route_handler.resolve_type_encoders() == {
        handler_type: handler_encoder,
        controller_type: controller_encoder,
        router_type: router_encoder,
        app_type: app_encoder,
    }


def test_type_encoders_response_override() -> None:
    class Foo:
        pass

    @get("/", type_encoders={Foo: lambda f: "foo"})
    def handler() -> Response:
        return Response({"obj": Foo()}, type_encoders={Foo: lambda f: "FOO"})

    with create_test_client([handler]) as client:
        assert client.get("/").json() == {"obj": "FOO"}
