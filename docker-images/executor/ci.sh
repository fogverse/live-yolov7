set -x
echo "$DREG"
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    -t ${DREG}ariqbasyar/fogbus2-fogverse:base-CCTVInference \
    -f docker-images/executor/Dockerfile \
    --push .
docker pull ${DREG}ariqbasyar/fogbus2-fogverse:base-CCTVInference
