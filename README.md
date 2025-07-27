# Synthetic Data Generation Pipeline

This project is a synthetic data generation pipeline that uses AI to create realistic, real-time data streams. It's built with Python (FastAPI) and leverages Timeplus for stream processing and Kafka for data messaging. The frontend is a simple HTML/CSS/JS interface for managing the data pipelines.

## Key Features

*   **AI-Powered Data Generation:** Uses an AI agent (likely OpenAI's GPT) to generate Timeplus Random Stream DDL from natural language descriptions.
*   **Real-time Data Streams:** Creates and manages self-generating data streams in Timeplus.
*   **Web Interface:** Provides a user-friendly UI to create, view, and delete data pipelines.
*   **Dockerized Environment:** The entire application stack (FastAPI app, Timeplus, Kafka) can be easily run using Docker Compose.

## Project Architecture

The project consists of the following components:

*   **Frontend:** A single-page web application built with HTML, CSS, and JavaScript that allows users to manage the data pipelines.
*   **Backend:** A FastAPI application that provides a RESTful API for creating, viewing, and deleting data pipelines. It uses an AI agent to generate the Timeplus DDL.
*   **Timeplus:** A real-time data platform used for creating and managing the synthetic data streams.
*   **Kafka:** A distributed streaming platform used for messaging. The generated data is pushed to a Kafka topic.

## Getting Started

### Prerequisites

*   Docker and Docker Compose
*   An OpenAI API key

### Installation and Running

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/timeplus-io/superpartner.git
    cd superpartner/random_stream
    ```

2.  **Create an `env.sh` file:**

    Create a file named `env.sh` in the root of the project and add your OpenAI API key:

    ```bash
    export OPENAI_API_KEY="your-openai-api-key"
    ```

3.  **Run the application:**

    ```bash
    source env.sh
    docker-compose up -d
    ```

4.  **Install dependencies and initialize UDFs:**

    ```bash
    make install
    ```

5.  **Access the application:**

    Open your web browser and navigate to `http://localhost:5001`.

## API Documentation

The FastAPI backend provides the following API endpoints:

*   `POST /pipelines`: Create a new synthetic data pipeline.
*   `GET /pipelines`: List all existing pipelines.
*   `GET /pipelines/{pipeline_id}`: Get the details of a specific pipeline.
*   `DELETE /pipelines/{pipeline_id}`: Delete a pipeline.
