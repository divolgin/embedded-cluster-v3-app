#!/usr/bin/env python3
"""Build release artifacts from checked-in source and validate Helm builders."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
HELM = os.environ.get("HELM", "helm")


def run(*args):
    subprocess.run(args, cwd=ROOT, check=True)


def chart_specs():
    for path in sorted((ROOT / "specs").glob("*.yaml")):
        for document in yaml.safe_load_all(path.read_text()):
            if document and document.get("kind") == "HelmChart":
                yield document["spec"]


def generate():
    # Build in a temporary directory so failure does not replace a usable release.
    with tempfile.TemporaryDirectory(prefix="ec-app-") as directory:
        output = Path(directory)
        for path in (ROOT / "specs").glob("*.yaml"):
            shutil.copy2(path, output / path.name)
        for spec in chart_specs():
            name = spec["chart"]["name"]
            version = str(spec["chart"]["chartVersion"])
            source = ROOT / "charts" / name
            archive_name = f"{name}-{version}.tgz"
            if source.is_dir():
                metadata = yaml.safe_load((source / "Chart.yaml").read_text())
                if metadata["name"] != name or str(metadata["version"]) != version:
                    raise ValueError(f"Chart metadata disagrees with spec: {name}")
                if metadata.get("dependencies"):
                    if not (source / "Chart.lock").is_file():
                        raise ValueError(f"Missing dependency lock: {name}")
                    dependencies = source / "charts"
                    if dependencies.exists():
                        shutil.rmtree(dependencies)
                    run(HELM, "dependency", "build", str(source), "--skip-refresh")
                run(HELM, "package", str(source), "--destination", str(output))
            else:
                shutil.copy2(ROOT / "vendor" / archive_name, output / archive_name)
            with tarfile.open(output / archive_name) as archive:
                metadata = yaml.safe_load(archive.extractfile(f"{name}/Chart.yaml"))
                if metadata["name"] != name or str(metadata["version"]) != version:
                    raise ValueError(f"Packaged chart disagrees with spec: {name}")
        destination = ROOT / "manifests"
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(output, destination)
    # Local Replicated lint discovers unpacked charts, rather than .tgz files.
    unpacked = ROOT / ".build" / "velero"
    if unpacked.exists():
        shutil.rmtree(unpacked)
    with tarfile.open(ROOT / "vendor" / "velero-12.1.0.tgz") as archive:
        archive.extractall(ROOT / ".build", filter="data")
    print("Generated manifests/", flush=True)


def lint():
    for spec in chart_specs():
        name = spec["chart"]["name"]
        version = spec["chart"]["chartVersion"]
        archive = ROOT / "manifests" / f"{name}-{version}.tgz"
        # EC evaluates the template functions at install time. Builder values
        # are the static values used to discover images for this release.
        with tempfile.TemporaryDirectory(prefix="ec-lint-") as directory:
            values = Path(directory) / "values.yaml"
            values.write_text(yaml.safe_dump(spec.get("builder", {})))
            run(HELM, "lint", str(archive), "--values", str(values))
            rendered = subprocess.check_output(
                [HELM, "template", spec.get("releaseName", name), str(archive),
                 "--namespace", spec.get("namespace", "default"),
                 "--values", str(values)], cwd=ROOT, text=True,
            )
            list(yaml.safe_load_all(rendered))
            print(f"Rendered and parsed {name}", flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("generate", "lint"):
        raise SystemExit("Usage: manifests.py generate|lint")
    {"generate": generate, "lint": lint}[sys.argv[1]]()
