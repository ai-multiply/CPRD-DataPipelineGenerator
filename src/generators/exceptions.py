class GeneratorError(Exception):
    """Base exception for all generator-related errors."""
    pass

class InputValidationError(GeneratorError):
    """Raised when input validation fails."""
    pass

class FileNotFoundError(GeneratorError):
    """Raised when required input files are not found."""
    pass

class ConfigurationError(GeneratorError):
    """Raised when configuration is invalid."""
    pass
