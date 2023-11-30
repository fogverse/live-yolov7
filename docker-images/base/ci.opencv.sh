set -x
echo $DREG
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    --build-arg DREG=$DREG \
    -t ${DREG}ariqbasyar/opencv:v4.8.1.78-py3.9.18 \
    -f docker-images/base/Dockerfile.opencv \
    --push .
