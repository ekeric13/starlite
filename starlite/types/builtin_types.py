# nopycln: file

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Type, Union

    from typing_extensions import TypeAlias, TypedDict

    from starlite.types.protocols import DataclassProtocol


__all__ = [
    "DataclassClass",
    "DataclassClassOrInstance",
    "NoneType",
    "TypedDictClass",
]

DataclassClass: "TypeAlias" = "Type[DataclassProtocol]"

DataclassClassOrInstance: "TypeAlias" = "Union[DataclassClass, DataclassProtocol]"

NoneType = type(None)

# mypy issue: https://github.com/python/mypy/issues/11030
TypedDictClass: "TypeAlias" = "Type[TypedDict]"  # type:ignore[valid-type]
