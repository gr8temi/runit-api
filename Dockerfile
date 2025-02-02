FROM python:3.10

# Set environment variables
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

# Install requirements
ADD requirements.txt .
RUN pip install -r requirements.txt
RUN rm requirements.txt

# copy application codebase
RUN mkdir /app
WORKDIR /app
COPY . .

RUN mkdir -p /app/logs && \
    chmod -R 755 /app/logs