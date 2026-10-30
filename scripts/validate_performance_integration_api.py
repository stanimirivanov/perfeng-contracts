"""Validate generated integration OpenAPI and checked-in exchanges offline."""

from pathlib import Path

from openapi_spec_validator import OpenAPIV31SpecValidator

try:
    from .performance_analysis import check_read_scope
    from .performance_integration import check_exchange
    from .validate import ROOT, load_contracts, read_json
    from .validate_api import check_local_references, schema_validator
except ImportError:
    from performance_analysis import check_read_scope
    from performance_integration import check_exchange
    from validate import ROOT, load_contracts, read_json
    from validate_api import check_local_references, schema_validator


def validate_integration(root: Path = ROOT) -> int:
    document = read_json(root / "api/performance-integration/v1/openapi.json")
    check_local_references(document, document)
    OpenAPIV31SpecValidator(document).validate()
    _, validators = load_contracts(root)
    count = 0
    for name in ("completed", "cancelled", "rejected"):
        messages = read_json(root / f"examples/performance-integration/{name}.json")
        for message in messages:
            validators["performance-integration/v1"].validate(message)
            kind = message["type"].split(".")[-2]
            component = {"requested": "Request", "cancel-requested": "Cancellation"}.get(
                kind, kind.title()
            )
            schema_validator(document, component).validate(message)
        check_exchange(messages, "https://provider.example/identity")
        count += len(messages)
    publication = read_json(root / "examples/performance-analysis/published.json")
    validators["performance-analysis/v1"].validate(publication)
    schema_validator(document, "AnalysisPublication").validate(publication)
    admission = read_json(root / "examples/performance-integration/completed.json")[1]
    check_read_scope(
        publication,
        provider=admission["source"],
        principal=admission["data"]["context"]["principal"],
        request=admission["data"]["context"]["request"],
    )
    return count + 1


if __name__ == "__main__":
    print(
        f"Validated performance integration OpenAPI and {validate_integration()} messages offline."
    )
