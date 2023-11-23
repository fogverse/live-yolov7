set -x
echo $DREG
docker buildx build \
    --platform linux/arm64 \
    --build-arg DREG=$DREG \
    -t ${DREG}ariqbasyar/fogverse:inference-gpu-jetson-sm \
    -f fog/jetson_nano/Dockerfile \
    --push .
