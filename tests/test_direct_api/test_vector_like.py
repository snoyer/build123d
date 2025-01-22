"""
build123d direct api tests

name: test_vector_like.py
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

from build123d.geometry import Axis, Vector
from build123d.topology import Vertex
from tests.base_test import DirectApiTestCase


class TestVectorLike(DirectApiTestCase):
    """Test typedef"""

    def test_axis_from_vertex(self):
        axis = Axis(Vertex(1, 2, 3), Vertex(0, 0, 1))
        self.assertVectorAlmostEquals(axis.position, (1, 2, 3), 5)
        self.assertVectorAlmostEquals(axis.direction, (0, 0, 1), 5)

    def test_axis_from_vector(self):
        axis = Axis(Vector(1, 2, 3), Vector(0, 0, 1))
        self.assertVectorAlmostEquals(axis.position, (1, 2, 3), 5)
        self.assertVectorAlmostEquals(axis.direction, (0, 0, 1), 5)

    def test_axis_from_tuple(self):
        axis = Axis((1, 2, 3), (0, 0, 1))
        self.assertVectorAlmostEquals(axis.position, (1, 2, 3), 5)
        self.assertVectorAlmostEquals(axis.direction, (0, 0, 1), 5)


if __name__ == "__main__":
    import unittest

    unittest.main()
