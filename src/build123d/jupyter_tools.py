"""

name: jupyter_tools.py

desc:
    Based on CadQuery version.

license:

    Copyright 2022 Gumyr

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

# pylint: disable=no-name-in-module
from json import dumps
import os
from string import Template
from typing import Any, Dict, List
from IPython.display import Javascript
from vtkmodules.vtkIOXML import vtkXMLPolyDataWriter

DEFAULT_COLOR = [1, 0.8, 0, 1]

dir_path = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(dir_path, "template_render.js"), encoding="utf-8") as f:
    TEMPLATE_JS = f.read()


def to_vtkpoly_string(
    shape: Any, tolerance: float = 1e-3, angular_tolerance: float = 0.1
) -> str:
    """to_vtkpoly_string

    Args:
        shape (Shape): object to convert
        tolerance (float, optional): Defaults to 1e-3.
        angular_tolerance (float, optional): Defaults to 0.1.

    Raises:
        ValueError: not a valid Shape

    Returns:
        str: vtkpoly str
    """
    if not hasattr(shape, "wrapped"):
        raise ValueError(f"Type {type(shape)} is not supported")

    writer = vtkXMLPolyDataWriter()
    writer.SetWriteToOutputString(True)
    writer.SetInputData(shape.to_vtk_poly_data(tolerance, angular_tolerance, True))
    writer.Write()

    return writer.GetOutputString()


def display(shape: Any) -> Javascript:
    """display

    Args:
        shape (Shape): object to display

    Raises:
        ValueError: not a valid Shape

    Returns:
        Javascript: code
    """
    payload: list[dict[str, Any]] = []

    if not hasattr(shape, "wrapped"):  # Is a "Shape"
        raise ValueError(f"Type {type(shape)} is not supported")

    payload.append(
        {
            "shape": to_vtkpoly_string(shape),
            "color": DEFAULT_COLOR,
            "position": [0, 0, 0],
            "orientation": [0, 0, 0],
        }
    )
    code = Template(TEMPLATE_JS).substitute(data=dumps(payload), element="element", ratio=0.5)

    return Javascript(code)
