SCHEME=$1
FRAMEWORK=$2

INTERVAL=5
OUTNAME=analysis/$SCHEME/$FRAMEWORK/$(date +"stats_%d-%m-%Y_%H-%M-%S.txt")
mkdir -p "${OUTNAME%/*}"
echo $OUTNAME

update_file() {
  echo $(date +'%s.%N') | tee --append $OUTNAME;
  docker stats --no-stream --format "table {{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.NetIO}},{{.BlockIO}},{{.PIDs}}" | tee --append $OUTNAME;
  echo "" | tee --append $OUTNAME;
}

while true;
do
  update_file & sleep $INTERVAL;
done