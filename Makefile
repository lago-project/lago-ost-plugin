VERSION=$(shell scripts/version_manager.py . version)
NAME=lago-ovirt
TAR_FILE=${NAME}-${VERSION}.tar
TARBALL_FILE=${TAR_FILE}.gz
SPECFILE=${NAME}.spec
# this is needed to use the libs from venv

OUTPUT_DIR=$(CURDIR)
RPM_DIR=${OUTPUT_DIR}/rpmbuild
DIST_DIR=${OUTPUT_DIR}/dist

TAR_DIST_LOCATION=${DIST_DIR}/${TAR_FILE}
TARBALL_DIST_LOCATION=${DIST_DIR}/${TARBALL_FILE}

.PHONY: build rpm srpm ${TARBALL_DIST_LOCATION} check-local dist check ${SPECFILE} docs fullchangelog changelog python-sdist add-extra-files-sdist clean distclean

changelog:
	echo Creating RPM compatible ChangeLog \
	&& ( \
		scripts/version_manager.py . changelog \
	) > ChangeLog \
	|| ( \
		echo Failed to generate RPM ChangeLog >&2 \
		&& exit 1 \
	)

fullchangelog:
	@if test -d ".git"; then \
		echo Creating FullChangeLog \
		&& ( \
			echo '# Generated by Makefile. Do not edit.'; echo; \
			git log --stat \
		) > FullChangeLog \
		|| ( \
			echo Failed to generate FullChangeLog >&2 \
		); \
	else \
		echo A git clone is required to generate a FullChangeLog >&2; \
	fi

${SPECFILE}: ${SPECFILE}.in changelog
	sed -e "s/@@VERSION@@/${VERSION}/g" \
		${SPECFILE}.in > $@; \
	cat ChangeLog >> $@

build:
	OVIRTLAGO_VERSION=${VERSION} python setup.py build

check: check-local

check-local:
	@# Check SSL backend for pycurl
	@if curl-config --configure | grep -q '\-\-with\-nss'; then \
		export PYCURL_SSL_LIBRARY=nss; \
	else \
		export PYCURL_SSL_LIBRARY=openssl; \
	fi; \
	tox -r -e py27

dist: ${TARBALL_DIST_LOCATION}

python-sdist:
	LAGO_VERSION=${VERSION} python2 setup.py sdist --dist-dir ${DIST_DIR}

add-extra-files-sdist: changelog fullchangelog
	gunzip ${TARBALL_DIST_LOCATION}
	tar rvf ${TAR_DIST_LOCATION} \
		FullChangeLog \
		ChangeLog
	gzip ${TAR_DIST_LOCATION}

${TARBALL_DIST_LOCATION}: python-sdist add-extra-files-sdist

srpm: dist ${SPECFILE}
	rpmbuild \
		--define "_topdir ${RPM_DIR}" \
		--define "_sourcedir ${DIST_DIR}" \
		-of \
		${SPECFILE}

rpm: dist ${SPECFILE}
	rpmbuild \
		--define "_topdir ${RPM_DIR}" \
		--define "_sourcedir ${DIST_DIR}" \
		-ba \
		${SPECFILE}

clean:
	python2 setup.py clean
	rm -rf ${DIST_DIR}
	rm -rf ${RPM_DIR}
	rm -rf build "$(REPO_LOCAL_REL_PATH)"
	rm -rf docs/_build
	rm -rf htmlcov
	find -name __pycache__ -type d | xargs -r rm -r
	find -name flake8.txt -exec rm {} \;
	rm -f ${SPECFILE}
	rm -f AUTHORS
	rm -f ChangeLog
	rm -f FullChangeLog
	rm -f .coverage
	rm -f coverage.xml
	rm -f lago.junit.xml
	rm -f docs/_static/ChangeLog.txt
	rm -f docs/ovirtlago.rst

distclean: clean
	rm -rf .eggs
	rm -rf .tox
	rm -rf lago_ovirt.egg-info

docs:
	tox -r -e docs

