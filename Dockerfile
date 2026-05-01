# Base Image
FROM python:3.10

# Having an editor is very nice
RUN apt-get update && apt-get install -y \
  vim sqlite3 postgresql \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /code

COPY requirements-dev.txt .

RUN pip install --require-hashes -r requirements-dev.txt

VOLUME /code

CMD ["/bin/bash"]
