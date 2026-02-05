class TerrainTileError(Exception):
    """Base class for exceptions in this module."""


class InvalidGeometryError(ValueError):
    """Exception raised for invalid geometries."""


class MissingDimensionError(ValueError):
    """Exception raised for missing dimensions in geometries."""
