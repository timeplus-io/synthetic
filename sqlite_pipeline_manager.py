import sqlite3
import json
import uuid
import logging
from pathlib import Path

db_logger = logging.getLogger("database")

class SQLitePipelineManager:
    def __init__(self, db_file="pipelines.db"):
        """Initialize SQLite-based pipeline manager"""
        db_logger.info("Initializing SQLitePipelineManager")
        self.db_file = Path(db_file)
        self._init_database()
        
    def _init_database(self):
        """Initialize the SQLite database and create tables if they don't exist"""
        db_logger.info(f"Initializing database: {self.db_file}")
        
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                
                # Create pipelines table
                create_table_sql = """
                CREATE TABLE IF NOT EXISTS pipelines (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    pipeline_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    write_count INTEGER DEFAULT 0
                )
                """
                
                cursor.execute(create_table_sql)
                conn.commit()
                db_logger.info("Database initialized successfully")
                
        except Exception as e:
            db_logger.error(f"Failed to initialize database: {e}")
            raise RuntimeError(f"Failed to initialize database: {e}")
    
    def _get_connection(self):
        """Get a database connection"""
        return sqlite3.connect(self.db_file)

    def create(self, pipeline, name):
        """Create a new pipeline entry"""
        pipeline_id = uuid.uuid4().hex
        db_logger.info(f"Creating pipeline with ID: {pipeline_id}, name: {name}")
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Convert pipeline to JSON string
                pipeline_json = json.dumps(pipeline, indent=2)
                
                # Insert new pipeline
                insert_sql = """
                INSERT INTO pipelines (id, name, pipeline_json, write_count)
                VALUES (?, ?, ?, ?)
                """
                
                cursor.execute(insert_sql, (pipeline_id, name, pipeline_json, 0))
                conn.commit()
                
                db_logger.info(f"Pipeline saved successfully with ID: {pipeline_id}")
                return pipeline_id
                
        except Exception as e:
            db_logger.error(f"Failed to create pipeline: {e}")
            raise RuntimeError(f"Failed to create pipeline: {e}")

    def get(self, pipeline_id):
        """Get a specific pipeline by ID"""
        db_logger.info(f"Retrieving pipeline with ID: {pipeline_id}")
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Query for the pipeline
                select_sql = """
                SELECT name, pipeline_json, write_count
                FROM pipelines
                WHERE id = ?
                """
                
                cursor.execute(select_sql, (pipeline_id,))
                result = cursor.fetchone()
                
                if not result:
                    db_logger.warning(f"Pipeline with id {pipeline_id} not found")
                    raise ValueError(f"Pipeline with id {pipeline_id} not found.")
                
                name, pipeline_json, write_count = result
                
                # Parse JSON
                pipeline_data = json.loads(pipeline_json)
                
                db_logger.info(f"Successfully retrieved pipeline: {name}")
                
                return {
                    "id": pipeline_id,
                    "name": name,
                    "pipeline": pipeline_data,
                    "write_count": write_count or 0
                }
                
        except ValueError:
            # Re-raise ValueError for not found
            raise
        except Exception as e:
            db_logger.error(f"Failed to retrieve pipeline {pipeline_id}: {e}")
            raise RuntimeError(f"Failed to get pipeline: {e}")

    def list_all(self):
        """List all pipelines"""
        db_logger.info("Listing all pipelines")
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Query for all pipelines
                select_sql = """
                SELECT id, name, pipeline_json, created_at
                FROM pipelines
                ORDER BY created_at DESC
                """
                
                cursor.execute(select_sql)
                results = cursor.fetchall()
                
                pipelines = []
                for row in results:
                    try:
                        pipeline_id, name, pipeline_json, created_at = row
                        pipeline_data = json.loads(pipeline_json)
                        
                        pipeline_info = {
                            "id": pipeline_id,
                            "name": name,
                            "question": pipeline_data.get("question", ""),
                            "created_at": created_at or ""
                        }
                        pipelines.append(pipeline_info)
                        
                    except Exception as e:
                        db_logger.error(f"Failed to parse pipeline {pipeline_id}: {e}")
                        continue
                
                db_logger.info(f"Found {len(pipelines)} pipelines")
                return pipelines
                
        except Exception as e:
            db_logger.error(f"Failed to list pipelines: {e}")
            raise RuntimeError(f"Failed to list pipelines: {e}")

    def delete(self, pipeline_id):
        """Delete a pipeline by ID"""
        db_logger.info(f"Deleting pipeline with ID: {pipeline_id}")
        
        try:
            # First, get the pipeline name for logging
            pipeline_info = self.get(pipeline_id)
            pipeline_name = pipeline_info["name"]
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Delete the pipeline
                delete_sql = "DELETE FROM pipelines WHERE id = ?"
                cursor.execute(delete_sql, (pipeline_id,))
                
                if cursor.rowcount == 0:
                    raise ValueError(f"Pipeline with id {pipeline_id} not found.")
                
                conn.commit()
                db_logger.info(f"Pipeline {pipeline_name} deleted successfully")
                
        except ValueError:
            # Re-raise ValueError for not found
            raise
        except Exception as e:
            db_logger.error(f"Failed to delete pipeline {pipeline_id}: {e}")
            raise RuntimeError(f"Failed to delete pipeline: {e}")

    def update_write_count(self, pipeline_id, count):
        """Update the write count for a pipeline"""
        db_logger.info(f"Updating write count for pipeline {pipeline_id}: {count}")
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                update_sql = "UPDATE pipelines SET write_count = ? WHERE id = ?"
                cursor.execute(update_sql, (count, pipeline_id))
                
                if cursor.rowcount == 0:
                    raise ValueError(f"Pipeline with id {pipeline_id} not found.")
                
                conn.commit()
                db_logger.debug(f"Write count updated successfully")
                
        except Exception as e:
            db_logger.error(f"Failed to update write count: {e}")
            raise RuntimeError(f"Failed to update write count: {e}")
