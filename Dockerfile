# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in docker
WORKDIR /usr/src/app

# Copy the content of the local src directory to the working directory
COPY . .

# Install the application dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 5000 to the outside world
EXPOSE 5000

# Command to run the application using gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "main:app"]
