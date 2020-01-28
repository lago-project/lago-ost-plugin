#!/bin/bash -ex
readonly BUILDS=$PWD/automation-build
readonly EXPORTS=$PWD/exported-artifacts
readonly SPEC="lago-ovirt.spec"

BUILDDEP="dnf builddep"
echo "cleaning dnf metadata"
dnf clean metadata

echo "Installing Lago"
dnf install -y lago

echo "cleaning $BUILDS, $EXPORTS"
rm -rf "$BUILDS" "$EXPORTS"/*{.rpm,.tar.gz}
mkdir -p "$BUILDS"
mkdir -p "$EXPORTS"

make clean
make "$SPEC"

echo "installing RPM build dependencies"
$BUILDDEP -y "$SPEC"

echo "creating RPM"
make rpm OUTPUT_DIR="$BUILDS"

find "$BUILDS" \
    \( -iname \*.rpm -or -iname \*.tar.gz \) \
    -exec mv {} "$EXPORTS/" \;
