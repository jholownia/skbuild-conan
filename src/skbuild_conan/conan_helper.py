import json
import subprocess
import sys
import os
import typing
import skbuild.constants as skc
from conan.tools.files import copy

class ConanHelper:
    """
    The ConanHelper is used for installing conan dependencies automatically
    for scikit-build based packages.
    This is kind of a workaround, not a production ready tool.

    Dominik Krupke, TU Braunschweig, 2023
    """

    def __init__(self, output_folder=".conan", build_profile="default", host_profile="default", local_recipes=None, settings=None, imports=None):
        self.generator_folder = os.path.abspath(output_folder)
        self.local_recipes = local_recipes if local_recipes else []
        self.build_profile = build_profile
        self.host_profile = host_profile
        self.settings = settings if settings else {}
        self.imports = imports if imports else []
        self._check_conan_version()

    def conan_version(self):
        args = [sys.executable, "-m", "conans.conan", "-v"]
        version = subprocess.check_output(args).decode().split(" ")[-1]
        return version

    def _check_conan_version(self):
        version = self.conan_version()
        if version[0] != "2":
            raise RuntimeError(f"Conan 2 required. Current version {version}.")

    def install_config(self, config_folder):        
        cmd = f"-m conans.conan config install {config_folder}"
        subprocess.run([sys.executable, *cmd.split(" ")], check=True)

    def _conan_to_json(self, args):
        """
        Runs conan with the args and parses the output as json.
        """
        args = [sys.executable, "-m", "conans.conan"] + args
        return json.loads(subprocess.check_output(args).decode())

    def _copy_imports(self):
        conan_folder = self.generator_folder
        skbuild_folder = skc.CMAKE_BUILD_DIR()
        copied = []
        for i in imports:
            copied += copy(None, i.pattern, os.path.join(conan_folder, i.src), os.path.join(skbuild.folder, i.dst))
        return copied
        
    def install_from_paths(self, paths):
        """
        Installs all the conanfiles to local cache. Will automatically skip if the package
        is already available. Currently only works on name and version, not user or
        similar.
        """
        for path in paths:
            package_info = self._conan_to_json(["inspect", "-f", "json", path])
            conan_list = self._conan_to_json(
                ["list", "-c", "-f", "json", package_info["name"]]
            )
            package_id = f"{package_info['name']}/{package_info['version']}"
            if package_id in conan_list["Local Cache"].keys():
                print(package_info["name"], "already available.")
                continue
            cmd = (
                f"-m conans.conan create {path} -pr:b default -pr:h default"
                f" -s build_type=Release --build=missing"
            )
            subprocess.run([sys.executable, *cmd.split(" ")], check=True)

    def create_profile(self):
        # check if profile exists or create a default one automatically.
        if "default" in self._conan_to_json(["profile", "list", "-f", "json"]):
            return  # Profile already exists
        cmd = f"-m conans.conan profile detect"
        subprocess.run([sys.executable, *cmd.split(" ")], check=False, stderr=None)

    

    def install(self, path: str = ".", requirements: typing.List[str] = None, extra_args: str = None):
        """
        Running conan to get C++ dependencies
        """        
        self.create_profile()
        self.install_from_paths(self.local_recipes)

        cmd = f"-m conans.conan install"
        cmd += f" -pr:h {self.host_profile} -pr:b {self.build_profile}"
        if requirements:
            # requirements passed from Python directly
            for req in requirements:
                cmd += f" --requires {req}"
        else:
            # requirements from conanfile
            cmd += f" {path}"
        for key, val in self.settings.items():
            cmd += f" -s {key}={val}"
        cmd += " --build=missing"
        # redirecting the output to a subfolder. The `cmake_args` makes sure
        # that CMake still finds it.
        cmd += f" --output-folder={self.generator_folder}"
        # Making sure  the right generators are used.
        #cmd += f" -g CMakeDeps -g CMakeToolchain"
        if extra_args:
            cmd += f" {extra_args}"

        subprocess.run([sys.executable, *cmd.split(" ")], check=True)
        copied = self._copy_imports()
        print("Copied files: ", copied)
        

    def cmake_args(self):
        """
        Has to be appended to `cmake_args` in `setup(...)`.
        """
        toolchain_path = os.path.abspath(
            f"{self.generator_folder}/build/conan_toolchain.cmake"
        )
        if not os.path.exists(toolchain_path):
            raise RuntimeError(
                "conan_toolchain.cmake not found. Make sure you"
                " specified 'CMakeDeps' and 'CMakeToolchain' as"
                " generators."
            )
        return [
            f"-DCMAKE_TOOLCHAIN_FILE={toolchain_path}",
            f"-DCMAKE_PREFIX_PATH={self.generator_folder}/build",
        ]
