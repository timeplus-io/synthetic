
CREATE EXTERNAL STREAM kafka_extrenal_stream_name
    (value string)
SETTINGS
    type='kafka', 
    brokers='broker_ip:9092',
    topic='topic_name';

CREATE MATERIALIZED VIEW kafka_materialized_view_name
    INTO kafka_extrenal_stream_name
AS
    SELECT json_encode(*)
    FROM random_stream_name
    WHERE value IS NOT NULL;