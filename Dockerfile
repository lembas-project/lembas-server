FROM node:14 AS tailwind

# Set the working directory in the container
WORKDIR /app

# Copy package.json and package-lock.json (if available)
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of your application's code
# COPY . .
COPY tailwind.config.js ./
COPY static/ ./static
COPY templates/ ./templates

# Install Tailwind CSS CLI globally
RUN npm install -g tailwindcss

# Generate CSS using Tailwind CSS CLI
# Adjust the input and output paths as needed
RUN tailwindcss -i ./static/css/input.css -o ./output.css

FROM --platform=linux/amd64 continuumio/miniconda3:24.11.1-0@sha256:6a66425f001f739d4778dd732e020afeb06175f49478fafc3ec673658d61550b as builder

# TODO: Replace this with a new builder image that is generated from its own lockfile
RUN conda install -c conda-forge --override-channels conda-project

WORKDIR /app

# Pre-install project dependencies during image build
COPY ./conda-lock.prod.yml ./
#COPY ./conda-project.yml ./
#COPY ./environment-*.yml ./

# Create the prod conda environment
RUN conda lock install -p /opt/env conda-lock.prod.yml
ENV PATH="/opt/env/bin:${PATH}"

# Because conda project is re-locking each time, I'm using conda-lock for now
#RUN conda project install --environment prod

# Copy in the app code
COPY app/ ./app
COPY static/ ./static
COPY templates/ ./templates

# Copy in the generated CSS code from tailwind
COPY --from=tailwind ./app/output.css static/css/

# Expose the port and run the service
EXPOSE 8000
ENTRYPOINT ["fastapi"]
CMD ["run"]

# Once we fix conda project, we may want to consider using this instead
#ENTRYPOINT ["conda", "project", "run"]
#CMD ["prod"]
