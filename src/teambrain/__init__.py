from importlib.metadata import version

# Lue depuis les métadonnées du paquet : pyproject.toml reste la seule source de la version
__version__ = version("teambrain")
