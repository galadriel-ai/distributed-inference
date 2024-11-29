FROM continuumio/miniconda3:24.7.1-0

RUN apt-get update && apt-get install -y gcc logrotate g++ libtidy-dev git libmagic1 tesseract-ocr

ADD requirements.txt /
RUN pip install -r requirements.txt

# Logrotate
COPY docker/logrotate_app_logs /etc/logrotate.d/log-file
RUN chmod 644 /etc/logrotate.d/log-file

# Create new user to not run in sudo mode
RUN useradd --create-home appuser
WORKDIR /home/appuser

COPY . /home/appuser

# Copy the Google Cloud credentials to the container
COPY /home/ubuntu/sidekik-ai-7191fc59c17c.json /home/appuser
