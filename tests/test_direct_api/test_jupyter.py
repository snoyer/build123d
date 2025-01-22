"""
build123d direct api tests

name: test_jupyter.py
by:   Gumyr
date: January 21, 2025

desc:
    This python module contains tests for the build123d project.

license:

    Copyright 2025 Gumyr

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

"""

import unittest

from build123d.geometry import Vector
from build123d.jupyter_tools import to_vtkpoly_string, display
from build123d.topology import Solid
from tests.base_test import DirectApiTestCase


class TestJupyter(DirectApiTestCase):
    def test_repr_javascript(self):
        shape = Solid.make_box(1, 1, 1)

        # Test no exception on rendering to js
        js1 = shape._repr_javascript_()

        assert "function render" in js1

    def test_display_error(self):
        with self.assertRaises(AttributeError):
            display(Vector())

        with self.assertRaises(ValueError):
            to_vtkpoly_string("invalid")

        with self.assertRaises(ValueError):
            display("invalid")


if __name__ == "__main__":
    import unittest

    unittest.main()
