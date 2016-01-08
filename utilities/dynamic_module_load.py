import imp
import os
import inspect


def load_module_from_file(file_path):
    py_mod = None

    (mod_name, file_ext) = os.path.splitext(os.path.split(file_path)[-1])

    if file_ext.lower() == '.py':
        py_mod = imp.load_source(mod_name, file_path)

    elif file_ext.lower() == '.pyc':
        py_mod = imp.load_compiled(mod_name, file_path)

    return py_mod


def load_modules_from_folder(folder_path, load_compiled=False):

    modules = []

    file_names = os.listdir(folder_path)

    for file_name in file_names:
        if file_name == "__init__.py":
            continue
        if not load_compiled and file_name.lower().endswith(".pyc"):
            continue

        module = load_module_from_file( os.path.join(folder_path, file_name) )

        if module is not None:
            # print "Found module:", file_name, module
            modules.append(module)

    return modules


def get_classes_from_folder(folder_path):
    folder_classes = []

    modules = load_modules_from_folder(folder_path)

    for module in modules:
        module_classes = inspect.getmembers(module, inspect.isclass)
        for new_class in module_classes:

            # Only grab classes defined in this module and that end with "Plugin"
            if inspect.getmodule(new_class[1]).__name__ == module.__name__:
                folder_classes.append(new_class)
                # print "Found class:", new_class

    return folder_classes
