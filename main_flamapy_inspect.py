import importlib
import inspect
import pkgutil

import flamapy.metamodels.fm_metamodel as fm_package

print("PACKAGE:", fm_package.__file__)
print("\nMODULES AND CLASSES:")

for module_info in pkgutil.walk_packages(
    fm_package.__path__,
    prefix=f"{fm_package.__name__}.",
):
    try:
        module = importlib.import_module(module_info.name)
    except Exception as error:
        print(f"\n{module_info.name}: IMPORT ERROR: {error}")
        continue

    classes = [
        (name, cls)
        for name, cls in inspect.getmembers(module, inspect.isclass)
        if cls.__module__ == module.__name__
    ]

    if classes:
        print(f"\n[{module_info.name}]")

        for name, cls in classes:
            try:
                signature = inspect.signature(cls)
            except (TypeError, ValueError):
                signature = "(signature unavailable)"

            print(f"  {name}{signature}")