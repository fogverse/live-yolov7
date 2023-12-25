echo SCHEME=$SCHEME
echo MODEL=$MODEL

gcloud compute instances create \
    $INSTANCE_NAME \
        --project=REDACTED \
        --zone=REDACTED \
        --machine-type=e2-highcpu-2 \
        --network-interface=network-tier=PREMIUM,stack-type=IPV4_ONLY,subnet=default \
        --maintenance-policy=MIGRATE \
        --provisioning-model=STANDARD \
        --service-account=REDACTED \
        --scopes=https://www.googleapis.com/auth/devstorage.read_only,https://www.googleapis.com/auth/logging.write,https://www.googleapis.com/auth/monitoring.write,https://www.googleapis.com/auth/servicecontrol,https://www.googleapis.com/auth/service.management.readonly,https://www.googleapis.com/auth/trace.append \
        --create-disk=auto-delete=yes,boot=yes,device-name=$INSTANCE_NAME,image=projects/ml-images/global/images/c2-deeplearning-pytorch-2-0-gpu-v20231209-debian-11,mode=rw,size=50,type=projects/REDACTED/zones/asia-southeast2-a/diskTypes/pd-standard \
        --no-shielded-secure-boot \
        --shielded-vtpm \
        --shielded-integrity-monitoring \
        --labels=goog-ec-src=vm_add-gcloud \
        --reservation-affinity=any
