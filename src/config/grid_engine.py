from dataclasses import dataclass
from typing import Dict

@dataclass
class GridEngineConfig:
    cpus: int
    memory: str
    runtime: str

    @classmethod
    def from_dict(cls, config: Dict) -> 'GridEngineConfig':
        """Create GridEngineConfig from dict."""
        return cls(
            cpus=config.get('cpus', 1),
            memory=config.get('memory', '4G'),
            runtime=config.get('runtime', '1:0:0')
        )

    def validate(self):
        """Validate grid engine configuration."""
        if not isinstance(self.cpus, int) or self.cpus < 1:
            raise ValueError(f"Invalid CPU count: {self.cpus}")
        if not isinstance(self.memory, str) or not self.memory.endswith(('G', 'M')):
            raise ValueError(f"Invalid memory specification: {self.memory}")
        if not isinstance(self.runtime, str) or not len(self.runtime.split(':')) == 3:
            raise ValueError(f"Invalid runtime format: {self.runtime}")
