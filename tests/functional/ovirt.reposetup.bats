#!/usr/bin/env bats
load common
load ovirt_common
load helpers
load env_setup

FIXTURES="$FIXTURES/ovirt.reposetup"
WORKDIR="$FIXTURES"/.lago
PREFIX="$WORKDIR/default"
TEMP_REPOS="${FIXTURES}/temp-repo"
REPOSYNC="${FIXTURES}/reposync-config.repo"
EXTRA_SOURCES="${FIXTURES}/extra-sources"

unset LAGO__START__WAIT_SUSPEND

@test "ovirt.runtest: setup" {
    local repo_path
    local repo_name
    local topdir="${FIXTURES}/dummy-rpm"
    local versions=("0.1.0" "0.2.0")

    rm -rf "$TEMP_REPOS" "$REPOSYNC" "$topdir"
    mkdir "$TEMP_REPOS"

    # Create dummy RPMs and repos
    for version in "${versions[@]}"; do
        # Create dummy RPM
        helpers.run_ok rpmbuild \
            -bb \
            --define "_topdir $topdir" \
            --define "__version $version" \
            "${FIXTURES}/dummy-rpm.spec"

        # Create a repo for the dumy RPM
        repo_name="dummy-${version}"
        repo_path="${TEMP_REPOS}/${repo_name}"
        mkdir "$repo_path"
        find "$topdir" \
            -name "*.rpm" \
            -exec mv {} "$repo_path" \;
        helpers.run_ok createrepo "$repo_path"

        # Add the the dummy repo to the reposync-config
        cat >> "$REPOSYNC" <<EOF
[${repo_name}]
name=$repo_name
baseurl=file:/${repo_path}

EOF
    done

    # Create extra-sources file with the lowest version of the dummy RPM
    echo \
        "${TEMP_REPOS}/$(ls "$TEMP_REPOS" | sort | head -n1)" \
        > "$EXTRA_SOURCES"

    # Create a Lago env
    local suite="$FIXTURES"/suite.yaml

    rm -rf "$WORKDIR"
    cd "$FIXTURES"
    helpers.run_ok "$LAGOCLI" \
        init \
        "$suite"
    helpers.run_ok "$LAGOCLI" start
}


@test "ovirt.runtest: simple runtest" {
    cd "$FIXTURES"
    #helpers.run_ok "$LAGOCLI" ovirt reposetup \

#    for testfile in "${testfiles[@]}"; do
#        helpers.run_ok "$LAGOCLI" ovirt runtest "$FIXTURES/$testfile"
#        helpers.contains "$output" "${testfile%.*}.test_pass"
#        helpers.is_file "$PREFIX/$testfile.junit.xml"
#        helpers.contains \
#            "$(cat $PREFIX/$testfile.junit.xml)" \
#            'errors="0"'
#    done
}

@test "ovirt.runtest: teardown" {
    if common.is_initialized "$WORKDIR"; then
        pushd "$FIXTURES"
        helpers.run_ok "$LAGOCLI" destroy -y --all-prefixes
        popd
    fi
    env_setup.destroy_domains
    env_setup.destroy_nets
}
