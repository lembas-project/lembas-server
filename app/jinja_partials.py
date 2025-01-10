from collections.abc import Callable
from functools import partial
from typing import TYPE_CHECKING, Any

from markupsafe import Markup as Markup

if TYPE_CHECKING:
    from fastapi.templating import Jinja2Templates

__all__ = [
    "register_starlette_extensions",
]


def register_starlette_extensions(templates: "Jinja2Templates") -> None:
    def render_partial(
        template_name: str,
        renderer: Callable[..., Any],
        markup: bool = True,
        **data: Any,
    ) -> Markup | str:
        if markup:
            return Markup(renderer(template_name, **data))

        return renderer(template_name, **data)

    def renderer(template_name: str, **data: Any) -> str:
        return templates.get_template(template_name).render(**data)

    templates.env.globals.update(render_partial=partial(render_partial, renderer=renderer))
