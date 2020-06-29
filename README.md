# Kafka for your data pipeline
## Project summary
Kafka has risen in popularity lately as businesses rely on it to power mission-critical applications and data pipelines.  

In this project, we will simulate a streaming ingestion pipeline using Kafka, and Kafka connect. Assuming we have our production database running on Postgres and we want to stream the Users table that contains customer data to different sources for different purposes. Kafka and Kafka Connect is perfect for this use case. In our simulation, we will write data to MySQL for other applications and S3 for our data lake ingestion.

## Project architecture
![architecture](/images/architecture.png)
For our example, we will use Kafka connect to capture changes in the Users table from our production database on-premise and write to a Kafka topic. Two connectors will subscribe to the topic above, and write any changes to our email service's MySQL database as well as the S3, our data lake.
## Instructions
### Clone the repo to your local machine


### Install docker and docker-compose
We will use docker and docker-compose for this project, and you can quickly lookup how to install them for your OS.

### Create an environment
Assuming you already have conda installed, you can create a new env and install the required packages by running:
```
conda create -n kafka-pipeline python=3.7 -y
conda activate kafka-pipeline
pip install -r requirements.txt
```
We will need PostgreSQL to connect to our source database (Postgres) and generate the streaming data. On Mac OS, you can install Postgresql using Homebrew by running:
```
brew install PostgreSQL
```
You can google how to install Postgresql for other platforms
### Start the production database (Postgres)
We use docker-compose to start services with minimum effort. You can start the Postgres production database using:
```
docker-compose -f docker-compose-pg.yml up -d
```
Your Postgres database should be running on port 5432, and you can check the status of the container by typing `docker ps` to a terminal.
### Generate streaming data
I have written a short script to generate user data using the Faker library. The script will generate one record per second to our Postgres database, simulating a production database. You can run the script in a separate terminal tab using:
```
python generate_data.py
```
If everything is set up correctly, you will see outputs like so:
```
Inserting data {'job': 'Physiotherapist', 'company': 'Miller LLC', 'ssn': '097-38-8791', 'residence': '421 Dustin Ramp Apt. 793\nPort Luis, AR 69680', 'username': 'terri24', 'name': 'Sarah Moran', 'sex': 'F', 'address': '906 Andrea Springs\nWest Tylerberg, ID 29968', 'mail': 'nsmith@hotmail.com', 'birthdate': datetime.date(1917, 6, 3), 'timestamp': datetime.datetime(2020, 6, 29, 11, 20, 20, 355755)}
```
### Start our Kafka broker
Great, now that we have a production database running with data streaming to it, let's start the main components of our simulation. We will be running the following services:
- Kafka broker: Kafa broker receives messages from producers and stores them by unique offset. The broker will also allow consumers to fetch messages by a topic, partition, and offset.
- Zookeeper: Zookeeper keeps track of the status of Kafka cluster nodes as well as Kafka topics and partitions
- Schema registry: Schema registry is a layer that will fetch and server your metadata (data about data) such as data type, precision, scale... and provides compatibility settings between different services.
- Kafka Connect: Kafka Connect is a framework for connecting Kafka with external systems such as databases, key-value stores, search indexes, and file systems.
- Kafdrop: Kafdrop is an opensource web UI fro viewing Kafka topics and browsing consumer groups. This will make inspecting and debugging our messages much easier.  

We can start all of these services by running:
```
docker-compose -f docker-compose-kafka.yml up -d
```
Wait a few minutes for the services to start up, and you can proceed to the next step. You can view logs outputs using:
```
docker-compose -f docker-compose-kafka.yml logs -f
```

