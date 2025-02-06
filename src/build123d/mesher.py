"""
build123d exporter/import for 3MF and STL

name: mesher.py
by:   Gumyr
date: Aug 9th 2023

desc:
    This module provides the Mesher class that implements exporting and importing
    both 3MF and STL mesh files.  It uses the 3MF Consortium's Lib3MF library
    (see https://github.com/3MFConsortium/lib3mf).

    Creating a 3MF object involves constructing a valid 3D model conforming to
    the 3MF specification. The resource hierarchy represents the various
    components that make up a 3MF object. The main components required to create
    a 3MF object are:

        Wrapper: The wrapper is the highest-level component representing the
    entire 3MF model. It serves as a container for all other resources and
    provides access to the complete 3D model. The wrapper is the starting point
    for creating and managing the 3MF model.

        Model: The model is a core component that contains the geometric and
    non-geometric resources of the 3D object. It represents the actual 3D
    content, including geometry, materials, colors, textures, and other model
    information.

        Resources: Within the model, various resources are used to define
    different aspects of the 3D object. Some essential resources are:

        a. Mesh: The mesh resource defines the geometry of the 3D object. It
    contains a collection of vertices, triangles, and other geometric
    information that describes the shape.

        b. Components: Components allow you to define complex structures by
    combining multiple meshes together. They are useful for hierarchical
    assemblies and instances.

        c. Materials: Materials define the appearance properties of the
    surfaces, such as color, texture, or surface finish.

        d. Textures: Textures are images applied to the surfaces of the 3D
    object to add detail and realism.

        e. Colors: Colors represent color information used in the 3D model,
    which can be applied to vertices or faces.

        Build Items: Build items are the instances of resources used in the 3D
    model. They specify the usage of resources within the model. For example, a
    build item can refer to a specific mesh, material, and transformation to
    represent an instance of an object.

        Metadata: Metadata provides additional information about the model, such
    as author, creation date, and custom properties.

        Attachments: Attachments can include additional files or data associated
    with the 3MF object, such as texture images or other external resources.

    When creating a 3MF object, you typically start with the wrapper and then
    create or import the necessary resources, such as meshes, materials, and
    textures, to define the 3D content. You then organize the model using build
    items, specifying how the resources are used in the scene. Additionally, you
    can add metadata and attachments as needed to complete the 3MF object.

license:

    Copyright 2023 Gumyr

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

# pylint has trouble with the OCP imports
# pylint: disable=no-name-in-module, import-error
import copy as copy_module
import ctypes
import math
import os
import sys
import warnings
from os import PathLike, fsdecode
from typing import Union
from uuid import UUID

from collections.abc import Iterable

import OCP.TopAbs as ta
from OCP.BRep import BRep_Tool
from OCP.BRepBuilderAPI import (
    BRepBuilderAPI_MakeFace,
    BRepBuilderAPI_MakePolygon,
    BRepBuilderAPI_MakeSolid,
    BRepBuilderAPI_Sewing,
)
from OCP.BRepGProp import BRepGProp
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.gp import gp_Pnt
from OCP.GProp import GProp_GProps
from OCP.TopAbs import TopAbs_ShapeEnum
from OCP.TopExp import TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS_Compound
from py_lib3mf import Lib3MF

from build123d.build_enums import MeshType, Unit
from build123d.geometry import TOLERANCE, Color
from build123d.topology import Compound, Shape, Shell, Solid, downcast


class Mesher:
    """Mesher

    Tool for exporting and importing meshed objects stored in 3MF or STL files.

    Args:
        unit (Unit, optional): model units. Defaults to Unit.MM.
    """

    # Translate b3d Units to Lib3MF ModelUnits
    _map_b3d_to_3mf_unit = {
        Unit.MC: Lib3MF.ModelUnit.MicroMeter,
        Unit.MM: Lib3MF.ModelUnit.MilliMeter,
        Unit.CM: Lib3MF.ModelUnit.CentiMeter,
        Unit.IN: Lib3MF.ModelUnit.Inch,
        Unit.FT: Lib3MF.ModelUnit.Foot,
        Unit.M: Lib3MF.ModelUnit.Meter,
    }
    # Translate Lib3MF ModelUnits to b3d Units
    _map_3mf_to_b3d_unit = {v: k for k, v in _map_b3d_to_3mf_unit.items()}

    # Translate b3d MeshTypes to 3MF ObjectType
    _map_b3d_mesh_type_3mf = {
        MeshType.OTHER: Lib3MF.ObjectType.Other,
        MeshType.MODEL: Lib3MF.ObjectType.Model,
        MeshType.SUPPORT: Lib3MF.ObjectType.Support,
        MeshType.SOLIDSUPPORT: Lib3MF.ObjectType.SolidSupport,
    }
    # Translate 3MF ObjectType to b3d MeshTypess
    _map_3mf_to_b3d_mesh_type = {v: k for k, v in _map_b3d_mesh_type_3mf.items()}

    def __init__(self, unit: Unit = Unit.MM):
        self.unit = unit
        libpath = os.path.dirname(Lib3MF.__file__)
        self.wrapper = Lib3MF.Wrapper(os.path.join(libpath, "lib3mf"))
        self.model = self.wrapper.CreateModel()
        self.model.SetUnit(Mesher._map_b3d_to_3mf_unit[unit])
        self.meshes: list[Lib3MF.MeshObject] = []

    @property
    def model_unit(self) -> Unit:
        """Unit used in the model"""
        return self.unit

    @property
    def triangle_counts(self) -> list[int]:
        """Number of triangles in each of the model's meshes"""
        return [m.GetTriangleCount() for m in self.meshes]

    @property
    def vertex_counts(self) -> list[int]:
        """Number of vertices in each of the models's meshes"""
        return [m.GetVertexCount() for m in self.meshes]

    @property
    def mesh_count(self) -> int:
        """Number of meshes in the model"""
        mesh_iterator: Lib3MF.MeshObjectIterator = self.model.GetMeshObjects()
        return mesh_iterator.Count()

    @property
    def library_version(self) -> str:
        """3MF Consortium Lib#MF version"""
        major, minor, micro = self.wrapper.GetLibraryVersion()
        return f"{major}.{minor}.{micro}"

    def add_meta_data(
        self,
        name_space: str,
        name: str,
        value: str,
        metadata_type: str,
        must_preserve: bool,
    ):
        """add_meta_data

        Add meta data to the models

        Args:
            name_space (str): categorizer of different metadata entries
            name (str): metadata label
            value (str): metadata content
            metadata_type (str): metadata type
            must_preserve (bool): metadata must not be removed if unused
        """
        # Get an existing meta data group if there is one
        mdg = self.model.GetMetaDataGroup()
        if mdg is None:
            # Create a components object to attach the meta data group
            components: Lib3MF.ComponentsObject = self.model.AddComponentsObject()
            mdg = components.GetMetaDataGroup()

        # Add the meta data
        mdg.AddMetaData(name_space, name, value, metadata_type, must_preserve)

    def add_code_to_metadata(self):
        """Add the code calling this method to the 3MF metadata with the custom
        name space `build123d`, name equal to the base file name and the type
        as `python`"""
        caller_file = sys._getframe().f_back.f_code.co_filename
        with open(caller_file, encoding="utf-8") as code_file:
            source_code = code_file.read()  # read whole file to a string

        self.add_meta_data(
            name_space="build123d",
            name=os.path.basename(caller_file),
            value=source_code,
            metadata_type="python",
            must_preserve=False,
        )

    def get_meta_data(self) -> list[dict]:
        """Retrieve all of the metadata"""
        meta_data_group = self.model.GetMetaDataGroup()
        meta_data_contents = []
        for i in range(meta_data_group.GetMetaDataCount()):
            meta_data = meta_data_group.GetMetaData(i)
            meta_data_dict = {}
            meta_data_dict["name_space"] = meta_data.GetNameSpace()
            meta_data_dict["name"] = meta_data.GetName()
            meta_data_dict["type"] = meta_data.GetType()
            meta_data_dict["value"] = meta_data.GetValue()
            meta_data_contents.append(meta_data_dict)
        return meta_data_contents

    def get_meta_data_by_key(self, name_space: str, name: str) -> dict:
        """Retrieve the metadata value and type for the provided name space and name"""
        meta_data_group = self.model.GetMetaDataGroup()
        meta_data_contents = {}
        meta_data = meta_data_group.GetMetaDataByKey(name_space, name)
        meta_data_contents["type"] = meta_data.GetType()
        meta_data_contents["value"] = meta_data.GetValue()
        return meta_data_contents

    def get_mesh_properties(self) -> list[dict]:
        """Retrieve the properties from all the meshes"""
        properties = []
        for mesh in self.meshes:
            property_dict = {}
            property_dict["name"] = mesh.GetName()
            property_dict["part_number"] = mesh.GetPartNumber()
            type_3mf = Lib3MF.ObjectType(mesh.GetType())
            property_dict["type"] = Mesher._map_3mf_to_b3d_mesh_type[type_3mf].name
            _uuid_valid, uuid_value = mesh.GetUUID()
            property_dict["uuid"] = uuid_value  # are bad values possible?
            properties.append(property_dict)
        return properties

    @staticmethod
    def _mesh_shape(
        ocp_mesh: Shape,
        linear_deflection: float,
        angular_deflection: float,
    ):
        """Mesh the shape into vertices and triangles"""
        loc = TopLoc_Location()  # Face locations
        BRepMesh_IncrementalMesh(
            theShape=ocp_mesh.wrapped,
            theLinDeflection=linear_deflection,
            isRelative=True,
            theAngDeflection=angular_deflection,
            isInParallel=True,
        )

        ocp_mesh_vertices = []
        triangles = []
        offset = 0
        for facet in ocp_mesh.faces():
            # Triangulate the face
            poly_triangulation = BRep_Tool.Triangulation_s(facet.wrapped, loc)
            trsf = loc.Transformation()
            # Store the vertices in the triangulated face
            node_count = poly_triangulation.NbNodes()
            for i in range(1, node_count + 1):
                gp_pnt = poly_triangulation.Node(i).Transformed(trsf)
                pnt = (gp_pnt.X(), gp_pnt.Y(), gp_pnt.Z())
                ocp_mesh_vertices.append(pnt)

            # Store the triangles from the triangulated faces
            if facet.wrapped is None:
                continue
            facet_reversed = facet.wrapped.Orientation() == ta.TopAbs_REVERSED
            order = [1, 3, 2] if facet_reversed else [1, 2, 3]
            for tri in poly_triangulation.Triangles():
                triangles.append([tri.Value(i) + offset - 1 for i in order])
            offset += node_count
        return ocp_mesh_vertices, triangles

    @staticmethod
    def _create_3mf_mesh(
        ocp_mesh_vertices: list[tuple[float, float, float]],
        triangles: list[list[int]],
    ):
        # Round off the vertices to avoid vertices within tolerance being
        # considered as different vertices
        digits = -int(round(math.log(TOLERANCE, 10), 1))
        
        # Create vertex to index mapping directly
        vertex_to_idx = {}
        next_idx = 0
        vert_table = {}
        
        # First pass - create mapping
        for i, (x, y, z) in enumerate(ocp_mesh_vertices):
            key = (round(x, digits), round(y, digits), round(z, digits))
            if key not in vertex_to_idx:
                vertex_to_idx[key] = next_idx
                next_idx += 1
            vert_table[i] = vertex_to_idx[key]
        
        # Create vertices array in one shot
        vertices_3mf = [
            Lib3MF.Position((ctypes.c_float * 3)(*v))
            for v in vertex_to_idx.keys()
        ]
        
        # Pre-allocate triangles array and process in bulk
        c_uint3 = ctypes.c_uint * 3
        triangles_3mf = []
        
        # Process triangles in bulk
        for tri in triangles:
            # Map indices directly without list comprehension
            a, b, c = tri[0], tri[1], tri[2]
            mapped_a = vert_table[a]
            mapped_b = vert_table[b]
            mapped_c = vert_table[c]
            
            # Quick degenerate check without set creation
            if mapped_a != mapped_b and mapped_b != mapped_c and mapped_c != mapped_a:
                triangles_3mf.append(Lib3MF.Triangle(c_uint3(mapped_a, mapped_b, mapped_c)))
        
        return (vertices_3mf, triangles_3mf)

    def _add_color(self, b3d_shape: Shape, mesh_3mf: Lib3MF.MeshObject):
        """Transfer color info from shape to mesh"""
        if b3d_shape.color:
            base_material_group = self.model.AddBaseMaterialGroup()
            color_lib3mf = self.wrapper.FloatRGBAToColor(*tuple(b3d_shape.color))
            base_material_id = base_material_group.AddMaterial(
                Name=str(b3d_shape.color), DisplayColor=color_lib3mf
            )
            mesh_3mf.SetObjectLevelProperty(
                base_material_group.GetResourceID(), base_material_id
            )

    def add_shape(
        self,
        shape: Shape | Iterable[Shape],
        linear_deflection: float = 0.001,
        angular_deflection: float = 0.1,
        mesh_type: MeshType = MeshType.MODEL,
        part_number: str | None = None,
        uuid_value: UUID | None = None,
    ):
        """add_shape

        Add a shape to the 3MF/STL file.

        Args:
            shape (Union[Shape, Iterable[Shape]]): build123d object
            linear_deflection (float, optional): mesh control for edges. Defaults to 0.001.
            angular_deflection (float, optional): mesh control for non-planar surfaces.
                Defaults to 0.1.
            mesh_type (MeshType, optional): 3D printing use of mesh. Defaults to MeshType.MODEL.
            part_number (str, optional): part #. Defaults to None.
            uuid_value (uuid, optional): value from uuid package. Defaults to None.

        Raises:
            RuntimeError: 3mf mesh is invalid
            Warning: Degenerate shape skipped
            Warning: 3mf mesh is not manifold
        """
        shapes = []
        for input_shape in shape if isinstance(shape, Iterable) else [shape]:
            if isinstance(input_shape, Compound):
                shapes.extend(list(input_shape))
            else:
                shapes.append(input_shape)

        for b3d_shape in shapes:
            # Create a 3MF mesh object
            mesh_3mf: Lib3MF.MeshObject = self.model.AddMeshObject()

            # Mesh the shape
            ocp_mesh_vertices, triangles = Mesher._mesh_shape(
                copy_module.deepcopy(b3d_shape),
                linear_deflection,
                angular_deflection,
            )

            # Skip invalid meshes
            if len(ocp_mesh_vertices) < 3 or not triangles:
                warnings.warn(
                    f"Degenerate shape {b3d_shape} - skipped",
                    stacklevel=2,
                )
                continue

            # Create 3mf mesh inputs
            vertices_3mf, triangles_3mf = Mesher._create_3mf_mesh(
                ocp_mesh_vertices, triangles
            )

            # Build the mesh
            mesh_3mf.SetGeometry(vertices_3mf, triangles_3mf)

            # Add the mesh properties
            mesh_3mf.SetType(Mesher._map_b3d_mesh_type_3mf[mesh_type])
            if b3d_shape.label:
                mesh_3mf.SetName(b3d_shape.label)
            if part_number:
                mesh_3mf.SetPartNumber(part_number)
            if uuid_value:
                mesh_3mf.SetUUID(str(uuid_value))
            # mesh_3mf.SetAttachmentAsThumbnail
            # mesh_3mf.SetPackagePart

            # Add color
            self._add_color(b3d_shape, mesh_3mf)

            # Check mesh
            if not mesh_3mf.IsValid():
                raise RuntimeError("3mf mesh is invalid")
            if not mesh_3mf.IsManifoldAndOriented():
                warnings.warn("3mf mesh is not manifold", stacklevel=2)

            # Add mesh to model
            self.meshes.append(mesh_3mf)
            self.model.AddBuildItem(mesh_3mf, self.wrapper.GetIdentityTransform())

            # Not sure is this is required...
            components = self.model.AddComponentsObject()
            components.AddComponent(mesh_3mf, self.wrapper.GetIdentityTransform())

    def _get_shape(self, mesh_3mf: Lib3MF.MeshObject) -> Shape:
        """Build build123d object from lib3mf mesh"""
        # Extract all the vertices
        gp_pnts = [gp_Pnt(*p.Coordinates[0:3]) for p in mesh_3mf.GetVertices()]

        # Extract all the triangle and create a Shell from generated Faces
        shell_builder = BRepBuilderAPI_Sewing()
        for i in range(mesh_3mf.GetTriangleCount()):
            # Extract the vertex indices for this triangle
            tri_indices = mesh_3mf.GetTriangle(i).Indices[0:3]
            # Convert to a list of gp_Pnt
            ocp_vertices = [gp_pnts[tri_indices[i]] for i in range(3)]
            # Create the triangular face using the polygon
            polygon_builder = BRepBuilderAPI_MakePolygon(*ocp_vertices, Close=True)
            face_builder = BRepBuilderAPI_MakeFace(polygon_builder.Wire())
            facet = face_builder.Face()
            facet_properties = GProp_GProps()
            BRepGProp.SurfaceProperties_s(facet, facet_properties)
            if facet_properties.Mass() != 0:  # Area==0 is an invalid facet
                shell_builder.Add(facet)

        # Create the Shell(s) - if the object has voids there will be multiple
        shell_builder.Perform()
        occ_sewed_shape = downcast(shell_builder.SewedShape())

        if isinstance(occ_sewed_shape, TopoDS_Compound):
            occ_shells = []
            explorer = TopExp_Explorer(occ_sewed_shape, TopAbs_ShapeEnum.TopAbs_SHELL)
            while explorer.More():
                occ_shells.append(downcast(explorer.Current()))
                explorer.Next()
        else:
            occ_shells = [occ_sewed_shape]

        # Create a solid if manifold
        shape_obj = Shell(occ_sewed_shape)
        if shape_obj.is_manifold:
            solid_builder = BRepBuilderAPI_MakeSolid(*occ_shells)
            shape_obj = Solid(solid_builder.Solid())

        return shape_obj

    def read(self, file_name: PathLike | str | bytes) -> list[Shape]:
        """read

        Args:
            file_name Union[PathLike, str, bytes]: file path

        Raises:
            ValueError: Unknown file format - must be 3mf or stl

        Returns:
            list[Shape]: build123d shapes extracted from mesh file
        """
        file_name = fsdecode(file_name)
        _, input_file_extension = os.path.splitext(file_name)
        if input_file_extension not in [".3mf", ".stl"]:
            raise ValueError(f"Unknown file format {input_file_extension}")
        reader = self.model.QueryReader(input_file_extension[1:])
        reader.ReadFromFile(file_name)
        self.unit = Mesher._map_3mf_to_b3d_unit[self.model.GetUnit()]

        # Extract 3MF meshes and translate to OCP meshes
        mesh_iterator: Lib3MF.MeshObjectIterator = self.model.GetMeshObjects()
        for _i in range(mesh_iterator.Count()):
            mesh_iterator.MoveNext()
            self.meshes.append(mesh_iterator.GetCurrentMeshObject())
        shapes = []
        for mesh in self.meshes:
            shape = self._get_shape(mesh)
            shape.label = mesh.GetName()
            # Extract color
            # TODO: check tuple 3rd value means material found
            base_mat_id, color_index, material_enabled = mesh.GetObjectLevelProperty()
            if material_enabled:
                base_mat = self.model.GetBaseMaterialGroupByID(base_mat_id)
                base_mat_color: Lib3MF.Color = base_mat.GetDisplayColor(color_index)
                color: tuple = self.wrapper.ColorToFloatRGBA(
                    base_mat_color
                )  # RGBA float
                shape.color = Color(*color)
            shapes.append(shape)

        return shapes

    def write(self, file_name: PathLike | str | bytes):
        """write

        Args:
            file_name Union[Pathlike, str, bytes]: file path

        Raises:
            ValueError: Unknown file format - must be 3mf or stl
        """
        file_name = fsdecode(file_name)
        _, output_file_extension = os.path.splitext(file_name)
        if output_file_extension not in [".3mf", ".stl"]:
            raise ValueError(f"Unknown file format {output_file_extension}")
        writer = self.model.QueryWriter(output_file_extension[1:])
        writer.WriteToFile(file_name)
