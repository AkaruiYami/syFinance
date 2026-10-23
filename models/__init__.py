import importlib
import pkgutil
from pathlib import Path

from .base import BaseModel

# Automatically import all modules in this package
package_dir = Path(__file__).parent

for module_info in pkgutil.iter_modules([str(package_dir)]):
    importlib.import_module(f"{__name__}.{module_info.name}")
