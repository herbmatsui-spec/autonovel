"""Prompt compiler service – renders axis selections into a single LLM prompt."""
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from src.schemas.axis import PromptContract, AxisType

_TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "prompts" / "templates" / "compiler"

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(),
    trim_blocks=True,
    lstrip_blocks=True,
)


def compile_prompt(contract: PromptContract) -> str:
    """Render the Jinja2 template for the selected output_mode."""
    template_name = f"{contract.output_mode}.j2"
    try:
        template = _env.get_template(template_name)
    except Exception:
        # fallback to generic template
        template = _env.get_template("novel.j2")

    # Build a plain dict for Jinja2
    axis_dict = {}
    for axis_type in AxisType:
        axis = contract.axes.get(axis_type)
        if axis:
            axis_dict[axis_type.value] = {"value": axis.value, "locked": axis.locked, "default": axis.default}
        else:
            axis_dict[axis_type.value] = {"value": None, "locked": False, "default": None}

    context = {"axis": axis_dict, "output_mode": contract.output_mode}
    return template.render(**context)