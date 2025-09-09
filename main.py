from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List
import json
import os
import re
import uuid
import logging
import time
from textwrap import dedent

import faker

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from proton_driver import client
from sqlite_pipeline_manager import SQLitePipelineManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pipeline_app.log'),
        logging.StreamHandler()  # Console output
    ]
)

# Create specific loggers
app_logger = logging.getLogger("pipeline_app")
db_logger = logging.getLogger("database")
ai_logger = logging.getLogger("ai_generator")
api_logger = logging.getLogger("api")

timeplus_host = os.getenv("TIMEPLUS_HOST") or "localhost"
timeplus_user = os.getenv("TIMEPLUS_USER") or "proton"
timeplus_password = os.getenv("TIMEPLUS_PASSWORD") or "timeplus@t+"
timeplus_port = int(os.getenv("TIMEPLUS_PORT", "8463"))

# Configuration for metadata storage
# Options: 'sqlite' (default) or 'mutable_stream'
METADATA_STORAGE = os.getenv("METADATA_STORAGE", "sqlite").lower()
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "pipelines.db")

def wait_for_timeplus_connection(max_retries=30, retry_delay=2):
    """
    Wait for Timeplus server to be available by pinging it with 'SELECT 1'
    
    Args:
        max_retries (int): Maximum number of connection attempts
        retry_delay (int): Delay between retries in seconds
        
    Returns:
        client.Client: Connected client instance
        
    Raises:
        RuntimeError: If connection fails after max_retries
    """
    
    db_logger.info(f"Waiting for Timeplus server at {timeplus_user}@{timeplus_host}:{timeplus_port}")
    db_logger.info(f"Will attempt connection up to {max_retries} times with {retry_delay}s delay between attempts")
    
    for attempt in range(1, max_retries + 1):
        try:
            db_logger.info(f"Connection attempt {attempt}/{max_retries}")
            
            # Create client connection
            timeplus_client = client.Client(
                host=timeplus_host,
                user=timeplus_user,
                password=timeplus_password,
                port=timeplus_port,
            )
            
            # Test connection with a simple query
            db_logger.debug("Testing connection with 'SELECT 1'")
            result = timeplus_client.execute("SELECT 1")
            
            if result and result[0][0] == 1:
                db_logger.info("✅ Timeplus server is ready and responding correctly")
                return timeplus_client
            else:
                db_logger.warning(f"Unexpected response from Timeplus: {result}")
                
        except Exception as e:
            db_logger.warning(f"Connection attempt {attempt} failed: {e}")
            
            if attempt < max_retries:
                db_logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                db_logger.error(f"Failed to connect to Timeplus after {max_retries} attempts")
                raise RuntimeError(f"Could not connect to Timeplus server after {max_retries} attempts. Last error: {e}")
    
    # This should never be reached, but just in case
    raise RuntimeError("Unexpected end of connection attempts")

# Pydantic models for request/response
class PipelineCreate(BaseModel):
    question: str

class PipelineResponse(BaseModel):
    id: str
    name: str
    question: str
    pipeline: dict

class PipelineList(BaseModel):
    pipelines: List[dict]

# Your existing helper functions
def extract_code_blocks_with_type(markdown_text):
    """
    Extract code blocks and their types from a Markdown string.

    Parameters:
        markdown_text (str): The Markdown content as a string.

    Returns:
        list: A list of tuples, each containing (code_type, code_content).
              If no type is specified, code_type will be an empty string.
    """
    app_logger.debug(f"Extracting code blocks from markdown text (length: {len(markdown_text)})")
    pattern = r"```(\w+)?\n(.*?)```"
    matches = re.findall(pattern, markdown_text, re.DOTALL)
    app_logger.debug(f"Found {len(matches)} code blocks")
    
    result = [
        (code_type if code_type else "", code_content.strip())
        for code_type, code_content in matches
    ]
    
    for i, (code_type, code_content) in enumerate(result):
        app_logger.debug(f"Code block {i}: type='{code_type}', length={len(code_content)}")
    
    return result

