# Kubernetes Manifest Property Tests

This directory contains property-based tests for Kubernetes manifests that validate structural correctness without requiring a running cluster.

## Setup

1. Create a virtual environment:
   ```bash
   python3 -m venv test_venv
   source test_venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r tests/requirements.txt
   ```

## Running Tests

### Direct execution:
```bash
cd tests && python3 test_k8s_manifests.py
```

### With pytest (recommended):
```bash
pytest tests/test_k8s_manifests.py -v
```

## Test Coverage

The tests implement 6 correctness properties from the k8s-migration design:

1. **Property 1**: All deployment probe fields conform to specification
2. **Property 2**: No plaintext credentials in any manifest  
3. **Property 3**: ConfigMap init.sql round-trip fidelity
4. **Property 4**: All Kubernetes resources declare the inventory namespace
5. **Property 5**: Nginx API prefix stripping (deterministic + property-based)
6. **Property 6**: PVC storageClassName is absent

## Files Tested

- `k8s/*.yaml` - All Kubernetes manifest files
- `frontend/nginx.conf` - Nginx configuration for API proxying
- `db_init/init.sql` - Original SQL initialization script

## Dependencies

- **pytest**: Test framework
- **PyYAML**: YAML parsing and validation
- **hypothesis**: Property-based testing (for Property 5)

## Expected Output

When all tests pass:
```
✓ All deployment probe fields conform to specification
✓ No plaintext credentials in any manifest
✓ ConfigMap init.sql round-trip fidelity verified
✓ All Kubernetes resources declare the inventory namespace
✓ PVC storageClassName is absent
✓ Nginx API prefix stripping works correctly
✓ Nginx API prefix stripping property-based test passed

🎉 All manifest property tests passed!
```