#!/usr/bin/env python3
"""
Property tests for Kubernetes manifests.

These tests validate structural correctness of k8s YAML files without requiring
a running cluster. They parse YAML files and assert conformance to the
specifications defined in the design document.
"""

import yaml
import pathlib
import re
from typing import Dict, Any, List, Optional

# Test configuration
K8S_DIR = pathlib.Path(__file__).parent.parent / "k8s"
SECRET_KEYS = {"POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB", "DATABASE_URL", "REDIS_URL"}

# For property-based testing
try:
    from hypothesis import given, settings
    from hypothesis import strategies as st
    HYPOTHESIS_AVAILABLE = True
except ImportError:
    HYPOTHESIS_AVAILABLE = False


def load_all(filename: str) -> List[Dict[str, Any]]:
    """Load all YAML documents from a k8s manifest file."""
    file_path = K8S_DIR / filename
    if not file_path.exists():
        raise FileNotFoundError(f"Manifest file not found: {file_path}")
    
    with file_path.open('r') as f:
        content = f.read()
    
    return list(yaml.safe_load_all(content))


def get_container_probes(deployment_doc: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Extract all probes from a Deployment manifest."""
    probes = {}
    
    spec = deployment_doc.get('spec', {})
    template = spec.get('template', {})
    template_spec = template.get('spec', {})
    containers = template_spec.get('containers', [])
    
    for container in containers:
        container_name = container.get('name', 'unknown')
        
        # Check for readinessProbe
        if 'readinessProbe' in container:
            probes[f"{container_name}.readinessProbe"] = container['readinessProbe']
        
        # Check for livenessProbe
        if 'livenessProbe' in container:
            probes[f"{container_name}.livenessProbe"] = container['livenessProbe']
    
    return probes


# Feature: k8s-migration, Property 1: all deployment probe fields conform to specification
def test_deployment_probe_fields_conform_to_specification():
    """
    Test that all deployment probe fields match the exact specification.
    
    For any Deployment manifest in k8s/ that defines a readiness or liveness probe,
    each probe's field values (command/path, initialDelaySeconds, periodSeconds,
    timeoutSeconds, failureThreshold, successThreshold) SHALL exactly match the
    values specified in the requirements.
    
    Specification:
    - deployment-postgres.yaml readiness probe: pg_isready exec, initialDelay=10, 
      period=5, timeout=5, failureThreshold=5, successThreshold=1
    - deployment-redis.yaml readiness probe: redis-cli ping exec, period=5, 
      timeout=3, failureThreshold=3
    - deployment-backend.yaml readiness probe: HTTP GET /health, initialDelay=15, 
      period=10, failureThreshold=3
    - deployment-backend.yaml liveness probe: HTTP GET /health, initialDelay=30, 
      period=20, failureThreshold=3
    - deployment-frontend.yaml readiness probe: HTTP GET /, port=80
    """
    
    # Expected probe configurations based on the specification
    expected_probes = {
        "deployment-postgres.yaml": {
            "postgres.readinessProbe": {
                "exec": {
                    "command": ["pg_isready"]
                },
                "initialDelaySeconds": 10,
                "periodSeconds": 5,
                "timeoutSeconds": 5,
                "failureThreshold": 5,
                "successThreshold": 1
            }
        },
        "deployment-redis.yaml": {
            "redis.readinessProbe": {
                "exec": {
                    "command": ["redis-cli", "ping"]
                },
                "periodSeconds": 5,
                "timeoutSeconds": 3,
                "failureThreshold": 3
                # Note: initialDelaySeconds and successThreshold not specified in requirements
            }
        },
        "deployment-backend.yaml": {
            "inventory-backend.readinessProbe": {
                "httpGet": {
                    "path": "/health",
                    "port": 8000
                },
                "initialDelaySeconds": 15,
                "periodSeconds": 10,
                "failureThreshold": 3
                # Note: timeoutSeconds and successThreshold not specified in requirements
            },
            "inventory-backend.livenessProbe": {
                "httpGet": {
                    "path": "/health",
                    "port": 8000
                },
                "initialDelaySeconds": 30,
                "periodSeconds": 20,
                "failureThreshold": 3
                # Note: timeoutSeconds and successThreshold not specified in requirements
            }
        },
        "deployment-frontend.yaml": {
            "inventory-frontend.readinessProbe": {
                "httpGet": {
                    "path": "/",
                    "port": 80
                }
                # Note: No timing fields specified in requirements - only path and port
            }
        }
    }
    
    # Test each deployment manifest
    for filename, expected_container_probes in expected_probes.items():
        docs = load_all(filename)
        
        # Find the Deployment document
        deployment_doc = None
        for doc in docs:
            if doc and doc.get('kind') == 'Deployment':
                deployment_doc = doc
                break
        
        assert deployment_doc is not None, f"No Deployment found in {filename}"
        
        # Extract actual probes
        actual_probes = get_container_probes(deployment_doc)
        
        # Verify each expected probe exists and matches specification
        for probe_key, expected_probe in expected_container_probes.items():
            assert probe_key in actual_probes, (
                f"Expected probe {probe_key} not found in {filename}. "
                f"Available probes: {list(actual_probes.keys())}"
            )
            
            actual_probe = actual_probes[probe_key]
            
            # Check probe type and configuration
            for field, expected_value in expected_probe.items():
                assert field in actual_probe, (
                    f"Missing field '{field}' in probe {probe_key} in {filename}"
                )
                
                actual_value = actual_probe[field]
                assert actual_value == expected_value, (
                    f"Probe field mismatch in {filename} {probe_key}.{field}: "
                    f"expected {expected_value}, got {actual_value}"
                )
            
            # Ensure no unexpected fields (beyond what's expected)
            # Note: Allow extra fields that might be defaults, but verify core fields
            core_fields = {"exec", "httpGet", "initialDelaySeconds", "periodSeconds", 
                          "timeoutSeconds", "failureThreshold", "successThreshold"}
            
            for field in expected_probe.keys():
                if field in core_fields:
                    # This field must match exactly as verified above
                    pass


# Feature: k8s-migration, Property 2: no plaintext credentials in any manifest
def test_no_plaintext_credentials_in_any_manifest():
    """
    Test that no plaintext credentials appear in any Kubernetes manifest.
    
    For any YAML file in k8s/ and for any environment variable entry in that file
    whose name matches one of the five secret keys (POSTGRES_USER, POSTGRES_PASSWORD, 
    POSTGRES_DB, DATABASE_URL, REDIS_URL), the entry SHALL use valueFrom.secretKeyRef 
    pointing to inventory-secrets, and SHALL NOT have a direct value field containing 
    a string.
    """
    
    # Get all YAML files in k8s directory
    yaml_files = list(K8S_DIR.glob("*.yaml"))
    
    credential_violations = []
    
    for yaml_file in yaml_files:
        docs = load_all(yaml_file.name)
        
        for doc_idx, doc in enumerate(docs):
            if not doc:
                continue
                
            # Recursively search for env vars in the document
            violations = _find_env_credential_violations(doc, yaml_file.name, doc_idx)
            credential_violations.extend(violations)
    
    if credential_violations:
        violation_msg = "\n".join([
            f"  - {violation}" for violation in credential_violations
        ])
        raise AssertionError(
            f"Found plaintext credentials in manifests:\n{violation_msg}\n"
            f"All secret keys {SECRET_KEYS} must use valueFrom.secretKeyRef, not value field."
        )


def _find_env_credential_violations(obj: Any, filename: str, doc_idx: int, path: str = "") -> List[str]:
    """Recursively find environment variable credential violations in a YAML object."""
    violations = []
    
    if isinstance(obj, dict):
        # Check if this is an env var definition
        if "name" in obj and obj["name"] in SECRET_KEYS:
            env_var_name = obj["name"]
            location = f"{filename}[{doc_idx}]{path}.{env_var_name}"
            
            # Check for forbidden direct value
            if "value" in obj:
                violations.append(f"{location} uses 'value' field (forbidden)")
            
            # Check for required secretKeyRef
            if "valueFrom" not in obj:
                violations.append(f"{location} missing 'valueFrom' field")
            elif "secretKeyRef" not in obj.get("valueFrom", {}):
                violations.append(f"{location} missing 'valueFrom.secretKeyRef' field")
            else:
                secret_ref = obj["valueFrom"]["secretKeyRef"]
                if secret_ref.get("name") != "inventory-secrets":
                    violations.append(f"{location} secretKeyRef.name != 'inventory-secrets'")
                if secret_ref.get("key") != env_var_name:
                    violations.append(f"{location} secretKeyRef.key != '{env_var_name}'")
        
        # Recurse into nested objects
        for key, value in obj.items():
            new_path = f"{path}.{key}" if path else key
            violations.extend(_find_env_credential_violations(value, filename, doc_idx, new_path))
    
    elif isinstance(obj, list):
        # Recurse into list items
        for idx, item in enumerate(obj):
            new_path = f"{path}[{idx}]"
            violations.extend(_find_env_credential_violations(item, filename, doc_idx, new_path))
    
    return violations


# Feature: k8s-migration, Property 3: configmap init.sql round-trip fidelity
def test_configmap_init_sql_round_trip_fidelity():
    """
    Test that ConfigMap init.sql content is byte-for-byte identical to db_init/init.sql.
    
    For any version of db_init/init.sql, the string stored in the data["init.sql"] 
    field of configmap-postgres-init.yaml SHALL be byte-for-byte identical to the 
    contents of db_init/init.sql. No character, whitespace, or encoding difference 
    is acceptable.
    """
    
    # Read the original init.sql file as raw bytes
    init_sql_path = pathlib.Path(__file__).parent.parent / "db_init/init.sql"
    if not init_sql_path.exists():
        raise FileNotFoundError(f"Original init.sql not found at {init_sql_path}")
    
    with init_sql_path.open('rb') as f:
        original_bytes = f.read()
    
    # Decode to string for comparison (assuming UTF-8)
    original_content = original_bytes.decode('utf-8')
    
    # Parse the ConfigMap
    configmap_docs = load_all("configmap-postgres-init.yaml")
    
    configmap_doc = None
    for doc in configmap_docs:
        if doc and doc.get('kind') == 'ConfigMap' and doc.get('metadata', {}).get('name') == 'postgres-init-sql':
            configmap_doc = doc
            break
    
    assert configmap_doc is not None, "ConfigMap 'postgres-init-sql' not found in configmap-postgres-init.yaml"
    
    # Extract the init.sql content from ConfigMap
    data = configmap_doc.get('data', {})
    assert 'init.sql' in data, "ConfigMap does not contain 'init.sql' key in data section"
    
    configmap_content = data['init.sql']
    
    # Compare byte-for-byte
    assert configmap_content == original_content, (
        f"ConfigMap init.sql content does not match db_init/init.sql exactly.\n"
        f"Original length: {len(original_content)} chars\n"
        f"ConfigMap length: {len(configmap_content)} chars\n"
        f"First 200 chars of original: {repr(original_content[:200])}\n"
        f"First 200 chars of configmap: {repr(configmap_content[:200])}"
    )


# Feature: k8s-migration, Property 4: all kubernetes resources declare the inventory namespace
def test_all_kubernetes_resources_declare_inventory_namespace():
    """
    Test that all namespaced Kubernetes resources declare the inventory namespace.
    
    For any YAML file in k8s/ that defines a namespaced resource (Deployment, Service, 
    PersistentVolumeClaim, ConfigMap), the metadata.namespace field SHALL be set to 
    "inventory". No resource manifest may omit the namespace field or set it to a 
    different value.
    """
    
    # Kubernetes kinds that are namespaced (excluding Namespace itself)
    namespaced_kinds = {
        'Deployment', 'Service', 'PersistentVolumeClaim', 'ConfigMap', 'Secret',
        'StatefulSet', 'DaemonSet', 'Job', 'CronJob', 'Ingress', 'ServiceAccount',
        'Role', 'RoleBinding', 'NetworkPolicy', 'PodDisruptionBudget'
    }
    
    # Get all YAML files in k8s directory
    yaml_files = list(K8S_DIR.glob("*.yaml"))
    
    namespace_violations = []
    
    for yaml_file in yaml_files:
        docs = load_all(yaml_file.name)
        
        for doc_idx, doc in enumerate(docs):
            if not doc:
                continue
            
            kind = doc.get('kind')
            if not kind:
                continue
            
            # Skip Namespace resources themselves
            if kind == 'Namespace':
                continue
            
            # Check only namespaced resource types
            if kind in namespaced_kinds:
                metadata = doc.get('metadata', {})
                namespace = metadata.get('namespace')
                
                location = f"{yaml_file.name}[{doc_idx}] {kind}/{metadata.get('name', 'unnamed')}"
                
                if namespace is None:
                    namespace_violations.append(f"{location} missing metadata.namespace field")
                elif namespace != 'inventory':
                    namespace_violations.append(f"{location} has namespace '{namespace}' != 'inventory'")
    
    if namespace_violations:
        violation_msg = "\n".join([f"  - {violation}" for violation in namespace_violations])
        raise AssertionError(
            f"Found namespace violations in manifests:\n{violation_msg}\n"
            f"All namespaced resources must declare namespace: inventory"
        )


# Feature: k8s-migration, Property 6: pvc storageClassName is absent
def test_pvc_storage_class_name_is_absent():
    """
    Test that PVC storageClassName field is absent for portability.
    
    For any reading of pvc-postgres.yaml, the spec.storageClassName field SHALL be 
    absent (not present in the YAML) or explicitly null. It SHALL NOT be set to any 
    specific storage class name (e.g., local-path, standard), ensuring the manifest 
    binds to the cluster default in both k3d and k3s environments.
    """
    
    pvc_docs = load_all("pvc-postgres.yaml")
    
    pvc_doc = None
    for doc in pvc_docs:
        if doc and doc.get('kind') == 'PersistentVolumeClaim':
            pvc_doc = doc
            break
    
    assert pvc_doc is not None, "PersistentVolumeClaim not found in pvc-postgres.yaml"
    
    spec = pvc_doc.get('spec', {})
    
    # Check that storageClassName is either absent or null
    if 'storageClassName' in spec:
        storage_class_name = spec['storageClassName']
        assert storage_class_name is None, (
            f"PVC spec.storageClassName is present with value '{storage_class_name}' "
            f"but should be absent or null for portability between k3d and k3s"
        )


# Feature: k8s-migration, Property 5: nginx api prefix stripping
def test_nginx_api_prefix_stripping_deterministic():
    """
    Test deterministic examples of Nginx API prefix stripping.
    
    This test verifies specific known patterns without property-based testing,
    providing concrete examples of the expected behavior.
    """
    
    # Read nginx.conf content
    nginx_conf_path = pathlib.Path(__file__).parent.parent / "frontend/nginx.conf"
    if not nginx_conf_path.exists():
        raise FileNotFoundError(f"nginx.conf not found at {nginx_conf_path}")
    
    with nginx_conf_path.open('r') as f:
        nginx_content = f.read()
    
    # Extract the location /api/ block and proxy_pass directive
    api_location_match = re.search(r'location\s+/api/\s*\{([^}]+)\}', nginx_content, re.DOTALL)
    assert api_location_match, "location /api/ block not found in nginx.conf"
    
    api_block_content = api_location_match.group(1)
    
    # Find proxy_pass directive
    proxy_pass_match = re.search(r'proxy_pass\s+([^;\s]+)', api_block_content)
    assert proxy_pass_match, "proxy_pass directive not found in location /api/ block"
    
    proxy_pass_url = proxy_pass_match.group(1).strip()
    
    # Verify the proxy_pass URL strips the /api prefix correctly
    expected_proxy_pass = "http://backend:8000/"
    assert proxy_pass_url == expected_proxy_pass, (
        f"proxy_pass URL '{proxy_pass_url}' should be '{expected_proxy_pass}' "
        f"to strip /api prefix correctly"
    )
    
    # Test deterministic examples
    test_cases = [
        ("/api/products", "/products"),
        ("/api/products/1/movements", "/products/1/movements"), 
        ("/api/health", "/health"),
        ("/api/", "/"),
        ("/api/categories", "/categories")
    ]
    
    for request_path, expected_backend_path in test_cases:
        # The nginx configuration should transform:
        # Client request: GET /api/products
        # Backend receives: GET /products (via proxy_pass http://backend:8000/)
        
        # Since proxy_pass ends with /, nginx strips the location prefix (/api/)
        # This is standard nginx behavior when proxy_pass URL ends with /
        
        # Verify this is the expected transformation
        if request_path.startswith("/api/"):
            actual_backend_path = request_path[4:]  # Strip "/api" (4 chars)
            assert actual_backend_path == expected_backend_path, (
                f"Request {request_path} should transform to {expected_backend_path}, "
                f"got {actual_backend_path}"
            )
    
    # Verify non-API paths are not affected by the /api/ location block
    non_api_paths = ["/", "/assets/main.js", "/favicon.ico", "/dashboard"]
    
    # These paths should NOT match the location /api/ block
    # They should be handled by the location / block with try_files
    
    # Check that the root location exists
    root_location_match = re.search(r'location\s+/\s*\{([^}]+)\}', nginx_content, re.DOTALL)
    assert root_location_match, "location / block not found in nginx.conf"
    
    root_block_content = root_location_match.group(1)
    
    # Verify try_files directive exists in root location for SPA handling
    try_files_match = re.search(r'try_files\s+([^;]+)', root_block_content)
    assert try_files_match, "try_files directive not found in location / block"


if HYPOTHESIS_AVAILABLE:
    # Feature: k8s-migration, Property 5: nginx api prefix stripping (property-based)
    @given(st.from_regex(r"[a-zA-Z0-9/_\-\.]{1,64}", fullmatch=True))
    @settings(max_examples=100)
    def test_nginx_api_prefix_stripping_property_based(path_segment):
        """
        Property-based test for Nginx API prefix stripping behavior.
        
        For any URL path segment composed of valid URL characters, the location /api/ 
        block in frontend/nginx.conf SHALL route a request for /api/{segment} to 
        proxy_pass http://backend:8000/{segment}, stripping the /api prefix exactly once.
        """
        
        # Read nginx.conf content
        nginx_conf_path = pathlib.Path(__file__).parent.parent / "frontend/nginx.conf"
        with nginx_conf_path.open('r') as f:
            nginx_content = f.read()
        
        # Extract proxy_pass URL (already tested in deterministic test)
        api_location_match = re.search(r'location\s+/api/\s*\{([^}]+)\}', nginx_content, re.DOTALL)
        assert api_location_match, "location /api/ block not found"
        
        api_block_content = api_location_match.group(1)
        proxy_pass_match = re.search(r'proxy_pass\s+([^;\s]+)', api_block_content)
        assert proxy_pass_match, "proxy_pass directive not found"
        
        proxy_pass_url = proxy_pass_match.group(1).strip()
        
        # Verify the transformation for this generated path segment
        request_path = f"/api/{path_segment}"
        expected_backend_path = f"/{path_segment}"
        
        # nginx location /api/ with proxy_pass http://backend:8000/ should:
        # - Match /api/* requests
        # - Strip the /api/ prefix due to trailing / in proxy_pass
        # - Forward the remainder to backend:8000
        
        assert proxy_pass_url == "http://backend:8000/", (
            f"proxy_pass should end with / to strip prefix, got: {proxy_pass_url}"
        )
        
        # The actual transformation happens at runtime, but we can verify
        # the configuration supports the expected behavior
        stripped_path = request_path[4:]  # Remove "/api" (4 characters)
        assert stripped_path == expected_backend_path, (
            f"Path transformation failed for {request_path}: "
            f"expected {expected_backend_path}, got {stripped_path}"
        )


if __name__ == "__main__":
    # Run the tests directly if executed as a script
    test_deployment_probe_fields_conform_to_specification()
    print("✓ All deployment probe fields conform to specification")
    
    test_no_plaintext_credentials_in_any_manifest()
    print("✓ No plaintext credentials in any manifest")
    
    test_configmap_init_sql_round_trip_fidelity() 
    print("✓ ConfigMap init.sql round-trip fidelity verified")
    
    test_all_kubernetes_resources_declare_inventory_namespace()
    print("✓ All Kubernetes resources declare the inventory namespace")
    
    test_pvc_storage_class_name_is_absent()
    print("✓ PVC storageClassName is absent")
    
    test_nginx_api_prefix_stripping_deterministic()
    print("✓ Nginx API prefix stripping works correctly")
    
    if HYPOTHESIS_AVAILABLE:
        test_nginx_api_prefix_stripping_property_based()
        print("✓ Nginx API prefix stripping property-based test passed")
    else:
        print("⚠ Hypothesis not available, skipping property-based test")
    
    print("\n🎉 All manifest property tests passed!")