import sys
import typing
import skbuild

from .conan_helper import ConanHelper


def setup(
    conanfile: str = ".",
    conan_recipes: typing.List[str] = None,
    conan_requirements: typing.List[str] = None,
    conan_output_folder=".conan",
    conan_config_folder: str = None,
    conan_build_profile="default",
    conan_host_profile="default",
    conan_profile_settings: typing.Dict = None,
    conan_extra_args: str = None,
    wrapped_setup: typing.Callable = skbuild.setup,
    cmake_args: typing.List[str] = None,
    **kwargs
):
    """
    An extended setup that takes care of conan dependencies.

    :param conanfile: Path to the folder with the conanfile.[py|txt]. By default the root
                        is assumed. The conanfile can be used to define the dependencies.
                        Alternatively, you can also use `conan_requirements` to define
                        the conan dependencies without a conanfile. This option is
                        exclusive. If you define `conan_requirements`, this option is
                        ignored.

    :param conan_recipes: List of paths to further conan recipes. The conan package index
        is far from perfect, so often you need to build your own recipes. You don't
        always want to upload those, so this argument gives you the option to integrate
        local recipes. Just the path to the folder containing the `conanfile.py`.

    :param conan_requirements: Instead of providing a conanfile, you can simply state
        the dependencies here. E.g. `["fmt/[>=10.0.0]"]` to add fmt in version >=10.0.0.

    :param conan_profile_settings: Overwrite conan profile settings. Sometimes necessary
        because of ABI-problems, etc.

    :param wrapped_setup: The setup-method that is going to be wrapped. This would allow
        you to extend already extended setup functions. By default, it is the `setup`
        of `skbuild`, which extends the `setup` of `setuptools`.

    :param conan_output_folder: The folder where conan will write the generated files.
        No real reason to change it unless the default creates conflicts with some other
        tool.

    :param conan_build_profile: Conan build profile to use.

    :param conan_host_profile: Conan host profile to use.

    :param conan_config_folder: The folder containing conan configuration files like profiles,
        remotes and settings to be installed with `conan config install` command.

    :param cmake_args: This is actually an argument of `skbuild` but we will extend it.
        It hands cmake custom arguments. We use it to tell cmake about the conan modules.

    :param conan_extra_args: Additional arguments to pass to conan install.

    :param kwargs: The arguments for the underlying `setup`. Please check the
        documentation of `skbuild` and `setuptools` for this.

    :return: The returned values of the wrapped setup.
    """

    # Workaround for mismatching ABI with GCC on Linux
    conan_profile_settings = conan_profile_settings if conan_profile_settings else {}
    if sys.platform == "linux" and "compiler.libcxx" not in conan_profile_settings:
        print('Using workaround and setting "compiler.libcxx=libstdc++11"')
        conan_profile_settings = conan_profile_settings.copy()
        conan_profile_settings["compiler.libcxx"]= "libstdc++11"

    conan_helper = ConanHelper(
        output_folder=conan_output_folder,
        local_recipes=conan_recipes,
        build_profile=conan_build_profile,
        host_profile=conan_host_profile,
        settings=conan_profile_settings,
    )

    if conan_config_folder:
        conan_helper.install_config(conan_config_folder)

    conan_helper.install(path=conanfile, requirements=conan_requirements, extra_args=conan_extra_args)
    cmake_args = cmake_args if cmake_args else []
    cmake_args += conan_helper.cmake_args()
    return wrapped_setup(cmake_args=cmake_args, **kwargs)
