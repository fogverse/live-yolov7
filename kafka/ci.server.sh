set -x
echo $DREG
IMAGE_NAME=${DREG}ariqbasyar/fogverse:kafka-server-3.1
docker build \
    -t $IMAGE_NAME \
    -f kafka/Dockerfile.server .
docker push $IMAGE_NAME
