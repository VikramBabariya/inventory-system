#!/bin/bash

# OCI A1.Flex Instance Creation Retry Script
# This script continuously attempts to create an A1.Flex instance until capacity becomes available
#
# Prerequisites:
# 1. OCI CLI installed and configured
# 2. SSH key generated at ~/.ssh/oci_inventory_key.pub
# 3. VCN and subnet created (run manual steps 1-4 first)
#
# Usage: ./scripts/oci-instance-retry.sh

set -e

# Configuration - UPDATE THESE VALUES
COMPARTMENT_OCID="ocid1.compartment.oc1..aaaa..."  # Replace with your compartment OCID
SUBNET_OCID="ocid1.subnet.oc1..aaaa..."           # Replace with your subnet OCID  
AD_NAME="your-AD-name"                             # Replace with your AD (e.g., "Uocm:AP-MUMBAI-1-AD-1")
SSH_KEY_FILE="$HOME/.ssh/oci_inventory_key.pub"
REGION="ap-mumbai-1"

# Instance configuration
DISPLAY_NAME="inventory-k3s-node"
SHAPE="VM.Standard.A1.Flex"
OCPUS=1
MEMORY_GB=6
BOOT_VOLUME_SIZE=50

# Retry configuration
RETRY_INTERVAL=1800  # 30 minutes between attempts (avoid rate limits)
MAX_ATTEMPTS=48      # Run for 24 hours maximum (48 * 30 min = 24 hours)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "OCI A1.Flex Instance Creation Retry Bot"
echo "========================================"
echo "Target: $SHAPE with $OCPUS OCPUs, ${MEMORY_GB}GB RAM"
echo "Compartment: $COMPARTMENT_OCID"
echo "Subnet: $SUBNET_OCID"
echo "AD: $AD_NAME"
echo "Max attempts: $MAX_ATTEMPTS (24 hours)"
echo "Retry interval: ${RETRY_INTERVAL}s (30 minutes)"
echo

# Validate prerequisites
echo "Validating prerequisites..."

# Check OCI CLI
if ! command -v oci &> /dev/null; then
    echo -e "${RED}ERROR: OCI CLI not installed. Install it first.${NC}"
    exit 1
fi

# Check SSH key
if [[ ! -f "$SSH_KEY_FILE" ]]; then
    echo -e "${RED}ERROR: SSH public key not found at $SSH_KEY_FILE${NC}"
    echo "Run: ssh-keygen -t rsa -b 4096 -C 'oci-inventory-k3s' -f ~/.ssh/oci_inventory_key"
    exit 1
fi

# Check OCI CLI config
if ! oci iam user get --user-id "$(oci iam user list --query 'data[0].id' --raw-output 2>/dev/null)" &>/dev/null; then
    echo -e "${RED}ERROR: OCI CLI not configured. Run: oci setup config${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites validated${NC}"
echo

# Get the Ubuntu 22.04 ARM64 image OCID for the region
echo "Looking up Ubuntu 22.04 ARM64 image..."
IMAGE_OCID=$(oci compute image list \
    --compartment-id "$COMPARTMENT_OCID" \
    --operating-system "Canonical Ubuntu" \
    --operating-system-version "22.04" \
    --shape "$SHAPE" \
    --query 'data[0].id' \
    --raw-output)

if [[ -z "$IMAGE_OCID" || "$IMAGE_OCID" == "null" ]]; then
    echo -e "${RED}ERROR: Could not find Ubuntu 22.04 ARM64 image for shape $SHAPE${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Found image: $IMAGE_OCID${NC}"
echo

# Test mode - validate configuration first
echo "Testing configuration validity..."
echo "Attempting dry-run validation..."

# Test compartment access
echo "→ Testing compartment access..."
if oci iam compartment get --compartment-id "$COMPARTMENT_OCID" >/dev/null 2>&1; then
    echo -e "${GREEN}  ✓ Compartment accessible${NC}"
else
    echo -e "${RED}  ✗ Cannot access compartment $COMPARTMENT_OCID${NC}"
    echo "  Check if the OCID is correct and you have permissions"
    exit 1
fi

# Test subnet access
echo "→ Testing subnet access..."
if oci network subnet get --subnet-id "$SUBNET_OCID" >/dev/null 2>&1; then
    echo -e "${GREEN}  ✓ Subnet accessible${NC}"
else
    echo -e "${RED}  ✗ Cannot access subnet $SUBNET_OCID${NC}"
    echo "  Check if the subnet OCID is correct"
    exit 1
fi

# Validate AD format
echo "→ Validating availability domain..."
if oci iam availability-domain list --compartment-id "$COMPARTMENT_OCID" --query "data[?name=='$AD_NAME'].name" --raw-output | grep -q "$AD_NAME"; then
    echo -e "${GREEN}  ✓ Availability domain exists${NC}"
else
    echo -e "${RED}  ✗ Availability domain '$AD_NAME' not found${NC}"
    echo "  Available ADs:"
    oci iam availability-domain list --compartment-id "$COMPARTMENT_OCID" --query 'data[*].name' --output table
    exit 1
fi

echo -e "${GREEN}✓ Configuration validation passed${NC}"
echo

# Start retry loop
attempt=1
start_time=$(date)

echo "Starting retry loop at $(date)"
echo "Press Ctrl+C to stop"
echo

