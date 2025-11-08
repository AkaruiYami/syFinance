import importlib
import pkgutil
import inspect
from pathlib import Path

from .base import BaseModel

# Automatically import all modules in this package
package_dir = Path(__file__).parent

for module_info in pkgutil.iter_modules([str(package_dir)]):
    module_name = module_info.name
    if module_name == "__init__":
        continue
    # Import the module dynamically
    module = importlib.import_module(f"{__name__}.{module_name}")

    # Register all classes that inherit from BaseModel
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if issubclass(obj, BaseModel) and obj is not BaseModel:
            # Optionally just accessing the class triggers BaseModel subclass registration
            pass

# Now BaseModel.get_all_tables() should include all models automatically