def generate_to_kafka_pipeline(input_stream, kafka_settings):
    app_logger.info(f"Generating Kafka pipeline for stream: {input_stream}")
    app_logger.debug(f"Kafka settings: {kafka_settings}")
    
    kafka_external_stream_name = "kafka_external_" + input_stream
    kafka_external_stream_ddl = f"""
    CREATE EXTERNAL STREAM {kafka_external_stream_name} (value string)
    SETTINGS { ','.join([f'{key} = \'{value}\'' for key, value in kafka_settings.items()]) }
    """

    write_to_kafka_mv_name = "mv_" + kafka_external_stream_name
    write_to_kafka_mv_ddl = f"""
    CREATE MATERIALIZED VIEW {write_to_kafka_mv_name} 
        INTO {kafka_external_stream_name}
    AS
        SELECT json_encode(*) as value
        FROM {input_stream}
    """
    
    pipeline = {}
    pipeline["kafka_external_stream"] = {
        "name": kafka_external_stream_name,
        "ddl": kafka_external_stream_ddl
    }
    pipeline["write_to_kafka_mv"] = {
        "name": write_to_kafka_mv_name,
        "ddl": write_to_kafka_mv_ddl
    }
    
    app_logger.info(f"Generated Kafka pipeline components:")
    app_logger.info(f"  - External stream: {kafka_external_stream_name}")
    app_logger.info(f"  - Materialized view: {write_to_kafka_mv_name}")
    
    return pipeline

class RandomNameGenerator:
    def __init__(self):
        self.instruction = "use no more than three words to summarize the input description, return snake case result such as word1_word2_word3 as result"
        # Initialize AI agent
        model_id = os.getenv("OPENAI_MODEL", "gpt-4o")
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        
        try:
            self.agent = Agent(
                model=OpenAIChat(id=model_id, api_key=api_key, base_url=base_url),
                instructions=dedent(self.instruction),
                markdown=False,
            )
            ai_logger.info("AI agent initialized successfully")
        except Exception as e:
            ai_logger.error(f"Failed to initialize AI agent for name generation: {e}")
            raise
    
    def get_name(self, description):
        try:
            ai_logger.info("Calling AI agent to generate name")
            result = self.agent.run(description, stream=False)
            return result.content.strip()
        except Exception as e:
            ai_logger.error(f"AI generation name failed: {e}")
            raise RuntimeError(f"Failed to generate name with AI: {e}")

class SyntheticDataGenerator:
    def __init__(self, name, question):
        ai_logger.info(f"Initializing SyntheticDataGenerator with name='{name}', question='{question}'")
        
        try:
            with open('./prompt/prompt.txt', 'r') as f:
                prompt = f.read()
            ai_logger.debug(f"Loaded prompt file (length: {len(prompt)})")
        except Exception as e:
            ai_logger.error(f"Failed to load prompt file: {e}")
            raise
            
        self.prompt = prompt
        
        # Initialize AI agent
        model_id = os.getenv("OPENAI_MODEL", "gpt-4o")
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        
        ai_logger.info(f"Initializing OpenAI agent with model: {model_id}")
        ai_logger.debug(f"Base URL: {base_url}")
        ai_logger.debug(f"API key configured: {'Yes' if api_key else 'No'}")
        
        try:
            self.agent = Agent(
                model=OpenAIChat(id=model_id, api_key=api_key, base_url=base_url),
                instructions=dedent(self.prompt),
                markdown=False,
            )
            ai_logger.info("AI agent initialized successfully")
        except Exception as e:
            ai_logger.error(f"Failed to initialize AI agent: {e}")
            raise
        
        self.name = name
        self.kafka_settings = {
            "type": "kafka",
            "brokers": os.getenv("KAFKA_BROKERS", "localhost:9092"),
            "topic": self.name + "_topic"
        }
        self.question = question
        self.user_prompt = f"{question}, ONLY return the random stream DDL, and the stream name is {self.name}"
        
        ai_logger.debug(f"Kafka settings: {self.kafka_settings}")
        ai_logger.debug(f"User prompt: {self.user_prompt}")

    def generate_pipeline(self):
        ai_logger.info(f"Starting pipeline generation for '{self.name}'")
        start_time = time.time()
        
        try:
            ai_logger.info("Calling AI agent to generate DDL...")
            result = self.agent.run(self.user_prompt, stream=False)
            
            generation_time = time.time() - start_time
            ai_logger.info(f"AI generation completed in {generation_time:.2f} seconds")
            ai_logger.debug(f"AI response length: {len(result.content)}")
            ai_logger.debug(f"AI response content preview: {result.content[:200]}...")
            
        except Exception as e:
            ai_logger.error(f"AI generation failed: {e}")
            raise RuntimeError(f"Failed to generate DDL with AI: {e}")
        
        try:
            ai_logger.info("Extracting code blocks from AI response...")
            d0 = extract_code_blocks_with_type(result.content)
            
            if not d0:
                ai_logger.error("No code blocks found in AI response")
                ai_logger.debug(f"Full AI response: {result.content}")
                raise RuntimeError("AI did not return any code blocks")
            
            if len(d0[0]) < 2 or not d0[0][1]:
                ai_logger.error("First code block is empty or malformed")
                ai_logger.debug(f"Code blocks found: {d0}")
                raise RuntimeError("AI returned empty or malformed DDL")
                
            ddl_content = d0[0][1]
            ai_logger.info(f"Extracted DDL content (length: {len(ddl_content)})")
            ai_logger.info(f"DDL preview: {ddl_content}")
            
        except Exception as e:
            ai_logger.error(f"Failed to extract DDL from AI response: {e}")
            raise
        
        try:
            ai_logger.info("Generating Kafka pipeline components...")
            pipeline = generate_to_kafka_pipeline(self.name, self.kafka_settings)
            
            pipeline["random_stream"] = {
                "name": self.name,
                "ddl": ddl_content
            }
            pipeline["question"] = self.question
            
            ai_logger.info("Pipeline generation completed successfully")
            ai_logger.debug(f"Pipeline structure: {list(pipeline.keys())}")
            
            return pipeline
            
        except Exception as e:
            ai_logger.error(f"Failed to generate pipeline structure: {e}")
            raise

