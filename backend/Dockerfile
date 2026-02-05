# 1. Start with a lightweight Python base
FROM python:3.12-slim as builder

WORKDIR /app

# 2. Install "Build Tools"
# gcc: The C Compiler. Required to build 'psycopg2' (Postgres driver).
# libpq-dev: Header files for Postgres. Required for compilation.
RUN apt-get update && apt-get install -y gcc libpq-dev

# 3. Create a Virtual Environment (The "Portable Artifact")
# Why venv in Docker? It creates a single, self-contained folder (/opt/venv)
# that contains ALL our libraries. This makes it super easy to "copy-paste"
# into the next stage.
RUN python -m venv /opt/venv

# 4. Activate the venv
# This ensures any 'pip install' command goes into /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .

# 5. Install Python Libraries
# This compiles psycopg2 using the 'gcc' we installed earlier.
RUN pip install --no-cache-dir -r requirements.txt


# 6. Start Fresh
# We grab a BRAND NEW, empty slice of the python:3.12-slim OS.
# It knows nothing about 'gcc' or the files from the previous stage.
FROM python:3.12-slim

WORKDIR /app

# 7. Install ONLY Runtime Dependencies
# libpq-5: This is the "Shared Library" version of Postgres.
# It lets the app *talk* to DB, but it cannot *compile* new code.
# rm -rf ...: Cleans up the apt cache to save space.
RUN apt-get update && \
    apt-get install -y libpq5 && \
    rm -rf /var/lib/apt/lists/*

# 8. Copy the Artifact
# We reach back into the 'builder' stage and grab JUST the venv folder.
# This works because the OS (Debian Bookworm) is the same in both stages.
COPY --from=builder /opt/venv /opt/venv

# 9. Activate the venv
ENV PATH="/opt/venv/bin:$PATH"

# 10. Security Hardening
# By default, Docker runs as 'root'. If a hacker breaks in, they own the container.
# We create a dummy user 'appuser' with no permissions and switch to it.
RUN useradd -m appuser
USER appuser

# 11. Run the App
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]