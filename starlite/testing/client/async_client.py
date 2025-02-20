from contextlib import AsyncExitStack
from typing import TYPE_CHECKING, Any, Dict, Generic, Mapping, Optional, TypeVar, Union

from starlite import HttpMethod
from starlite.exceptions import MissingDependencyException
from starlite.testing.client.base import BaseTestClient
from starlite.testing.life_span_handler import LifeSpanHandler
from starlite.testing.transport import TestClientTransport
from starlite.types import AnyIOBackend, ASGIApp

try:
    from httpx import USE_CLIENT_DEFAULT, AsyncClient, Response
except ImportError as e:
    raise MissingDependencyException(
        "To use starlite.testing, install starlite with 'testing' extra, e.g. `pip install starlite[testing]`"
    ) from e


if TYPE_CHECKING:
    from httpx._client import UseClientDefault
    from httpx._types import (
        AuthTypes,
        CookieTypes,
        HeaderTypes,
        QueryParamTypes,
        RequestContent,
        RequestData,
        RequestFiles,
        TimeoutTypes,
        URLTypes,
    )

    from starlite.middleware.session.base import BaseBackendConfig


T = TypeVar("T", bound=ASGIApp)


class AsyncTestClient(AsyncClient, BaseTestClient, Generic[T]):  # type: ignore [misc]
    lifespan_handler: LifeSpanHandler
    exit_stack: "AsyncExitStack"

    def __init__(
        self,
        app: T,
        base_url: str = "http://testserver.local",
        raise_server_exceptions: bool = True,
        root_path: str = "",
        backend: AnyIOBackend = "asyncio",
        backend_options: Optional[Mapping[str, Any]] = None,
        session_config: Optional["BaseBackendConfig"] = None,
        cookies: Optional["CookieTypes"] = None,
    ):
        """An Async client implementation providing a context manager for testing applications asynchronously.

        Args:
            app: The instance of :class:`Starlite <starlite.app.Starlite>` under test.
            base_url: URL scheme and domain for test request paths, e.g. 'http://testserver'.
            raise_server_exceptions: Flag for the underlying test client to raise server exceptions instead of
                wrapping them in an HTTP response.
            root_path: Path prefix for requests.
            backend: The async backend to use, options are "asyncio" or "trio".
            backend_options: 'anyio' options.
            session_config: Configuration for Session Middleware class to create raw session cookies for request to the
                route handlers.
            cookies: Cookies to set on the client.
        """
        BaseTestClient.__init__(
            self,
            app=app,
            base_url=base_url,
            backend=backend,
            backend_options=backend_options,
            session_config=session_config,
            cookies=cookies,
        )
        AsyncClient.__init__(
            self,
            app=app,
            base_url=base_url,
            headers={"user-agent": "testclient"},
            follow_redirects=True,
            cookies=cookies,
            transport=TestClientTransport(  # type: ignore [arg-type]
                client=self,
                raise_server_exceptions=raise_server_exceptions,
                root_path=root_path,
            ),
        )

    async def __aenter__(self) -> "AsyncTestClient[T]":
        async with AsyncExitStack() as stack:
            self.blocking_portal = portal = stack.enter_context(self.portal())
            self.lifespan_handler = LifeSpanHandler(client=self)

            @stack.callback
            def reset_portal() -> None:
                delattr(self, "blocking_portal")

            @stack.callback
            def wait_shutdown() -> None:
                portal.call(self.lifespan_handler.wait_shutdown)

            self.exit_stack = stack.pop_all()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.exit_stack.aclose()

    async def request(
        self,
        method: str,
        url: "URLTypes",
        *,
        content: Optional["RequestContent"] = None,
        data: Optional["RequestData"] = None,
        files: Optional["RequestFiles"] = None,
        json: Optional[Any] = None,
        params: Optional["QueryParamTypes"] = None,
        headers: Optional["HeaderTypes"] = None,
        cookies: Optional["CookieTypes"] = None,
        auth: Optional[Union["AuthTypes", "UseClientDefault"]] = USE_CLIENT_DEFAULT,
        follow_redirects: Union[bool, "UseClientDefault"] = USE_CLIENT_DEFAULT,
        timeout: Union["TimeoutTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        extensions: Optional[Mapping[str, Any]] = None,
    ) -> Response:
        """Sends a request.

        Args:
            method: An HTTP method.
            url: URL or path for the request.
            content: Request content.
            data: Form encoded data.
            files: Multipart files to send.
            json: JSON data to send.
            params: Query parameters.
            headers: Request headers.
            cookies: Request cookies.
            auth: Auth headers.
            follow_redirects: Whether to follow redirects.
            timeout: Request timeout.
            extensions: Dictionary of ASGI extensions.

        Returns:
            An HTTPX Response.
        """
        return await AsyncClient.request(
            self,
            url=self.base_url.join(url),
            method=method.value if isinstance(method, HttpMethod) else method,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    async def get(  # type: ignore [override]
        self,
        url: "URLTypes",
        *,
        params: Optional["QueryParamTypes"] = None,
        headers: Optional["HeaderTypes"] = None,
        cookies: Optional["CookieTypes"] = None,
        auth: Union["AuthTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        follow_redirects: Union[bool, "UseClientDefault"] = USE_CLIENT_DEFAULT,
        timeout: Union["TimeoutTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        extensions: Optional[Mapping[str, Any]] = None,
    ) -> Response:
        """Sends a GET request.

        Args:
            url: URL or path for the request.
            params: Query parameters.
            headers: Request headers.
            cookies: Request cookies.
            auth: Auth headers.
            follow_redirects: Whether to follow redirects.
            timeout: Request timeout.
            extensions: Dictionary of ASGI extensions.

        Returns:
            An HTTPX Response.
        """
        return await AsyncClient.get(
            self,
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    async def options(
        self,
        url: "URLTypes",
        *,
        params: Optional["QueryParamTypes"] = None,
        headers: Optional["HeaderTypes"] = None,
        cookies: Optional["CookieTypes"] = None,
        auth: Union["AuthTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        follow_redirects: Union[bool, "UseClientDefault"] = USE_CLIENT_DEFAULT,
        timeout: Union["TimeoutTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        extensions: Optional[Mapping[str, Any]] = None,
    ) -> Response:
        """Sends an OPTIONS request.

        Args:
            url: URL or path for the request.
            params: Query parameters.
            headers: Request headers.
            cookies: Request cookies.
            auth: Auth headers.
            follow_redirects: Whether to follow redirects.
            timeout: Request timeout.
            extensions: Dictionary of ASGI extensions.

        Returns:
            An HTTPX Response.
        """
        return await AsyncClient.options(
            self,
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    async def head(
        self,
        url: "URLTypes",
        *,
        params: Optional["QueryParamTypes"] = None,
        headers: Optional["HeaderTypes"] = None,
        cookies: Optional["CookieTypes"] = None,
        auth: Union["AuthTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        follow_redirects: Union[bool, "UseClientDefault"] = USE_CLIENT_DEFAULT,
        timeout: Union["TimeoutTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        extensions: Optional[Mapping[str, Any]] = None,
    ) -> Response:
        """Sends a HEAD request.

        Args:
            url: URL or path for the request.
            params: Query parameters.
            headers: Request headers.
            cookies: Request cookies.
            auth: Auth headers.
            follow_redirects: Whether to follow redirects.
            timeout: Request timeout.
            extensions: Dictionary of ASGI extensions.

        Returns:
            An HTTPX Response.
        """
        return await AsyncClient.head(
            self,
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    async def post(
        self,
        url: "URLTypes",
        *,
        content: Optional["RequestContent"] = None,
        data: Optional["RequestData"] = None,
        files: Optional["RequestFiles"] = None,
        json: Optional[Any] = None,
        params: Optional["QueryParamTypes"] = None,
        headers: Optional["HeaderTypes"] = None,
        cookies: Optional["CookieTypes"] = None,
        auth: Union["AuthTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        follow_redirects: Union[bool, "UseClientDefault"] = USE_CLIENT_DEFAULT,
        timeout: Union["TimeoutTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        extensions: Optional[Mapping[str, Any]] = None,
    ) -> Response:
        """Sends a POST request.

        Args:
            url: URL or path for the request.
            content: Request content.
            data: Form encoded data.
            files: Multipart files to send.
            json: JSON data to send.
            params: Query parameters.
            headers: Request headers.
            cookies: Request cookies.
            auth: Auth headers.
            follow_redirects: Whether to follow redirects.
            timeout: Request timeout.
            extensions: Dictionary of ASGI extensions.

        Returns:
            An HTTPX Response.
        """
        return await AsyncClient.post(
            self,
            url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    async def put(
        self,
        url: "URLTypes",
        *,
        content: Optional["RequestContent"] = None,
        data: Optional["RequestData"] = None,
        files: Optional["RequestFiles"] = None,
        json: Optional[Any] = None,
        params: Optional["QueryParamTypes"] = None,
        headers: Optional["HeaderTypes"] = None,
        cookies: Optional["CookieTypes"] = None,
        auth: Union["AuthTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        follow_redirects: Union[bool, "UseClientDefault"] = USE_CLIENT_DEFAULT,
        timeout: Union["TimeoutTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        extensions: Optional[Mapping[str, Any]] = None,
    ) -> Response:
        """Sends a PUT request.

        Args:
            url: URL or path for the request.
            content: Request content.
            data: Form encoded data.
            files: Multipart files to send.
            json: JSON data to send.
            params: Query parameters.
            headers: Request headers.
            cookies: Request cookies.
            auth: Auth headers.
            follow_redirects: Whether to follow redirects.
            timeout: Request timeout.
            extensions: Dictionary of ASGI extensions.

        Returns:
            An HTTPX Response.
        """
        return await AsyncClient.put(
            self,
            url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    async def patch(
        self,
        url: "URLTypes",
        *,
        content: Optional["RequestContent"] = None,
        data: Optional["RequestData"] = None,
        files: Optional["RequestFiles"] = None,
        json: Optional[Any] = None,
        params: Optional["QueryParamTypes"] = None,
        headers: Optional["HeaderTypes"] = None,
        cookies: Optional["CookieTypes"] = None,
        auth: Union["AuthTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        follow_redirects: Union[bool, "UseClientDefault"] = USE_CLIENT_DEFAULT,
        timeout: Union["TimeoutTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        extensions: Optional[Mapping[str, Any]] = None,
    ) -> Response:
        """Sends a PATCH request.

        Args:
            url: URL or path for the request.
            content: Request content.
            data: Form encoded data.
            files: Multipart files to send.
            json: JSON data to send.
            params: Query parameters.
            headers: Request headers.
            cookies: Request cookies.
            auth: Auth headers.
            follow_redirects: Whether to follow redirects.
            timeout: Request timeout.
            extensions: Dictionary of ASGI extensions.

        Returns:
            An HTTPX Response.
        """
        return await AsyncClient.patch(
            self,
            url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    async def delete(
        self,
        url: "URLTypes",
        *,
        params: Optional["QueryParamTypes"] = None,
        headers: Optional["HeaderTypes"] = None,
        cookies: Optional["CookieTypes"] = None,
        auth: Union["AuthTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        follow_redirects: Union[bool, "UseClientDefault"] = USE_CLIENT_DEFAULT,
        timeout: Union["TimeoutTypes", "UseClientDefault"] = USE_CLIENT_DEFAULT,
        extensions: Optional[Mapping[str, Any]] = None,
    ) -> Response:
        """Sends a DELETE request.

        Args:
            url: URL or path for the request.
            params: Query parameters.
            headers: Request headers.
            cookies: Request cookies.
            auth: Auth headers.
            follow_redirects: Whether to follow redirects.
            timeout: Request timeout.
            extensions: Dictionary of ASGI extensions.

        Returns:
            An HTTPX Response.
        """
        return await AsyncClient.delete(
            self,
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    async def get_session_data(self) -> Dict[str, Any]:
        """Get session data.

        Returns:
            A dictionary containing session data.

        Examples:
            .. code-block: python

                from starlite import Starlite, post
                from starlite.middleware.session.memory_backend import MemoryBackendConfig

                session_config = MemoryBackendConfig()


                @post(path="/test")
                def set_session_data(request: Request) -> None:
                    request.session["foo"] == "bar"


                app = Starlite(
                    route_handlers=[set_session_data], middleware=[session_config.middleware]
                )

                async with AsyncTestClient(app=app, session_config=session_config) as client:
                    await client.post("/test")
                    assert await client.get_session_data() == {"foo": "bar"}

        """
        return await super()._get_session_data()

    async def set_session_data(self, data: Dict[str, Any]) -> None:
        """Set session data.

        Args:
            data: Session data

        Returns:
            None

        Examples:
            .. code-block: python

                from starlite import Starlite, get
                from starlite.middleware.session.memory_backend import MemoryBackendConfig

                session_config = MemoryBackendConfig()


                @get(path="/test")
                def get_session_data(request: Request) -> Dict[str, Any]:
                    return request.session


                app = Starlite(
                    route_handlers=[get_session_data], middleware=[session_config.middleware]
                )

                async with AsyncTestClient(app=app, session_config=session_config) as client:
                    await client.set_session_data({"foo": "bar"})
                    assert await client.get("/test").json() == {"foo": "bar"}

        """
        return await super()._set_session_data(data)
