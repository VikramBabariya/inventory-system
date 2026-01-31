ADR 001: Selection of FastAPI for Backend Service

Status: Accepted Context: We need a backend framework to handle high-concurrency inventory requests. The system requires rapid API development, automatic documentation for frontend integration, and low latency for stock checks.

Decision: We chose FastAPI (Python).

Justification:

Performance: FastAPI is built on "Starlette" and "Pydantic," making it one of the fastest Python frameworks (on par with Node.js and Go). Flask and Django are significantly slower for high-concurrency tasks.

Asynchronous Support: It has native async/await support. This is critical for our project because our backend will spend most of its time "waiting" for the Database and Redis. Async allows it to handle thousands of other requests while waiting.

Automatic Docs: It automatically generates Swagger UI (OpenAPI) documentation. This allows us to test our API endpoints in the browser without writing extra code.

Indian Market Context: While Django is "legacy enterprise," FastAPI is the standard for modern Cloud-Native and Data-centric roles in India.

Consequences:

We need to use an ASGI server (Uvicorn) instead of a traditional WSGI server (Gunicorn) to run it.