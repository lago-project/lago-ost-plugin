###############
Installing lago-ost-plugin
###############

RPM Based - Fedora 24+ / CentOS 7
====================================

1. Add the following repositories to a new file at
   ``/etc/yum.repos.d/lago.repo`` (If you installed lago before,
   the `lago` repository should be already configured):

   For Fedora:

   .. code:: ini

    [lago]
    baseurl=http://resources.ovirt.org/repos/lago/stable/0.0/rpm/fc$releasever
    name=Lago
    enabled=1
    gpgcheck=0

    [ovirt-ci-tools]
    baseurl=http://resources.ovirt.org/repos/ci-tools/fc$releasever
    name=oVirt CI Tools
    enabled=1
    gpgcheck=0

   For CentOS:

   .. code:: ini

    [lago]
    baseurl=http://resources.ovirt.org/repos/lago/stable/0.0/rpm/el$releasever
    name=Lago
    enabled=1
    gpgcheck=0

    [ovirt-ci-tools]
    baseurl=http://resources.ovirt.org/repos/ci-tools/el$releasever
    name=oVirt CI Tools
    enabled=1
    gpgcheck=0


   *For CentOS only*, you will need **EPEL** repository:

       .. code:: bash

           $ sudo yum install epel-release



2. Install lago-ovirt (for Fedora use ``dnf`` instead):

   .. code:: bash

       $ sudo yum install lago-ovirt

3.  Install ovirt-engine-sdk-python==4.2.7

    pycurl is a dependency required when installing ovirt-engine-sdk-python
    
    An error message received:
    ImportError: pycurl: libcurl link-time ssl backend (openssl) is different from
    compile-time ssl backend (none/other)

    Steps to fix the problem:
        % pip remove pycurl
        % pip uninstall pycurl

        % pip install --compile --no-cache-dir  --with-openssl pycurl
        or
        % pip install --compile --no-cache-dir  --with-nss pycurl
