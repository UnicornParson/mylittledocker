source .env
if [ -z "$GERRIT_HOME" ]; then
    echo "empty GERRIT_HOME variable. check your .env file" && exit 1
fi
echo "home: $GERRIT_HOME" 
mkdir -p $GERRIT_HOME/git
mkdir -p $GERRIT_HOME/index
mkdir -p $GERRIT_HOME/cache
docker-compose up -d