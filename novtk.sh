uv pip install --no-deps ocpsvg svgelements cadquery_ocp_novtk
gsed -i '/cadquery-ocp >/d; /ocpsvg/d' pyproject.toml
uv pip install -e .
git checkout pyproject.toml 
