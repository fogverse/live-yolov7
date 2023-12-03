set -x
echo "$DREG"
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    -t ${DREG}ariqbasyar/fogbus2-fogverse:base-user \
    -f docker-images/input/Dockerfile \
    --push .
docker pull ${DREG}ariqbasyar/fogbus2-fogverse:base-user
