import json
import uuid
import logging
from proton_driver import client

db_logger = logging.getLogger("database")

class MutableStreamPipelineManager:
    def __init__(self, timeplus_client, pipeline_stream_name="synthetic_data_pipelines"):
        """Initialize mutable stream-based pipeline manager"""
        db_logger.info("Initializing MutableStreamPipelineManager")
        self.client = timeplus_client
        self.pipeline_stream_name = pipeline_stream_name
        self._init_database()
        
    def _init_database(self):
        """Initialize the mutable stream for storing pipeline metadata"""
        db_logger.info(f"Initializing pipeline metadata stream: {self.pipeline_stream_name}")
        
        try:
            create_sql = f"""CREATE MUTABLE STREAM IF NOT EXISTS {self.pipeline_stream_name} (
                id string,
                name string,
                pipeline string
            )
            PRIMARY KEY (id)
            """
            
            db_logger.debug(f"Executing DDL: {create_sql}")
            self.client.execute(create_sql)
            db_logger.info("Pipeline metadata stream initialized successfully")
            
        except Exception as e:
            db_logger.error(f"Failed to initialize pipeline metadata stream: {e}")
            raise RuntimeError(f"Failed to initialize pipeline metadata stream: {e}")

    def create(self, pipeline, name):
        """Create a new pipeline entry in mutable stream"""
        pipeline_id = uuid.uuid4().hex
        db_logger.info(f"Creating pipeline with ID: {pipeline_id}, name: {name}")
        
        try:
            # Convert pipeline to JSON string
            pipeline_json = json.dumps(pipeline, indent=2)
            
            # Insert new pipeline
            insert_sql = f"INSERT INTO {self.pipeline_stream_name} (id, name, pipeline) VALUES"
            values = [[pipeline_id, name, pipeline_json]]
            
            db_logger.debug(f"Executing insert: {insert_sql}")
            db_logger.debug(f"Values: id={pipeline_id}, name={name}, pipeline_length={len(pipeline_json)}")
            
            self.client.execute(insert_sql, values)
            db_logger.info(f"Pipeline saved successfully with ID: {pipeline_id}")
            return pipeline_id
            
        except Exception as e:
            db_logger.error(f"Failed to create pipeline: {e}")
            raise RuntimeError(f"Failed to create pipeline: {e}")

    def get(self, pipeline_id):
        """Get a specific pipeline by ID from mutable stream"""
        db_logger.info(f"Retrieving pipeline with ID: {pipeline_id}")
        
        try:
            # Query for the pipeline
            query_sql = f"SELECT name, pipeline FROM table({self.pipeline_stream_name}) WHERE id = '{pipeline_id}'"
            db_logger.debug(f"Executing query: {query_sql}")
            
            result = self.client.execute(query_sql)
            db_logger.debug(f"Query result: {len(result) if result else 0} rows")
            
            if result:
                name = result[0][0]
                pipeline_json = result[0][1]
                
                db_logger.debug(f"Found pipeline: name={name}, json_length={len(pipeline_json)}")
                
                try:
                    pipeline_data = json.loads(pipeline_json)
                    db_logger.info(f"Successfully retrieved pipeline from mutable stream: {name}")
                    
                    return {
                        "id": pipeline_id,
                        "name": name,
                        "pipeline": pipeline_data,
                        "write_count": 0  # Will be updated by caller if needed
                    }
                except json.JSONDecodeError as e:
                    db_logger.error(f"Failed to parse pipeline JSON: {e}")
                    db_logger.debug(f"Malformed JSON: {pipeline_json}")
                    raise RuntimeError(f"Failed to parse pipeline data: {e}")
            else:
                db_logger.warning(f"Pipeline with id {pipeline_id} not found")
                raise ValueError(f"Pipeline with id {pipeline_id} not found.")
                
        except ValueError:
            # Re-raise ValueError for not found
            raise
        except Exception as e:
            db_logger.error(f"Failed to retrieve pipeline {pipeline_id}: {e}")
            raise RuntimeError(f"Failed to get pipeline: {e}")

    def list_all(self):
        """List all pipelines from mutable stream"""
        db_logger.info("Listing all pipelines")
        
        try:
            # Query for all pipelines
            query_sql = f"SELECT id, name, pipeline FROM table({self.pipeline_stream_name})"
            db_logger.debug(f"Executing query: {query_sql}")
            
            result = self.client.execute(query_sql)
            db_logger.info(f"Found {len(result) if result else 0} pipelines")
            
            pipelines = []
            for i, row in enumerate(result):
                try:
                    pipeline_id, name, pipeline_json = row
                    pipeline_data = json.loads(pipeline_json)
                    
                    pipeline_info = {
                        "id": pipeline_id,
                        "name": name,
                        "question": pipeline_data.get("question", ""),
                        "created_at": pipeline_data.get("created_at", "")
                    }
                    pipelines.append(pipeline_info)
                    
                    db_logger.debug(f"Pipeline {i}: {pipeline_id} - {name}")
                    
                except Exception as e:
                    db_logger.error(f"Failed to parse pipeline {i}: {e}")
                    continue
            
            db_logger.info(f"Successfully processed {len(pipelines)} pipelines from mutable stream")
            return pipelines
            
        except Exception as e:
            db_logger.error(f"Failed to list pipelines: {e}")
            raise RuntimeError(f"Failed to list pipelines: {e}")

    def delete(self, pipeline_id):
        """Delete a pipeline by ID from mutable stream"""
        db_logger.info(f"Deleting pipeline metadata with ID: {pipeline_id}")
        
        try:
            # Delete the pipeline metadata
            delete_sql = f"DELETE FROM {self.pipeline_stream_name} WHERE id = '{pipeline_id}'"
            db_logger.debug(f"Executing: {delete_sql}")
            
            self.client.execute(delete_sql)
            db_logger.info(f"Pipeline metadata deleted successfully from mutable stream")
            
        except Exception as e:
            db_logger.error(f"Failed to delete pipeline metadata {pipeline_id}: {e}")
            raise RuntimeError(f"Failed to delete pipeline metadata: {e}")

    def update_write_count(self, pipeline_id, count):
        """Update write count - not implemented for mutable stream (handled externally)"""
        # Note: Mutable stream doesn't store write_count directly
        # It's calculated on-the-fly by the calling code
        db_logger.debug(f"Write count update requested for pipeline {pipeline_id}: {count}")
        pass
