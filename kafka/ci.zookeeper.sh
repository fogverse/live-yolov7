set -x
echo $DREG
IMAGE_NAME=bitnami/zookeeper:3.8
NEW_TAG=${DREG}ariqbasyar/fogverse:kafka-zookeeper-3.8
docker pull $IMAGE_NAME
docker tag $IMAGE_NAME $NEW_TAG
docker push $NEW_TAG
