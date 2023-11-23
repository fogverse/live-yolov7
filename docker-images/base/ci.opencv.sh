docker buildx build \
    --platform linux/amd64,linux/arm64 \
    -t ariqbasyar/opencv:v4.8.1.78-py3.9.18 \
    -f docker-images/base/Dockerfile.opencv \
    --push .