class PipelineManager:
    def __init__(self):
        db_logger.info(f"Initializing PipelineManager with metadata storage: {METADATA_STORAGE}")
        db_logger.info(f"Connecting to Timeplus: {timeplus_user}@{timeplus_host}:{timeplus_port}")
        
        # Initialize Timeplus client for stream operations
        try:
            self.client = client.Client(
                host=timeplus_host,
                user=timeplus_user,
                password=timeplus_password,
                port=timeplus_port,
            )
            db_logger.info("Timeplus connection established")
        except Exception as e:
            db_logger.error(f"Failed to connect to Timeplus: {e}")
            raise
        
        # Initialize metadata storage based on configuration
        self.use_sqlite = METADATA_STORAGE == "sqlite"
        
        if self.use_sqlite:
            # Initialize SQLite manager for metadata
            try:
                self.metadata_manager = SQLitePipelineManager(SQLITE_DB_PATH)
                db_logger.info(f"SQLite metadata manager initialized with database: {SQLITE_DB_PATH}")
            except Exception as e:
                db_logger.error(f"Failed to initialize SQLite manager: {e}")
                raise
        else:
            # Initialize mutable stream for metadata (legacy mode)
            self.pipeline_stream_name = "synthetic_data_pipelines"
            self._init_pipeline_metadata()
        
    def _init_pipeline_metadata(self):
        """Initialize mutable stream for metadata storage (legacy mode)"""
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
            raise

    def create(self, pipeline, name):
        pipeline_id = uuid.uuid4().hex
        db_logger.info(f"Creating pipeline with ID: {pipeline_id}, name: {name}")
        
        # Create the pipeline components in Timeplus
        db_logger.info("Creating pipeline components in timeplus...")
        try:
            # Create random stream
            random_stream_ddl = pipeline["random_stream"]["ddl"]
            db_logger.debug(f"Creating random stream with DDL: {random_stream_ddl}")
            self.client.execute(random_stream_ddl)
            db_logger.info(f"Created random stream: {pipeline['random_stream']['name']}")
        except Exception as e:
            db_logger.error(f"Error creating random stream: {e}")
            db_logger.error(f"Failed DDL might be: {pipeline.get('random_stream', {}).get('ddl', 'N/A')}")
            raise RuntimeError(f"Failed to create pipeline: {e}")
        
        try:
            # Create Kafka external stream
            kafka_stream_ddl = pipeline["kafka_external_stream"]["ddl"]
            db_logger.info(f"Creating Kafka external stream with DDL: {kafka_stream_ddl}")
            self.client.execute(kafka_stream_ddl)
            db_logger.info(f"Created Kafka external stream: {pipeline['kafka_external_stream']['name']}")
        except Exception as e:
            db_logger.warning(f"Error creating external stream and retry it: {e}")
            time.sleep(3) # Retry after a short delay
            try:
                self.client.execute(kafka_stream_ddl)
            except Exception as e:
                db_logger.error(f"Failed to create Kafka external stream: {e}")
                db_logger.error(f"Failed DDL might be: {pipeline.get('kafka_external_stream', {}).get('ddl', 'N/A')}")
                raise RuntimeError(f"Failed to create pipeline: {e}")
        
        try:
            # Create materialized view
            mv_ddl = pipeline["write_to_kafka_mv"]["ddl"]
            db_logger.info(f"Creating materialized view with DDL: {mv_ddl}")
            self.client.execute(mv_ddl)
            db_logger.info(f"Created materialized view: {pipeline['write_to_kafka_mv']['name']}")
            
        except Exception as e:
            db_logger.error(f"Error creating materialized view: {e}")
            db_logger.error(f"Failed DDL might be: {pipeline.get('write_to_kafka_mv', {}).get('ddl', 'N/A')}")
            raise RuntimeError(f"Failed to create pipeline: {e}")
        
        # Save metadata using the configured backend
        try:
            db_logger.info(f"Saving pipeline metadata using {METADATA_STORAGE}...")
            
            if self.use_sqlite:
                # Save to SQLite
                saved_id = self.metadata_manager.create(pipeline, name)
                db_logger.info("Pipeline metadata saved successfully to SQLite")
            else:
                # Save to mutable stream (legacy mode)
                pipeline_json = json.dumps(pipeline, indent=2)
                insert_sql = f"INSERT INTO {self.pipeline_stream_name} (id, name, pipeline) VALUES"
                values = [[pipeline_id, name, pipeline_json]]
                
                db_logger.debug(f"Executing insert: {insert_sql}")
                db_logger.debug(f"Values: id={pipeline_id}, name={name}, pipeline_length={len(pipeline_json)}")
                
                self.client.execute(insert_sql, values)
                saved_id = pipeline_id
                db_logger.info("Pipeline metadata saved successfully to mutable stream")
                
        except Exception as e:
            db_logger.error(f"Failed to save pipeline metadata: {e}")
            raise RuntimeError(f"Failed to save pipeline metadata: {e}")
        
        db_logger.info(f"Pipeline creation completed successfully with ID: {saved_id}")
        return saved_id
    
    def _get_pipeline_write_count(self, pipeline_json):
        query_sql = f"SELECT COUNT(*) FROM table({pipeline_json['write_to_kafka_mv']['name']}) WHERE _tp_time > earliest_ts()"
        db_logger.debug(f"Executing query: {query_sql}")
        
        try:
            result = self.client.execute(query_sql)
            db_logger.debug(f"Query result: {len(result) if result else 0} rows")
            
            if result:
                return result[0][0]
            else:
                return 0
        except Exception as e:
            db_logger.error(f"Failed to get write count: {e}")
            return 0
        
    def get(self, pipeline_id):
        db_logger.info(f"Retrieving pipeline with ID: {pipeline_id}")
        
        try:
            if self.use_sqlite:
                # Get from SQLite
                pipeline_info = self.metadata_manager.get(pipeline_id)
                
                # Get live write count from Timeplus
                live_count = self._get_pipeline_write_count(pipeline_info['pipeline'])
                
                # Update the write count
                pipeline_info['write_count'] = live_count
                
                db_logger.info(f"Successfully retrieved pipeline from SQLite: {pipeline_info['name']} (writes: {live_count})")
                return pipeline_info
            else:
                # Get from mutable stream (legacy mode)
                query_sql = f"SELECT name, pipeline FROM table({self.pipeline_stream_name}) WHERE id = '{pipeline_id}'"
                db_logger.debug(f"Executing query: {query_sql}")
                
                result = self.client.execute(query_sql)
                db_logger.debug(f"Query result: {len(result) if result else 0} rows")
                
                if result:
                    name = result[0][0]
                    pipeline_json = result[0][1]
                    
                    db_logger.debug(f"Found pipeline: name={name}, json_length={len(pipeline_json)}")
                    
                    # Get Pipeline Stats
                    count = self._get_pipeline_write_count(json.loads(pipeline_json))
                    db_logger.info(f"Pipeline {name} has {count} writes")
                    
                    try:
                        pipeline_data = json.loads(pipeline_json)
                        db_logger.info(f"Successfully retrieved pipeline from mutable stream: {name}")
                        
                        return {
                            "id": pipeline_id,
                            "name": name,
                            "pipeline": pipeline_data,
                            "write_count": count
                        }
                    except json.JSONDecodeError as e:
                        db_logger.error(f"Failed to parse pipeline JSON: {e}")
                        db_logger.debug(f"Malformed JSON: {pipeline_json}")
                        raise RuntimeError(f"Failed to parse pipeline data: {e}")
                else:
                    db_logger.warning(f"Pipeline with id {pipeline_id} not found")
                    raise ValueError(f"Pipeline with id {pipeline_id} not found.")
                
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            db_logger.error(f"Failed to retrieve pipeline: {e}")
            raise RuntimeError(f"Failed to get pipeline: {e}")

    def list_all(self):
        db_logger.info("Listing all pipelines")
        
        try:
            if self.use_sqlite:
                # List from SQLite
                pipelines = self.metadata_manager.list_all()
                db_logger.info(f"Successfully listed {len(pipelines)} pipelines from SQLite")
                return pipelines
            else:
                # List from mutable stream (legacy mode)
                query_sql = f"SELECT id, name, pipeline FROM table({self.pipeline_stream_name})"
                db_logger.debug(f"Executing query: {query_sql}")
                
                result = self.client.execute(query_sql)
                db_logger.info(f"Found {len(result) if result else 0} pipelines")
                
                pipelines = []
                for i, row in enumerate(result):
                    try:
                        id, name, pipeline_json = row
                        pipeline_data = json.loads(pipeline_json)
                        
                        pipeline_info = {
                            "id": id,
                            "name": name,
                            "question": pipeline_data.get("question", ""),
                            "created_at": pipeline_data.get("created_at", "")
                        }
                        pipelines.append(pipeline_info)
                        
                        db_logger.debug(f"Pipeline {i}: {id} - {name}")
                        
                    except Exception as e:
                        db_logger.error(f"Failed to parse pipeline {i}: {e}")
                        continue
                
                db_logger.info(f"Successfully processed {len(pipelines)} pipelines from mutable stream")
                return pipelines
            
        except Exception as e:
            db_logger.error(f"Failed to list pipelines: {e}")
            raise RuntimeError(f"Failed to list pipelines: {e}")

    def delete(self, pipeline_id):
        db_logger.info(f"Deleting pipeline with ID: {pipeline_id}")
        
        # Get pipeline info first (this will work with both backends)
        try:
            pipeline_info = self.get(pipeline_id)
            pipeline = pipeline_info["pipeline"]
            name = pipeline_info["name"]
            
            db_logger.info(f"Deleting pipeline: {name}")
            
        except Exception as e:
            db_logger.error(f"Failed to get pipeline info for deletion: {e}")
            raise
        
        # Delete the pipeline resources from Timeplus
        try:
            db_logger.info("Deleting pipeline components from Timeplus...")
            
            # Delete materialized view
            mv_name = pipeline['write_to_kafka_mv']['name']
            db_logger.debug(f"Dropping materialized view: {mv_name}")
            self.client.execute(f"DROP VIEW IF EXISTS {mv_name}")
            
            # Delete Kafka external stream
            kafka_stream_name = pipeline['kafka_external_stream']['name']
            db_logger.debug(f"Dropping external stream: {kafka_stream_name}")
            self.client.execute(f"DROP STREAM IF EXISTS {kafka_stream_name}")
            
            # Delete random stream
            random_stream_name = pipeline['random_stream']['name']
            db_logger.debug(f"Dropping random stream: {random_stream_name}")
            self.client.execute(f"DROP STREAM IF EXISTS {random_stream_name}")
            
            db_logger.info("Pipeline components deleted successfully")
            
        except Exception as e:
            db_logger.error(f"Error deleting pipeline resources: {e}")
            raise RuntimeError(f"Failed to delete pipeline resources: {e}")
        
        # TODO: delete Kafka topic
        
        # Delete pipeline metadata using the configured backend
        try:
            if self.use_sqlite:
                # Delete from SQLite
                db_logger.info("Deleting pipeline metadata from SQLite...")
                self.metadata_manager.delete(pipeline_id)
                db_logger.info(f"Pipeline {name} deleted successfully from SQLite")
            else:
                # Delete from mutable stream (legacy mode)
                db_logger.info("Deleting pipeline metadata from mutable stream...")
                delete_sql = f"DELETE FROM {self.pipeline_stream_name} WHERE id = '{pipeline_id}'"
                db_logger.debug(f"Executing: {delete_sql}")
                
                self.client.execute(delete_sql)
                db_logger.info(f"Pipeline {name} deleted successfully from mutable stream")
            
        except Exception as e:
            db_logger.error(f"Failed to delete pipeline metadata: {e}")
            raise RuntimeError(f"Failed to delete pipeline metadata: {e}")

