set -x
echo $DREG
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    --build-arg DREG=$DREG \
    -t ${DREG}ariqbasyar/pytorch:v2.1.1-py3.9.18 \
    -f docker-images/base/Dockerfile.pytorch \
    --push .