### Configure source connector
There are two types of connectors in Kafka Connect Source connector and Sink connector. The names itself are self-explanatory. We will configure our source connector to our production database (Postgres) using the Kafka connect rest API.
```
curl -i -X PUT http://localhost:8083/connectors/SOURCE_POSTGRES/config \
     -H "Content-Type: application/json" \
     -d '{
            "connector.class":"io.confluent.connect.jdbc.JdbcSourceConnector",
            "connection.url":"jdbc:postgresql://postgres:5432/TEST",
            "connection.user":"TEST",
            "connection.password":"password",
            "poll.interval.ms":"1000",
            "mode":"incrementing",
            "incrementing.column.name":"index",
            "topic.prefix":"P_",
            "table.whitelist":"USERS",
            "validate.non.null":"false"
        }'

```
When you see `HTTP/1.1 201 Created`, the connector is successfully created.
What this command does is sending a JSON message with our configurations to the Kafka Connect instance. I will explain some of the configurations here, but you can reference the full list of configs [here](https://docs.confluent.io/current/connect/kafka-connect-jdbc/source-connector/source_config_options.html)
- `connector.class`: we are using the JDBC source connector to connect to our production database and extract data.
- `connection.url`: the connection string to our source database. Since we are using the docker's internal network, the database address is Postgres. If you are connecting to external databases, replace Postgres with the database's IP.
- `connection.user` & `connection.password`:  credentials for our database
- `poll.interval.ms`: frequency to poll for new data. We are polling every second.
- `mode`: the mode for updating each table when it is polled. We are using an incremental key (index), but we can also update using a timestamp or bulk update.
- `topic.prefix`: the prefix of the topic to write data to in Kafka
- `table.whitelist`: list of table names to look for in our database. You can also set the `query` parameter to use a custom query.

With the Kafdrop instance running, you can open a browser and go to `localhost:9000` to see our `P_USERS` topic.
![kafdrop1](/images/kafdrop1.png)
You can go into the topic and see some sample messages on our topic.
![kafdrop2](/images/kafdrop2.png)
### Create sink connectors
We will create two sink connectors (Mysql and S3) with our data already in Kafka. Let's start first with Mysql. Start the Mysql database by running:
```
docker-compose -f docker-compose-mysql.yml up -d
```
Here is our configuration:
```
curl -i -X PUT http://localhost:8083/connectors/SINK_MYSQL/config \
     -H "Content-Type: application/json" \
     -d '{
               "connector.class":"io.confluent.connect.jdbc.JdbcSinkConnector",
               "tasks.max":1,
               "topics":"P_USERS",
           "insert.mode":"insert",
               "connection.url":"jdbc:mysql://mysql:3306/TEST",
               "connection.user":"TEST",
               "connection.password":"password",
               "auto.create":true
         }'
```
That's it. Your generated data should now be streaming from Postgres to Mysql. Let's go over the properties of the Mysql sink connector:
- `insert.mode`: How to insert data to the database. You can choose between `insert` and `upsert`.
- `topics`: The topic to read data from
- `connection.url`: Sink connection URL
- `connection.user` & `connection.password`: Sink credentials
- `auto.create`: Auto-create table if not exits

To write data to S3, it is equally easy and straight forward. You will need to setup environment variables: `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` in the `docker-compose-kafka.yml` file. After that you can create a S3 connector using the following configs:

```
curl -i -X PUT -H "Accept:application/json" \
    -H  "Content-Type:application/json" http://localhost:8083/connectors/SINK_S3/config \
    -d '
{
    "connector.class": "io.confluent.connect.s3.S3SinkConnector",
    "s3.region": "ap-southeast-1",
    "s3.bucket.name": "bucket-name",
    "topics": "P_USERS",
    "flush.size": "5",
    "timezone": "UTC",
    "tasks.max": "1",
    "value.converter.value.subject.name.strategy": "io.confluent.kafka.serializers.subject.RecordNameStrategy",
    "locale": "US",
    "format.class": "io.confluent.connect.s3.format.json.JsonFormat",
    "partitioner.class": "io.confluent.connect.storage.partitioner.DefaultPartitioner",
    "internal.value.converter": "org.apache.kafka.connect.json.JsonConverter",
    "storage.class": "io.confluent.connect.s3.storage.S3Storage",
    "rotate.schedule.interval.ms": "6000"
}'
```
Some notable configs:
- `s3.region`: region of your S3 bucket
- `s3.bucket.name`: bucket name to write data to
- `topics`: topics to read data from
- `format.class`: data format. You can choose from `JSON`, `Avro` and `Parquet`

And voila, your pipeline is now complete. With a couple of docker-compose configurations files and connectors configurations, you have created a streaming pipeline that enables near real-time data analytics capability. Pretty powerful stuff! Kafka and its components are horizontally scalable. You can add more components to process real-time data such as Spark Streaming, KSQL, Beam, or Flink.

## Clean up
If you don't have any other docker containers running, you can shut down the ones for this project with the following command:
```
docker stop $(docker ps -aq)
```
Optionally, you can clean up docker images downloaded locally by rinning:
```
docker system prune
```
