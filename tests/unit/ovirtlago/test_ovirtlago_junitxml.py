#
# Copyright 2017 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA
#
# Refer to the README and COPYING files for full details of the license
#
import pytest

from ovirtlago import prefix


class TestJunitXMLdir(object):
    @pytest.mark.parametrize(
        "default_dir, default_file, junitxml_file, expect",
        [
            (
                '/home/default', 'test01.py.junit.xml', 'foo.xml',
                '/home/default/foo.xml'
            ),
            (
                '/home/default', 'test01.py.junit.xml', 'foo',
                '/home/default/foo'
            ),
            (
                '/home/default', 'test01.py.junit.xml', '/home/xxxx',
                '/home/xxxx'
            ),
            (
                '/home/default', 'test01.py.junit.xml', '/home/xxxx/',
                '/home/xxxx/test01.py.junit.xml'
            ),
            (
                '/home/default', 'test01.py.junit.xml', '',
                '/home/default/test01.py.junit.xml'
            ),
        ],
    )
    def test_filename(self, default_dir, default_file, junitxml_file, expect):
        assert prefix._create_output_filename(
            default_dir, default_file, junitxml_file
        ) == expect
