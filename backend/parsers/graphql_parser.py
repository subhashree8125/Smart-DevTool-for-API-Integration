import re
import json
import logging
from typing import Dict, Any, List
from backend.models.schemas import EndpointSchema

logger = logging.getLogger(__name__)

def parse_graphql(content: str) -> Dict[str, Any]:
    """
    Parses GraphQL Schema Definition Language (SDL).
    Identifies Queries and Mutations, and translates them to HTTP POST /graphql endpoints
    with their respective schema argument parameters.
    """
    endpoints = []
    
    # Simple regex parsing to extract Query and Mutation blocks
    query_block_match = re.search(r'type\s+Query\s*\{(.*?)\}', content, re.DOTALL | re.IGNORECASE)
    mutation_block_match = re.search(r'type\s+Mutation\s*\{(.*?)\}', content, re.DOTALL | re.IGNORECASE)

    blocks = []
    if query_block_match:
        blocks.append(("Query", query_block_match.group(1)))
    if mutation_block_match:
        blocks.append(("Mutation", mutation_block_match.group(1)))

    # Parse fields within blocks
    # Pattern to capture: field_name(arg: Type, ...): ReturnType
    field_pattern = re.compile(
        r'(\w+)\s*(?:\((.*?)\))?\s*:\s*([\w\[\]\!]+)', 
        re.DOTALL
    )

    for block_type, block_content in blocks:
        fields = field_pattern.findall(block_content)
        for name, args_str, ret_type in fields:
            # Skip fields with comments or description artifacts parsed incorrectly
            if name.lower() in ("query", "mutation"):
                continue

            query_params = []
            sample_args = []
            
            if args_str:
                # Parse arguments: argName: Type
                arg_pairs = re.findall(r'(\w+)\s*:\s*([\w\[\]\!]+)', args_str)
                for arg_name, arg_type in arg_pairs:
                    query_params.append({
                        "name": arg_name,
                        "type": arg_type,
                        "required": "!" in arg_type,
                        "description": f"GraphQL {block_type} argument"
                    })
                    # Create mock argument values
                    if "int" in arg_type.lower() or "float" in arg_type.lower():
                        val = "0"
                    elif "boolean" in arg_type.lower():
                        val = "true"
                    else:
                        val = '"string"'
                    sample_args.append(f"{arg_name}: {val}")

            # Prepare sample request payload
            args_formatted = f"({', '.join(sample_args)})" if sample_args else ""
            sample_query = (
                f"{block_type.lower()} {{\n"
                f"  {name}{args_formatted} {{\n"
                f"    # Return fields (Type: {ret_type})\n"
                f"  }}\n"
                f"}}"
            )
            
            sample_request = json.dumps({"query": sample_query}, indent=2)

            endpoints.append(EndpointSchema(
                id=f"{block_type.lower()}_{name}",
                method="POST",
                path="/graphql",
                description=f"GraphQL {block_type} operation to invoke {name}.",
                auth_required=False,
                headers=[{"name": "Content-Type", "type": "string", "required": True, "description": "application/json"}],
                query_params=[],
                path_params=[],
                request_body={"type": "object", "properties": {"query": "string", "variables": "object"}},
                response_body={"type": "object", "properties": {"data": {name: ret_type}}},
                status_codes=[200],
                sample_request=sample_request,
                sample_response=json.dumps({"data": {name: None}}, indent=2)
            ))

    # If no endpoints detected by regex, we add a generic GraphQL POST endpoint
    if not endpoints:
        endpoints.append(EndpointSchema(
            id="graphql_endpoint",
            method="POST",
            path="/graphql",
            description="Generic GraphQL entry point for execution of queries and mutations.",
            auth_required=False,
            headers=[{"name": "Content-Type", "type": "string", "required": True}],
            query_params=[],
            path_params=[],
            request_body={"type": "object", "properties": {"query": "string", "variables": "object"}},
            response_body={"type": "object", "properties": {"data": "object"}},
            status_codes=[200],
            sample_request=json.dumps({"query": "query { __schema { types { name } } }"}, indent=2)
        ))

    return {
        "name": "GraphQL API",
        "version": "1.0.0",
        "base_url": "/graphql",
        "auth_type": "Bearer Token / None",
        "endpoints": endpoints
    }
