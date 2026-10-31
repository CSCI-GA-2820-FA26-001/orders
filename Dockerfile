##################################################
# Create production image for the Orders service
##################################################
FROM python:3.12-slim

# Set up the Python production environment
WORKDIR /app
COPY Pipfile Pipfile.lock ./
RUN python -m pip install --upgrade pip pipenv && \
    pipenv install --system --deploy && \
    pip uninstall -y pipenv

# Copy the application contents
COPY wsgi.py .
COPY service/ ./service/

# Switch to a non-root user
RUN useradd --uid 1001 orders && chown -R orders /app
USER orders

# Expose any ports the app is expecting in the environment
ENV FLASK_APP=wsgi:app
ENV PORT=8080
EXPOSE $PORT

# Run the service
ENTRYPOINT ["gunicorn"]
CMD ["--bind=0.0.0.0:8080", "--log-level=info", "wsgi:app"]
