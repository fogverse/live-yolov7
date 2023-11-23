docker buildx build \
    --platform linux/amd64,linux/arm64 \
    -t ariqbasyar/pytorch:py3.9.18 \
    -f docker-images/base/Dockerfile.pytorch \
    --push .
