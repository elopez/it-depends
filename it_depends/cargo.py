import json
from os import chdir, getcwd
from pathlib import Path
import shutil
import subprocess
from typing import Iterable, Optional

from semantic_version.base import Always, BaseSpec

from .dependencies import (
    ClassifierAvailability, Dependency, DependencyClassifier, DependencyResolver, Package, PackageCache, SimpleSpec,
    SourcePackage, SourceRepository, Version
)


@BaseSpec.register_syntax
class CargoSpec(SimpleSpec):
    SYNTAX = 'cargo'

    class Parser(SimpleSpec.Parser):
        @classmethod
        def parse(cls, expression):
            # The only difference here is that cargo clauses can have whitespace, so we need to strip each block:
            blocks = [b.strip() for b in expression.split(',')]
            clause = Always()
            for block in blocks:
                if not cls.NAIVE_SPEC.match(block):
                    raise ValueError("Invalid simple block %r" % block)
                clause &= cls.parse_block(block)

            return clause

    def __str__(self):
        # remove the whitespace to canonicalize the spec
        return ",".join(b.strip() for b in self.expression.split(','))


def get_dependencies(cargo_package_path: str, check_for_cargo: bool = True) -> Iterable[Package]:
    if check_for_cargo and shutil.which("cargo") is None:
        raise ValueError("`cargo` does not appear to be installed! Make sure it is installed and in the PATH.")

    orig_dir = getcwd()
    chdir(cargo_package_path)

    try:
        metadata = json.loads(subprocess.check_output(["cargo", "metadata", "--format-version", "1"]))
    finally:
        chdir(orig_dir)

    for package in metadata["packages"]:
        yield Package(
            name=package["name"],
            version=Version.coerce(package["version"]),
            source="cargo",
            dependencies=[
                Dependency(
                    package=dep["name"],
                    semantic_version=CargoClassifier.parse_spec(dep["req"])
                )
                for dep in package["dependencies"]
            ]
        )


class CargoClassifier(DependencyClassifier):
    name = "cargo"
    description = "classifies the dependencies of Rust packages using `cargo metadata`"

    def is_available(self) -> ClassifierAvailability:
        if shutil.which("cargo") is None:
            return ClassifierAvailability(False, "`cargo` does not appear to be installed! "
                                                 "Make sure it is installed and in the PATH.")
        return ClassifierAvailability(True)

    @classmethod
    def parse_spec(cls, spec: str) -> CargoSpec:
        return CargoSpec(spec)

    def can_classify(self, repo: SourceRepository) -> bool:
        return (repo.path / "Cargo.toml").exists()

    def classify(self, repo: SourceRepository, cache: Optional[PackageCache] = None):
        raise NotImplementedError("TODO")
        return DependencyResolver(get_dependencies(path, check_for_cargo=False), source=self, cache=cache)