# FastAPI app
app = FastAPI(title="Synthetic Data Pipeline API", description="API for managing synthetic data pipelines")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Initialize pipeline manager
try:
    wait_for_timeplus_connection()
    pipeline_manager = PipelineManager()
    app_logger.info("Application initialized successfully")
except Exception as e:
    app_logger.error(f"Failed to initialize application: {e}")
    raise

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log request
    api_logger.info(f"Request: {request.method} {request.url}")
    api_logger.debug(f"Headers: {dict(request.headers)}")
    
    # Process request
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    api_logger.info(f"Response: {response.status_code} ({process_time:.3f}s)")
    
    return response

@app.post("/pipelines", response_model=dict)
async def create_pipeline(pipeline_data: PipelineCreate):
    """Create a new synthetic data pipeline"""
    api_logger.info("POST /pipelines - Creating new pipeline")
    api_logger.debug(f"Request data: {pipeline_data.dict()}")
    
    try:
        # Generate a random name for the pipeline
        fake = faker.Faker()
        name_generator = RandomNameGenerator()
        name = f'rnd_{name_generator.get_name(pipeline_data.question)}_{fake.random_digit()}'
        api_logger.info(f"Generated pipeline name: {name}")
        
        # Generate pipeline using AI
        api_logger.info("Starting AI pipeline generation...")
        generator = SyntheticDataGenerator(
            name=name,
            question=pipeline_data.question
        )
        pipeline = generator.generate_pipeline()
        
        # Create pipeline in database
        api_logger.info("Creating pipeline in database...")
        pipeline_id = pipeline_manager.create(pipeline, name)
        
        response_data = {
            "id": pipeline_id,
            "name": name,
            "question": pipeline_data.question,
            "message": "Pipeline created successfully"
        }
        
        api_logger.info(f"Pipeline created successfully: {pipeline_id}")
        api_logger.debug(f"Response data: {response_data}")
        
        return response_data
        
    except Exception as e:
        api_logger.error(f"Failed to create pipeline: {e}")
        api_logger.error(f"Exception type: {type(e).__name__}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/pipelines", response_model=dict)
