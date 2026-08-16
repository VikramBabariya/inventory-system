#!/bin/bash

# Single attempt OCI A1.Flex instance creation (no retry loop)
# Use this for manual testing or when rate limits are a concern

set -e

# Configuration - UPDATE THESE VALUES
COMPARTMENT_OCID="ocid1.compartment.oc1..aaaa..."  # Replace with your compartment OCID
SUBNET_OCID="ocid1.subnet.oc1..aaaa..."           # Replace with your subnet OCID
AD_NAME="your-AD-name"                             # Replace with your AD
SSH_KEY_FILE="$HOME/.ssh/oci_inventory_key.pub"
REGION="ap-mumbai-1"

# Instance configuration
DISPLAY_NAME="inventory-k3s-node"
SHAPE="VM.Standard.A1.Flex"
OCPUS=2
MEMORY_GB=12
BOOT_VOLUME_SIZE=50

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================="
echo "OCI A1.Flex Instance Creation (Single Try)"
echo "========================================="
echo "Target: $SHAPE with $OCPUS OCPUs, ${MEMORY_GB}GB RAM"
echo "Time: $(date)"
echo

# Get Ubuntu 22.04 ARM64 image
echo "Looking up Ubuntu 22.04 ARM64 image..."
IMAGE_OCID=$(oci compute image list \
    --compartment-id "$COMPARTMENT_OCID" \
    --operating-system "Canonical Ubuntu" \
    --operating-system-version "22.04" \
    --shape "$SHAPE" \
    --query 'data[0].id' \
    --raw-output)

if [[ -z "$IMAGE_OCID" || "$IMAGE_OCID" == "null" ]]; then
    echo -e "${RED}ERROR: Could not find Ubuntu 22.04 ARM64 image${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Found image: $IMAGE_OCID${NC}"
echo

# Single attempt
echo -e "${YELLOW}Attempting to create instance...${NC}"
echo "Parameters:"
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
    --max-wait-seconds 600; then
    
    echo
    echo -e "${GREEN}🎉 SUCCESS! Instance created successfully!${NC}"
    
else
    echo
    echo -e "${RED}✗ Instance creation failed${NC}"
    echo "This is normal if there's no capacity. Try again later manually or use the retry script."
    exit 1
fi