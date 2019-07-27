import sys
from pathlib import Path
import os
import asyncio
# ---- the compatibility with command line

# ---- import Config for get access to all configuration
# from Core.ConfigSystem.Bases import ConfigGlobals

# Do not pass if main

if __name__ == "__main__":
    print("Do not run HaloNet.py directly!")
    sys.exit()

# Scan for entities and standard directories (/System/..., /Common/..., /Entities/*/...)
workspace = os.getcwd()
os.chdir(str(Path(sys.argv[0]).parent))
parent_dir = str(Path(sys.argv[0]).parent.parent)
if parent_dir != ".":
    entity_dirs = os.listdir(parent_dir + "/Entities/")
else:
    parent_dir = str(Path(__file__).parent.parent)
    entity_dirs = os.listdir(parent_dir + "/Entities/")
for entity_dir in entity_dirs:
    if not entity_dir.startswith("__"):
        sys.path.append(parent_dir + "/Entities/" + entity_dir)
sys.path.append(parent_dir + "/System")
sys.path.append(parent_dir + "/Common")

from Core.ConfigSystem.Bases import ConfigGlobals

# Import the configuration override (top over system)
import Config


# Try import the last configuration override (top over standard)
try:
    import ConfigDefault_override
except ImportError:
    pass

# import user defined symbols (Types, Storages)
import Types
import Storages

from Core import WARN_MSG
from Core.CommandLine import CommandLine
from Core.ConfigSystem.GeneratorConfig import ConfigurationGenerator
from Core.Globals import Globals
from Core.CodeGen import CodeGen

# todo: not used for now
# from Core.Common.PatchNoneType import run_NoneType_patch
# run_NoneType_patch()

# Check the color patterns enabled (for some consoles need)
if CommandLine.get_arguments().no_color_patterns:
    import Core.Common.Platform
    Core.Common.Platform.color_patterns_enabled = False

# Try enable uvloop
try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    WARN_MSG("Unable to import 'uvloop'. At this moment uvloop works only on *nixes operation systems. Program will work slower")

# Let's generate metadata for all services (not for child processes)
if not CommandLine.get_arguments().is_child_process:
    CodeGen(generate_only_config=True)

# Remember signature
Globals.generator_signature = ConfigurationGenerator().generator_signature

apps_mapping = Config.AppConfig.context_by_name

# Check we're not in generator
if not Globals.IsInGenerator:
    # in this case reach all working directories
    workspace = str(Path(os.getcwd()).parent)
    Globals.workspace = workspace
    script_name = str(os.path.basename(sys.argv[0])).replace(".py", "")

    removed_paths = list()
    for path in sys.path:
        if path.startswith(workspace):
            p = path.replace(workspace, "")[1:]
            if p.startswith("Entities"):
                removed_paths.append(path)

    if script_name in apps_mapping:
        for rmp in removed_paths:
            if not rmp.endswith(apps_mapping[script_name]):
                sys.path.remove(rmp)

        context_name = apps_mapping[script_name]
        Globals.context_name = context_name
    else:
        WARN_MSG(f"There is no config for {script_name}")
    import Core.LocalDatatypes


    if not CommandLine.get_arguments().silent:
        print("Welcome to HaloNet services!")

# setup generated info and version
ConfigurationGenerator().load_generated_info()
Globals.generator_signature = ConfigurationGenerator().generator_signature
Globals.version = ConfigGlobals.Version

# A now HaloNet imported, the service can be successfully started
Globals.HaloNet_imported = True