async def list_pipelines():
    """List all pipelines"""
    api_logger.info("GET /pipelines - Listing all pipelines")
    
    try:
        pipelines = pipeline_manager.list_all()
        response_data = {"pipelines": pipelines}
        
        api_logger.info(f"Listed {len(pipelines)} pipelines")
        api_logger.debug(f"Pipeline IDs: {[p['id'] for p in pipelines]}")
        
        return response_data
        
    except Exception as e:
        api_logger.error(f"Failed to list pipelines: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/pipelines/{pipeline_id}", response_model=dict)
async def get_pipeline(pipeline_id: str):
    """Get a specific pipeline by ID"""
    api_logger.info(f"GET /pipelines/{pipeline_id} - Getting pipeline details")
    
    try:
        pipeline = pipeline_manager.get(pipeline_id)
        
        api_logger.info(f"Retrieved pipeline: {pipeline['name']}")
        api_logger.debug(f"Pipeline components: {list(pipeline['pipeline'].keys())}")
        
        return pipeline
        
    except ValueError as e:
        api_logger.warning(f"Pipeline not found: {pipeline_id}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        api_logger.error(f"Failed to get pipeline {pipeline_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/pipelines/{pipeline_id}")
async def delete_pipeline(pipeline_id: str):
    """Delete a pipeline by ID"""
    api_logger.info(f"DELETE /pipelines/{pipeline_id} - Deleting pipeline")
    
    try:
        pipeline_manager.delete(pipeline_id)
        
        response_data = {"message": f"Pipeline {pipeline_id} deleted successfully"}
        api_logger.info(f"Pipeline deleted successfully: {pipeline_id}")
        
        return response_data
        
    except ValueError as e:
        api_logger.warning(f"Pipeline not found for deletion: {pipeline_id}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        api_logger.error(f"Failed to delete pipeline {pipeline_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
async def get_manager_page(request: Request):
    """Serve the pipeline management HTML page"""
    api_logger.info("GET / - Serving management page")
    return templates.TemplateResponse("index.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    app_logger.info("Starting application server on port 5002")
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "5002")))
