from abc import ABC, abstractmethod
from typing import Dict, Any
import jinja2
import logging
from pathlib import Path

class BaseGenerator(ABC):
    def __init__(self, template_name: str, logger: logging.Logger):
        self.template_name = template_name
        self.logger = logger
        self.template_env = self._setup_template_environment()

    def _setup_template_environment(self) -> jinja2.Environment:
        """Setup Jinja2 template environment."""
        template_dir = Path(__file__).parent.parent.parent / 'templates'
        return jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(template_dir)),
            trim_blocks=True,
            lstrip_blocks=True
        )

    @abstractmethod
    def validate_inputs(self, config: Dict[str, Any]):
        """Validate inputs required for this generator."""
        pass

    @abstractmethod
    def generate(self, config: Dict[str, Any]) -> str:
        """Generate the script content."""
        pass

    def _render_template(self, **kwargs) -> str:
        """Render the template with provided arguments."""
        template = self.template_env.get_template(f"{self.template_name}.sh.j2")
        return template.render(**kwargs)
