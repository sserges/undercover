from fastapi.routing import APIRoute

from backend.main import app


def routes() -> list[APIRoute]:
    return [route for route in app.routes if isinstance(route, APIRoute)]


def test_every_operation_id_matches_its_function():
    for route in routes():
        assert route.operation_id == route.endpoint.__name__, route.path


def test_every_operation_has_a_one_line_docstring():
    for route in routes():
        doc = route.endpoint.__doc__
        assert doc, route.path
        assert "\n" not in doc.strip(), route.path


def test_no_operation_has_optional_inputs():
    schema = app.openapi()
    components = schema.get("components", {}).get("schemas", {})
    for path, operations in schema["paths"].items():
        for operation in operations.values():
            for parameter in operation.get("parameters", []):
                assert parameter["required"], f"{path} {parameter['name']}"
            body = operation.get("requestBody")
            if body:
                assert body["required"], path
                ref = body["content"]["application/json"]["schema"]["$ref"]
                fields = components[ref.split("/")[-1]]
                required = set(fields.get("required", []))
                assert set(fields["properties"]) == required, path
