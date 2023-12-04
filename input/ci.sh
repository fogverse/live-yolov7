set -x
echo $DREG
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    --build-arg DREG=$DREG \
    -t ${DREG}ariqbasyar/fogbus2-fogverse:user-0 \
    -f Dockerfile \
    --push ..
docker pull ${DREG}ariqbasyar/fogbus2-fogverse:user-0
