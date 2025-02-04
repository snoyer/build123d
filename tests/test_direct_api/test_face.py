"""
build123d imports

name: test_face.py
by:   Gumyr
date: January 22, 2025

desc:
    This python module contains tests for the build123d project.

license:

    Copyright 2025 Gumyr

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

"""

import math
import os
import platform
import random
import unittest

from build123d.build_common import Locations
from build123d.build_enums import Align, CenterOf, GeomType
from build123d.build_line import BuildLine
from build123d.build_part import BuildPart
from build123d.build_sketch import BuildSketch
from build123d.exporters3d import export_stl
from build123d.geometry import Axis, Location, Plane, Pos, Vector
from build123d.importers import import_stl
from build123d.objects_curve import Polyline
from build123d.objects_part import Box, Cylinder
from build123d.objects_sketch import Rectangle, RegularPolygon
from build123d.operations_generic import fillet
from build123d.operations_part import extrude
from build123d.operations_sketch import make_face
from build123d.topology import Edge, Face, Solid, Wire


class TestFace(unittest.TestCase):
    def test_make_surface_from_curves(self):
        bottom_edge = Edge.make_circle(radius=1, end_angle=90)
        top_edge = Edge.make_circle(radius=1, plane=Plane((0, 0, 1)), end_angle=90)
        curved = Face.make_surface_from_curves(bottom_edge, top_edge)
        self.assertTrue(curved.is_valid())
        self.assertAlmostEqual(curved.area, math.pi / 2, 5)
        self.assertAlmostEqual(
            curved.normal_at(), (math.sqrt(2) / 2, math.sqrt(2) / 2, 0), 5
        )

        bottom_wire = Wire.make_circle(1)
        top_wire = Wire.make_circle(1, Plane((0, 0, 1)))
        curved = Face.make_surface_from_curves(bottom_wire, top_wire)
        self.assertTrue(curved.is_valid())
        self.assertAlmostEqual(curved.area, 2 * math.pi, 5)

    def test_center(self):
        test_face = Face(Wire.make_polygon([(0, 0), (1, 0), (1, 1), (0, 0)]))
        self.assertAlmostEqual(test_face.center(CenterOf.MASS), (2 / 3, 1 / 3, 0), 1)
        self.assertAlmostEqual(
            test_face.center(CenterOf.BOUNDING_BOX),
            (0.5, 0.5, 0),
            5,
        )

    def test_face_volume(self):
        rect = Face.make_rect(1, 1)
        self.assertAlmostEqual(rect.volume, 0, 5)

    def test_chamfer_2d(self):
        test_face = Face.make_rect(10, 10)
        test_face = test_face.chamfer_2d(
            distance=1, distance2=2, vertices=test_face.vertices()
        )
        self.assertAlmostEqual(test_face.area, 100 - 4 * 0.5 * 1 * 2)

    def test_chamfer_2d_reference(self):
        test_face = Face.make_rect(10, 10)
        edge = test_face.edges().sort_by(Axis.Y)[0]
        vertex = edge.vertices().sort_by(Axis.X)[0]
        test_face = test_face.chamfer_2d(
            distance=1, distance2=2, vertices=[vertex], edge=edge
        )
        self.assertAlmostEqual(test_face.area, 100 - 0.5 * 1 * 2)
        self.assertAlmostEqual(test_face.edges().sort_by(Axis.Y)[0].length, 9)
        self.assertAlmostEqual(test_face.edges().sort_by(Axis.X)[0].length, 8)

    def test_chamfer_2d_reference_inverted(self):
        test_face = Face.make_rect(10, 10)
        edge = test_face.edges().sort_by(Axis.Y)[0]
        vertex = edge.vertices().sort_by(Axis.X)[0]
        test_face = test_face.chamfer_2d(
            distance=2, distance2=1, vertices=[vertex], edge=edge
        )
        self.assertAlmostEqual(test_face.area, 100 - 0.5 * 1 * 2)
        self.assertAlmostEqual(test_face.edges().sort_by(Axis.Y)[0].length, 8)
        self.assertAlmostEqual(test_face.edges().sort_by(Axis.X)[0].length, 9)

    def test_chamfer_2d_error_checking(self):
        with self.assertRaises(ValueError):
            test_face = Face.make_rect(10, 10)
            edge = test_face.edges().sort_by(Axis.Y)[0]
            vertex = edge.vertices().sort_by(Axis.X)[0]
            other_edge = test_face.edges().sort_by(Axis.Y)[-1]
            test_face = test_face.chamfer_2d(
                distance=1, distance2=2, vertices=[vertex], edge=other_edge
            )

    def test_make_rect(self):
        test_face = Face.make_plane()
        self.assertAlmostEqual(test_face.normal_at(), (0, 0, 1), 5)

    def test_length_width(self):
        test_face = Face.make_rect(8, 10, Plane.XZ)
        self.assertAlmostEqual(test_face.length, 8, 5)
        self.assertAlmostEqual(test_face.width, 10, 5)

    def test_geometry(self):
        box = Solid.make_box(1, 1, 2)
        self.assertEqual(box.faces().sort_by(Axis.Z).last.geometry, "SQUARE")
        self.assertEqual(box.faces().sort_by(Axis.Y).last.geometry, "RECTANGLE")
        with BuildPart() as test:
            with BuildSketch():
                RegularPolygon(1, 3)
            extrude(amount=1)
        self.assertEqual(test.faces().sort_by(Axis.Z).last.geometry, "POLYGON")

    def test_is_planar(self):
        self.assertTrue(Face.make_rect(1, 1).is_planar)
        self.assertFalse(
            Solid.make_cylinder(1, 1).faces().filter_by(GeomType.CYLINDER)[0].is_planar
        )
        # Some of these faces have geom_type BSPLINE but are planar
        mount = Solid.make_loft(
            [
                Rectangle((1 + 16 + 4), 20, align=(Align.MIN, Align.CENTER)).wire(),
                Pos(1, 0, 4)
                * Rectangle(16, 20, align=(Align.MIN, Align.CENTER)).wire(),
            ],
        )
        self.assertTrue(all(f.is_planar for f in mount.faces()))

    def test_negate(self):
        square = Face.make_rect(1, 1)
        self.assertAlmostEqual(square.normal_at(), (0, 0, 1), 5)
        flipped_square = -square
        self.assertAlmostEqual(flipped_square.normal_at(), (0, 0, -1), 5)

    def test_offset(self):
        bbox = Face.make_rect(2, 2, Plane.XY).offset(5).bounding_box()
        self.assertAlmostEqual(bbox.min, (-1, -1, 5), 5)
        self.assertAlmostEqual(bbox.max, (1, 1, 5), 5)

    def test_make_from_wires(self):
        outer = Wire.make_circle(10)
        inners = [
            Wire.make_circle(1).locate(Location((-2, 2, 0))),
            Wire.make_circle(1).locate(Location((2, 2, 0))),
        ]
        happy = Face(outer, inners)
        self.assertAlmostEqual(happy.area, math.pi * (10**2 - 2), 5)

        outer = Edge.make_circle(10, end_angle=180).to_wire()
        with self.assertRaises(ValueError):
            Face(outer, inners)
        with self.assertRaises(ValueError):
            Face(Wire.make_circle(10, Plane.XZ), inners)

        outer = Wire.make_circle(10)
        inners = [
            Wire.make_circle(1).locate(Location((-2, 2, 0))),
            Edge.make_circle(1, end_angle=180).to_wire().locate(Location((2, 2, 0))),
        ]
        with self.assertRaises(ValueError):
            Face(outer, inners)

    def test_sew_faces(self):
        patches = [
            Face.make_rect(1, 1, Plane((x, y, z)))
            for x in range(2)
            for y in range(2)
            for z in range(3)
        ]
        random.shuffle(patches)
        sheets = Face.sew_faces(patches)
        self.assertEqual(len(sheets), 3)
        self.assertEqual(len(sheets[0]), 4)
        self.assertTrue(isinstance(sheets[0][0], Face))

    def test_surface_from_array_of_points(self):
        pnts = [
            [
                Vector(x, y, math.cos(math.pi * x / 10) + math.sin(math.pi * y / 10))
                for x in range(11)
            ]
            for y in range(11)
        ]
        surface = Face.make_surface_from_array_of_points(pnts)
        bbox = surface.bounding_box()
        self.assertAlmostEqual(bbox.min, (0, 0, -1), 3)
        self.assertAlmostEqual(bbox.max, (10, 10, 2), 2)

    def test_bezier_surface(self):
        points = [
            [
                (x, y, 2 if x == 0 and y == 0 else 1 if x == 0 or y == 0 else 0)
                for x in range(-1, 2)
            ]
            for y in range(-1, 2)
        ]
        surface = Face.make_bezier_surface(points)
        bbox = surface.bounding_box()
        self.assertAlmostEqual(bbox.min, (-1, -1, 0), 3)
        self.assertAlmostEqual(bbox.max, (+1, +1, +1), 1)
        self.assertLess(bbox.max.Z, 1.0)

        weights = [
            [2 if x == 0 or y == 0 else 1 for x in range(-1, 2)] for y in range(-1, 2)
        ]
        surface = Face.make_bezier_surface(points, weights)
        bbox = surface.bounding_box()
        self.assertAlmostEqual(bbox.min, (-1, -1, 0), 3)
        self.assertGreater(bbox.max.Z, 1.0)

        too_many_points = [
            [
                (x, y, 2 if x == 0 and y == 0 else 1 if x == 0 or y == 0 else 0)
                for x in range(-1, 27)
            ]
            for y in range(-1, 27)
        ]

        with self.assertRaises(ValueError):
            Face.make_bezier_surface([[(0, 0)]])
        with self.assertRaises(ValueError):
            Face.make_bezier_surface(points, [[1, 1], [1, 1]])
        with self.assertRaises(ValueError):
            Face.make_bezier_surface(too_many_points)

    def test_thicken(self):
        pnts = [
            [
                Vector(x, y, math.cos(math.pi * x / 10) + math.sin(math.pi * y / 10))
                for x in range(11)
            ]
            for y in range(11)
        ]
        surface = Face.make_surface_from_array_of_points(pnts)
        solid = Solid.thicken(surface, 1)
        self.assertAlmostEqual(solid.volume, 101.59, 2)

        square = Face.make_rect(10, 10)
        bbox = Solid.thicken(square, 1, normal_override=(0, 0, -1)).bounding_box()
        self.assertAlmostEqual(bbox.min, (-5, -5, -1), 5)
        self.assertAlmostEqual(bbox.max, (5, 5, 0), 5)

    def test_make_holes(self):
        radius = 10
        circumference = 2 * math.pi * radius
        hex_diagonal = 4 * (circumference / 10) / 3
        cylinder = Solid.make_cylinder(radius, hex_diagonal * 5)
        cylinder_wall: Face = cylinder.faces().filter_by(GeomType.PLANE, reverse=True)[
            0
        ]
        with BuildSketch(Plane.XZ.offset(radius)) as hex:
            with Locations((0, hex_diagonal)):
                RegularPolygon(
                    hex_diagonal * 0.4, 6, align=(Align.CENTER, Align.CENTER)
                )
        hex_wire_vertical: Wire = hex.sketch.faces()[0].outer_wire()

        projected_wire: Wire = hex_wire_vertical.project_to_shape(
            target_object=cylinder, center=(0, 0, hex_wire_vertical.center().Z)
        )[0]
        projected_wires = [
            projected_wire.rotate(Axis.Z, -90 + i * 360 / 10).translate(
                (0, 0, (j + (i % 2) / 2) * hex_diagonal)
            )
            for i in range(5)
            for j in range(4 - i % 2)
        ]
        cylinder_walls_with_holes = cylinder_wall.make_holes(projected_wires)
        self.assertTrue(cylinder_walls_with_holes.is_valid())
        self.assertLess(cylinder_walls_with_holes.area, cylinder_wall.area)

    def test_is_inside(self):
        square = Face.make_rect(10, 10)
        self.assertTrue(square.is_inside((1, 1)))
        self.assertFalse(square.is_inside((20, 1)))

    def test_import_stl(self):
        torus = Solid.make_torus(10, 1)
        # exporter = Mesher()
        # exporter.add_shape(torus)
        # exporter.write("test_torus.stl")
        export_stl(torus, "test_torus.stl")
        imported_torus = import_stl("test_torus.stl")
        # The torus from stl is tessellated therefore the areas will only be close
        self.assertAlmostEqual(imported_torus.area, torus.area, 0)
        os.remove("test_torus.stl")

    def test_is_coplanar(self):
        square = Face.make_rect(1, 1, plane=Plane.XZ)
        self.assertTrue(square.is_coplanar(Plane.XZ))
        self.assertTrue((-square).is_coplanar(Plane.XZ))
        self.assertFalse(square.is_coplanar(Plane.XY))
        surface: Face = Solid.make_sphere(1).faces()[0]
        self.assertFalse(surface.is_coplanar(Plane.XY))

    def test_center_location(self):
        square = Face.make_rect(1, 1, plane=Plane.XZ)
        cl = square.center_location
        self.assertAlmostEqual(cl.position, (0, 0, 0), 5)
        self.assertAlmostEqual(Plane(cl).z_dir, Plane.XZ.z_dir, 5)

    def test_position_at(self):
        square = Face.make_rect(2, 2, plane=Plane.XZ.offset(1))
        p = square.position_at(0.25, 0.75)
        self.assertAlmostEqual(p, (-0.5, -1.0, 0.5), 5)

    def test_location_at(self):
        bottom = Box(1, 2, 3, align=Align.MIN).faces().filter_by(Axis.Z)[0]
        loc = bottom.location_at(0.5, 0.5)
        self.assertAlmostEqual(loc.position, (0.5, 1, 0), 5)
        self.assertAlmostEqual(loc.orientation, (-180, 0, -180), 5)

        front = Box(1, 2, 3, align=Align.MIN).faces().filter_by(Axis.X)[0]
        loc = front.location_at(0.5, 0.5, x_dir=(0, 0, 1))
        self.assertAlmostEqual(loc.position, (0.0, 1.0, 1.5), 5)
        self.assertAlmostEqual(loc.orientation, (0, -90, 0), 5)

    def test_make_surface(self):
        corners = [Vector(x, y) for x in [-50.5, 50.5] for y in [-24.5, 24.5]]
        net_exterior = Wire(
            [
                Edge.make_line(corners[3], corners[1]),
                Edge.make_line(corners[1], corners[0]),
                Edge.make_line(corners[0], corners[2]),
                Edge.make_three_point_arc(
                    corners[2],
                    (corners[2] + corners[3]) / 2 - Vector(0, 0, 3),
                    corners[3],
                ),
            ]
        )
        surface = Face.make_surface(
            net_exterior,
            surface_points=[Vector(0, 0, -5)],
        )
        hole_flat = Wire.make_circle(10)
        hole = hole_flat.project_to_shape(surface, (0, 0, -1))[0]
        surface = Face.make_surface(
            exterior=net_exterior,
            surface_points=[Vector(0, 0, -5)],
            interior_wires=[hole],
        )
        self.assertTrue(surface.is_valid())
        self.assertEqual(surface.geom_type, GeomType.BSPLINE)
        bbox = surface.bounding_box()
        self.assertAlmostEqual(bbox.min, (-50.5, -24.5, -5.113393280136395), 5)
        self.assertAlmostEqual(bbox.max, (50.5, 24.5, 0), 5)

        # With no surface point
        surface = Face.make_surface(net_exterior)
        bbox = surface.bounding_box()
        self.assertAlmostEqual(bbox.min, (-50.5, -24.5, -3), 5)
        self.assertAlmostEqual(bbox.max, (50.5, 24.5, 0), 5)

        # Exterior Edge
        surface = Face.make_surface([Edge.make_circle(50)], surface_points=[(0, 0, -5)])
        bbox = surface.bounding_box()
        self.assertAlmostEqual(bbox.min, (-50, -50, -5), 5)
        self.assertAlmostEqual(bbox.max, (50, 50, 0), 5)

    def test_make_surface_error_checking(self):
        with self.assertRaises(ValueError):
            Face.make_surface(Edge.make_line((0, 0), (1, 0)))

        with self.assertRaises(RuntimeError):
            Face.make_surface([Edge.make_line((0, 0), (1, 0))])

        if platform.system() != "Darwin":
            with self.assertRaises(RuntimeError):
                Face.make_surface(
                    [Edge.make_circle(50)], surface_points=[(0, 0, -50), (0, 0, 50)]
                )

            with self.assertRaises(RuntimeError):
                Face.make_surface(
                    [Edge.make_circle(50)],
                    interior_wires=[Wire.make_circle(5, Plane.XZ)],
                )

    def test_sweep(self):
        edge = Edge.make_line((1, 0), (2, 0))
        path = Wire.make_circle(1)
        circle_with_hole = Face.sweep(edge, path)
        self.assertTrue(isinstance(circle_with_hole, Face))
        self.assertAlmostEqual(circle_with_hole.area, math.pi * (2**2 - 1**1), 5)
        with self.assertRaises(ValueError):
            Face.sweep(edge, Polyline((0, 0), (0.1, 0), (0.2, 0.1)))

    def test_to_arcs(self):
        with BuildSketch() as bs:
            with BuildLine() as bl:
                Polyline((0, 0), (1, 0), (1.5, 0.5), (2, 0), (2, 1), (0, 1), (0, 0))
                fillet(bl.vertices(), radius=0.1)
            make_face()
        smooth = bs.faces()[0]
        fragmented = smooth.to_arcs()
        self.assertLess(len(smooth.edges()), len(fragmented.edges()))

    def test_outer_wire(self):
        face = (Face.make_rect(1, 1) - Face.make_rect(0.5, 0.5)).face()
        self.assertAlmostEqual(face.outer_wire().length, 4, 5)

    def test_wire(self):
        face = (Face.make_rect(1, 1) - Face.make_rect(0.5, 0.5)).face()
        with self.assertWarns(UserWarning):
            outer = face.wire()
        self.assertAlmostEqual(outer.length, 4, 5)

    def test_constructor(self):
        with self.assertRaises(ValueError):
            Face(bob="fred")

    def test_normal_at(self):
        face = Face.make_rect(1, 1)
        self.assertAlmostEqual(face.normal_at(0, 0), (0, 0, 1), 5)
        self.assertAlmostEqual(face.normal_at(face.position_at(0, 0)), (0, 0, 1), 5)
        with self.assertRaises(ValueError):
            face.normal_at(0)
        with self.assertRaises(ValueError):
            face.normal_at(center=(0, 0))
        face = Cylinder(1, 1).faces().filter_by(GeomType.CYLINDER)[0]
        self.assertAlmostEqual(face.normal_at(0, 1), (1, 0, 0), 5)

    def test_remove_holes(self):
        # Planar test
        frame = (Rectangle(1, 1) - Rectangle(0.5, 0.5)).face()
        filled = frame.remove_holes()
        self.assertEqual(len(frame.inner_wires()), 1)
        self.assertEqual(len(filled.inner_wires()), 0)
        self.assertAlmostEqual(frame.area, 0.75, 5)
        self.assertAlmostEqual(filled.area, 1.0, 5)

        # Errors
        frame.wrapped = None
        with self.assertRaises(ValueError):
            frame.remove_holes()

        # No holes
        rect = Face.make_rect(1, 1)
        self.assertEqual(rect, rect.remove_holes())

        # Non-planar test
        cyl_face = (
            (Cylinder(1, 3) - Cylinder(0.5, 3, rotation=(90, 0, 0)))
            .faces()
            .sort_by(Face.area)[-1]
        )
        filled = cyl_face.remove_holes()
        self.assertEqual(len(cyl_face.inner_wires()), 2)
        self.assertEqual(len(filled.inner_wires()), 0)
        self.assertTrue(cyl_face.area < filled.area)
        self.assertAlmostEqual(cyl_face.total_area, filled.area, 5)

    def test_total_area(self):
        frame = (Rectangle(1, 1) - Rectangle(0.5, 0.5)).face()
        frame.wrapped = None
        self.assertAlmostEqual(frame.total_area, 0.0, 5)


if __name__ == "__main__":
    unittest.main()