while [[ $attempt -le $MAX_ATTEMPTS ]]; do
    echo -e "${YELLOW}Attempt $attempt/$MAX_ATTEMPTS at $(date)...${NC}"
    
    # Attempt to create the instance
    echo "Launching instance with parameters:"
    echo "  Compartment: $COMPARTMENT_OCID"
    echo "  AD: $AD_NAME"
    echo "  Shape: $SHAPE ($OCPUS OCPUs, ${MEMORY_GB}GB)"
    echo "  Image: $IMAGE_OCID"
    echo "  Subnet: $SUBNET_OCID"
    echo
    
    if oci compute instance launch \
        --compartment-id "$COMPARTMENT_OCID" \
        --availability-domain "$AD_NAME" \
        --shape "$SHAPE" \
        --shape-config "{\"ocpus\": $OCPUS, \"memoryInGBs\": $MEMORY_GB}" \
        --subnet-id "$SUBNET_OCID" \
        --image-id "$IMAGE_OCID" \
        --ssh-authorized-keys-file "$SSH_KEY_FILE" \
        --display-name "$DISPLAY_NAME" \
        --boot-volume-size-in-gbs "$BOOT_VOLUME_SIZE" \
        --assign-public-ip true \
        --region "$REGION" \
        --wait-for-state RUNNING \
        --max-wait-seconds 600 \
        > /tmp/oci-instance-creation.log 2>&1; then
        
        echo
        echo -e "${GREEN}🎉 SUCCESS! Instance created successfully!${NC}"
        echo "Started at: $start_time"
        echo "Completed at: $(date)"
        echo "Total attempts: $attempt"
        
        # Extract instance details
        INSTANCE_ID=$(grep '"id":' /tmp/oci-instance-creation.log | head -1 | sed 's/.*"id": "\([^"]*\)".*/\1/')
        echo "Instance ID: $INSTANCE_ID"
        
        # Get the public IP
        echo "Retrieving public IP address..."
        sleep 10  # Wait a moment for IP assignment
        PUBLIC_IP=$(oci compute instance list-vnics \
            --instance-id "$INSTANCE_ID" \
            --query 'data[0]."public-ip"' \
            --raw-output)
        
        if [[ -n "$PUBLIC_IP" && "$PUBLIC_IP" != "null" ]]; then
            echo -e "${GREEN}Public IP: $PUBLIC_IP${NC}"
            echo
            echo "Next steps:"
            echo "1. Test SSH access: ssh -i ~/.ssh/oci_inventory_key ubuntu@$PUBLIC_IP"
            echo "2. Update your runbook with this IP address"
            echo "3. Proceed to k3s installation (task 15)"
        else
            echo -e "${YELLOW}Instance created but public IP not yet available. Check OCI Console.${NC}"
        fi
        
        echo
        echo "Creation log saved to: /tmp/oci-instance-creation.log"
        exit 0
    else
        echo -e "${RED}✗ Instance creation failed${NC}"
        echo
        echo "Error details from OCI CLI:"
        if [[ -f /tmp/oci-instance-creation.log ]]; then
            cat /tmp/oci-instance-creation.log
        else
            echo "No log file found"
        fi
        echo
        
        # Try to extract specific error message
        error_msg=$(cat /tmp/oci-instance-creation.log 2>/dev/null | grep -i "ServiceError\|error\|capacity\|failed" | head -3 || echo "Unknown error")
        
        if echo "$error_msg" | grep -qi "out of capacity\|OutOfCapacity\|capacity"; then
            echo -e "${YELLOW}→ This is a capacity issue (expected). Retrying...${NC}"
        elif echo "$error_msg" | grep -qi "NotAuthorized\|Unauthorized"; then
            echo -e "${RED}→ Authorization error. Check your OCI CLI config and permissions.${NC}"
            echo "Try: oci iam user get --user-id \$(oci iam user list --query 'data[0].id' --raw-output)"
            exit 1
        elif echo "$error_msg" | grep -qi "InvalidParameter\|BadRequest"; then
            echo -e "${RED}→ Invalid parameter error. Check your OCIDs and configuration.${NC}"
            echo "Verify:"
            echo "  - Compartment OCID: $COMPARTMENT_OCID"
            echo "  - Subnet OCID: $SUBNET_OCID"  
            echo "  - AD Name: $AD_NAME"
            exit 1
        elif echo "$error_msg" | grep -qi "TooManyRequests\|rate.*limit\|throttle"; then
            echo -e "${YELLOW}→ API rate limit hit. Increasing wait time...${NC}"
            echo "Sleeping for 45 minutes to avoid rate limits..."
            sleep 2700  # 45 minutes
            continue  # Skip the normal sleep and try again
        elif echo "$error_msg" | grep -qi "LimitExceeded"; then
            echo -e "${RED}→ Service limit exceeded. You may have reached Always Free limits.${NC}"
            exit 1
        else
            echo -e "${YELLOW}→ Unexpected error. Retrying anyway...${NC}"
        fi
        
        if [[ $attempt -eq $MAX_ATTEMPTS ]]; then
            echo
            echo -e "${RED}Maximum attempts reached. Giving up after 24 hours.${NC}"
            echo "Final error log:"
            cat /tmp/oci-instance-creation.log 2>/dev/null || echo "No log available"
            echo
            echo "You may want to:"
            echo "1. Try again later"
            echo "2. Consider creating a new OCI account with a different home region"
            echo "3. Try with reduced OCPUs (1 OCPU, 6GB RAM) first"
            exit 1
        fi
        
        echo "Sleeping for ${RETRY_INTERVAL}s (30 minutes) before next attempt..."
        sleep $RETRY_INTERVAL
    fi
    
    ((attempt++))
done