set -x
echo "$DREG"
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    -t ${DREG}ariqbasyar/fogverse:master \
    -f docker-images/master/Dockerfile \
    --push .
