#!/bin/bash

# OCI Configuration Helper Script
# This script helps you gather the required OCIDs for the retry script

set -e

echo "========================================"
echo "OCI Configuration Helper"
echo "========================================"
echo "This script will help you gather the required OCIDs"
echo

# Check OCI CLI
if ! command -v oci &> /dev/null; then
    echo "ERROR: OCI CLI not installed. Install it first."
    echo "Visit: https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/cliinstall.htm"
    exit 1
fi

echo "1. Getting your User OCID..."
USER_OCID=$(oci iam user list --query 'data[0].id' --raw-output 2>/dev/null || echo "")
if [[ -n "$USER_OCID" ]]; then
    echo "   User OCID: $USER_OCID"
else
    echo "   Could not retrieve user OCID. Is OCI CLI configured? Run: oci setup config"
    exit 1
fi

echo
echo "2. Getting your Tenancy OCID..."
TENANCY_OCID=$(oci iam user get --user-id "$USER_OCID" --query 'data."compartment-id"' --raw-output 2>/dev/null || echo "")
if [[ -n "$TENANCY_OCID" && "$TENANCY_OCID" != "null" ]]; then
    echo "   Tenancy OCID: $TENANCY_OCID"
else
    echo "   Could not retrieve tenancy OCID"
fi

echo
echo "3. Listing your compartments..."
echo "   Available compartments:"
oci iam compartment list --compartment-id "$TENANCY_OCID" --query 'data[*].{Name:name, OCID:id}' --output table 2>/dev/null || echo "   Could not list compartments"

echo
echo "4. Getting your home region..."
HOME_REGION=$(oci iam region-subscription list --query 'data[?is_home_region == `true`]."region_name" | [0]' --raw-output 2>/dev/null || echo "")
if [[ -n "$HOME_REGION" && "$HOME_REGION" != "null" ]]; then
    echo "   Home region: $HOME_REGION"
else
    echo "   Could not determine home region. Trying alternative method..."
    # Alternative method - get current config region
    HOME_REGION=$(oci iam region list --query 'data[0]."name"' --raw-output 2>/dev/null || echo "")
    if [[ -n "$HOME_REGION" && "$HOME_REGION" != "null" ]]; then
        echo "   Current configured region: $HOME_REGION (may be home region)"
    else
        echo "   Could not determine region. Please check: oci iam region-subscription list"
    fi
fi

echo
echo "5. Listing availability domains in your home region..."
if [[ -n "$HOME_REGION" && "$HOME_REGION" != "null" ]]; then
    echo "   Available ADs:"
    oci iam availability-domain list --compartment-id "$TENANCY_OCID" --query 'data[*].name' --output table 2>/dev/null || {
        echo "   Could not list ADs. Trying raw output..."
        oci iam availability-domain list --compartment-id "$TENANCY_OCID" --query 'data[*].name' --raw-output 2>/dev/null | nl -nln || echo "   Failed to get AD list"
    }
else
    echo "   Skipping AD list (no region found)"
fi

echo
echo "6. Alternative: Get current region from config..."
CONFIG_REGION=$(grep "region" ~/.oci/config 2>/dev/null | head -1 | cut -d'=' -f2 | tr -d ' ' || echo "not found")
echo "   Config file region: $CONFIG_REGION"

echo
echo "========================================"
echo "Troubleshooting:"
echo "========================================"
echo "If information is missing above, try these manual commands:"
echo
echo "# Get home region manually"
echo "oci iam region-subscription list"
echo
echo "# Get availability domains manually (replace with your tenancy OCID)"
echo "oci iam availability-domain list --compartment-id <your_tenancy_ocid>"
echo
echo "# List compartments manually (replace with your tenancy OCID)" 
echo "oci iam compartment list --compartment-id <your_tenancy_ocid>"
echo
echo "========================================"
echo "Manual Steps Needed:"
echo "========================================"
echo "1. Create your VCN and subnet using the OCI Console (follow the runbook)"
echo "2. Copy the Subnet OCID from the OCI Console → Networking → Virtual Cloud Networks → Your VCN → Subnets"
echo "3. Update the retry script with these values:"
echo
echo "   COMPARTMENT_OCID=\"YOUR_COMPARTMENT_OCID\"  # Pick one from the list above"
echo "   SUBNET_OCID=\"YOUR_SUBNET_OCID\"            # From OCI Console after creating subnet"
echo "   AD_NAME=\"YOUR_AD_NAME\"                    # Pick one from the ADs listed above"
echo "   REGION=\"${HOME_REGION:-YOUR_HOME_REGION}\" # Your home region (replace if not detected)"
echo
echo "Then run: ./scripts/oci-instance-retry.sh"