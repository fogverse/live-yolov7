set -x
echo $DREG
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    --build-arg DREG=$DREG \
    -t ${DREG}ariqbasyar/fogverse:input \
    -f input/Dockerfile \
    --push .
